from contextvars import ContextVar
from datetime import datetime, timedelta

import ee

import gee_ready

S1_COLLECTION = "COPERNICUS/S1_GRD"
JRC_WATER = "JRC/GSW1_4/GlobalSurfaceWater"

TEAL = "#00BFA8"
AMBER = "#E8A318"


active_polygon: ContextVar = ContextVar("active_polygon", default=None)


def bbox_geometry(bbox: list) -> ee.Geometry:
    gee_ready.wait()
    polygon = active_polygon.get()
    if polygon:
        return ee.Geometry.Polygon([[list(p) for p in polygon]])
    return ee.Geometry.Rectangle(bbox)


def polygon_envelope(polygon: list) -> list:
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    return [min(lons), min(lats), max(lons), max(lats)]


def s1_collection(
    geometry: ee.Geometry,
    polarization: str = "VV",
    instrument_mode: str = "IW",
) -> ee.ImageCollection:
    return (
        ee.ImageCollection(S1_COLLECTION)
        .filter(ee.Filter.eq("instrumentMode", instrument_mode))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
        .select(polarization)
        .filterBounds(geometry)
    )


def require_images(collection: ee.ImageCollection, context: str) -> int:
    count = collection.size().getInfo()
    if count == 0:
        raise ValueError(
            f"No Sentinel-1 data found for {context}. "
            "Try a wider date range, or check that the area is within "
            "Sentinel-1 coverage (most land is revisited every 12 days)."
        )
    return count


def baseline_window(start_date: str, days: int = 30) -> tuple:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end = start_dt - timedelta(days=1)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def permanent_water_mask(occurrence_pct: int = 75) -> ee.Image:
    return ee.Image(JRC_WATER).select("occurrence").gt(occurrence_pct)


WATER_BLUE = "#3BA7FF"


def permanent_water_tile(geometry: ee.Geometry, occurrence_pct: int = 50) -> str:
    water = ee.Image(JRC_WATER).select("occurrence").gt(occurrence_pct).selfMask().clip(geometry)
    return tile_url(water, {"palette": [WATER_BLUE], "min": 0, "max": 1})


def despeckle(image: ee.Image, radius_m: int = 50) -> ee.Image:
    return image.focalMedian(radius_m, "circle", "meters")


def ensemble_area(
    diff_image: ee.Image,
    thresholds: list,
    geometry: ee.Geometry,
    band: str,
    exclude_mask: ee.Image = None,
    direction: str = "lt",
    scale: int = 30,
) -> dict:
    areas = {}
    for t in thresholds:
        mask = diff_image.lt(t) if direction == "lt" else diff_image.gt(t)
        if exclude_mask is not None:
            mask = mask.where(exclude_mask, 0)
        mask = mask.selfMask().clip(geometry)
        areas[t] = area_km2(mask, geometry, band=band, scale=scale)

    values = list(areas.values())
    low, high = min(values), max(values)
    mid = sorted(values)[len(values) // 2]
    spread = round((high - low) / mid, 3) if mid > 0 else 0.0
    return {
        "areas_by_threshold": {str(t): a for t, a in areas.items()},
        "area_low_km2": low,
        "area_high_km2": high,
        "relative_spread": spread,
    }


def spread_penalty(spread: float, max_penalty: float = 0.25) -> float:
    return min(max_penalty, max_penalty * spread)


def tile_url(image: ee.Image, vis_params: dict) -> str:
    map_id = image.getMapId(vis_params)
    return map_id["tile_fetcher"].url_format


def area_km2(mask_image: ee.Image, geometry: ee.Geometry, band: str, scale: int = 30) -> float:
    pixel_area = mask_image.multiply(ee.Image.pixelArea())
    result = pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    m2 = result.get(band, 0) or 0
    return round(float(m2) / 1_000_000, 2)


def latest_image_date(collection: ee.ImageCollection) -> str:
    latest = collection.sort("system:time_start", False).first()
    return ee.Date(latest.get("system:time_start")).format("YYYY-MM-dd").getInfo()


_BACKSCATTER_RANGE = {
    "VV": (-25, 0),
    "HH": (-25, 0),
    "HV": (-28, -5),
    "VH": (-28, -5),
}


def backscatter_tile(
    bbox: list,
    start_date: str,
    end_date: str,
    polarization: str = "VV",
    instrument_mode: str = "IW",
) -> dict:
    geometry = bbox_geometry(bbox)
    coll = s1_collection(geometry, polarization, instrument_mode).filterDate(start_date, end_date)
    require_images(coll, f"this area between {start_date} and {end_date}")

    composite = coll.mean().clip(geometry)
    vmin, vmax = _BACKSCATTER_RANGE.get(polarization, (-25, 0))
    url = tile_url(composite, {"min": vmin, "max": vmax})

    return {
        "tile_url": url,
        "data_date": latest_image_date(coll),
        "polarization": polarization,
    }
