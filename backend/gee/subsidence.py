import ee
from datetime import datetime, timedelta
from gee import common

_SLOPE_THRESHOLD = 1.5
SUBSIDENCE_PALETTE = ["#1E6FE8", "#9BC7FF", "#0B120E", "#FFC59B", "#FF3B5C"]


def detect_subsidence(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV").filterDate(
        start_date, end_date
    )
    count = common.require_images(
        s1, f"this area between {start_date} and {end_date}"
    )
    if count < 5:
        raise ValueError(
            "A subsidence trend needs at least ~5 Sentinel-1 passes to be "
            "meaningful. Widen the date range (several months works best)."
        )

    base = ee.Date(start_date)

    def add_time(img):
        t = (
            ee.Image(img.date().difference(base, "year"))
            .float()
            .rename("t")
        )
        return img.addBands(t)

    fitted = (
        s1.map(add_time)
        .select(["t", "VV"])
        .reduce(ee.Reducer.linearFit())
    )
    slope = fitted.select("scale")

    permanent = common.permanent_water_mask(50)
    significant = slope.abs().gt(_SLOPE_THRESHOLD).And(permanent.Not())
    trend = slope.updateMask(significant).rename("VV").clip(geometry)

    url = common.tile_url(
        trend, {"min": -4, "max": 4, "palette": SUBSIDENCE_PALETTE}
    )

    trend_mask = significant.selfMask().rename("VV").clip(geometry)
    trend_km2 = common.area_km2(trend_mask, geometry, band="VV", scale=30)

    data_date = common.latest_image_date(s1)
    confidence = round(min(0.85, 0.45 + 0.03 * count), 2)

    return {
        "tile_url": url,
        "result_image": trend_mask,
        "trend_area_km2": trend_km2,
        "confidence": confidence,
        "data_date": data_date,
        "images_used": count,
        "headline_stat": {
            "label": "Progressive-change area",
            "value": trend_km2,
            "unit": "km²",
        },
    }
