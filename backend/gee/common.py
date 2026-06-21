"""
Shared Google Earth Engine helpers used by every Kairos analysis function.

Rules enforced here (see CLAUDE.md):
- All computation stays server-side on GEE. Nothing is ever downloaded.
- Sentinel-1 is always filtered to instrument mode + polarization.
- Results are always clipped to the AOI before getMapId().
- reduceRegion always uses bestEffort=True.
"""

import ee
from datetime import datetime, timedelta

S1_COLLECTION = "COPERNICUS/S1_GRD"
JRC_WATER = "JRC/GSW1_4/GlobalSurfaceWater"

# Kairos palette (from the design spec)
TEAL = "#00BFA8"
AMBER = "#E8A318"


def bbox_geometry(bbox: list) -> ee.Geometry:
    """Convert [min_lon, min_lat, max_lon, max_lat] into an ee.Geometry."""
    return ee.Geometry.Rectangle(bbox)


def s1_collection(
    geometry: ee.Geometry,
    polarization: str = "VV",
    instrument_mode: str = "IW",
) -> ee.ImageCollection:
    """
    Sentinel-1 GRD collection, correctly filtered.

    polarization: 'VV' or 'VH'
    instrument_mode: 'IW' for land/coastal, 'EW' for polar sea ice
    """
    return (
        ee.ImageCollection(S1_COLLECTION)
        .filter(ee.Filter.eq("instrumentMode", instrument_mode))
        .filter(
            ee.Filter.listContains("transmitterReceiverPolarisation", polarization)
        )
        .select(polarization)
        .filterBounds(geometry)
    )


def require_images(collection: ee.ImageCollection, context: str) -> int:
    """
    Count images; raise a user-facing ValueError if the collection is empty.
    The /analyze endpoint converts ValueError into an HTTP 400 with this message.
    """
    count = collection.size().getInfo()
    if count == 0:
        raise ValueError(
            f"No Sentinel-1 data found for {context}. "
            "Try a wider date range, or check that the area is within "
            "Sentinel-1 coverage (most land is revisited every 12 days)."
        )
    return count


def baseline_window(start_date: str, days: int = 30) -> tuple:
    """Return (baseline_start, baseline_end) strings ending the day before start_date."""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end = start_dt - timedelta(days=1)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def permanent_water_mask(occurrence_pct: int = 75) -> ee.Image:
    """Pixels that were water more than occurrence_pct% of the time historically."""
    return ee.Image(JRC_WATER).select("occurrence").gt(occurrence_pct)


# Reference-layer palette (distinct from the teal/amber detection palette so
# context layers read as "background" against the analysis result on top).
WATER_BLUE = "#3BA7FF"


def permanent_water_tile(geometry: ee.Geometry, occurrence_pct: int = 50) -> str:
    """
    A standalone reference tile of historically permanent water (rivers, lakes,
    coastline) clipped to the AOI. Rendered alongside a detection result so the
    user can tell genuinely NEW water (e.g. flooding) from water that is always
    there. Returns a Mapbox-compatible XYZ tile URL.
    """
    water = (
        ee.Image(JRC_WATER)
        .select("occurrence")
        .gt(occurrence_pct)
        .selfMask()
        .clip(geometry)
    )
    return tile_url(water, {"palette": [WATER_BLUE], "min": 0, "max": 1})


def tile_url(image: ee.Image, vis_params: dict) -> str:
    """Generate a Mapbox-compatible XYZ tile URL from a GEE image."""
    map_id = image.getMapId(vis_params)
    return map_id["tile_fetcher"].url_format


def area_km2(mask_image: ee.Image, geometry: ee.Geometry, band: str, scale: int = 30) -> float:
    """Sum the area (km^2) of all unmasked truthy pixels in mask_image."""
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
    """Date (YYYY-MM-DD) of the most recent image in the collection."""
    latest = collection.sort("system:time_start", False).first()
    return ee.Date(latest.get("system:time_start")).format("YYYY-MM-dd").getInfo()
