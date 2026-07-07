import ee
from datetime import datetime, timedelta
from gee import common

_CLEAR_DROP_DB = 3.0
_POND_DARK_DB = -17.0
MINING_COLOR = "#FF6B2C"


def detect_land_disturbance(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)

    def dual_pol(start, end):
        return (
            ee.ImageCollection(common.S1_COLLECTION)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .select(["VV", "VH"])
            .filterBounds(geometry)
            .filterDate(start, end)
        )

    recent = dual_pol(start_date, end_date)
    recent_count = common.require_images(
        recent,
        f"dual-pol (VV+VH) coverage of this area between {start_date} and {end_date}",
    )

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    base_end = start_dt - timedelta(days=1)
    base_start = base_end - timedelta(days=365)
    baseline = dual_pol(
        base_start.strftime("%Y-%m-%d"), base_end.strftime("%Y-%m-%d")
    )
    baseline_count = common.require_images(
        baseline, "the 12-month land-cover baseline"
    )

    recent_mean = recent.mean()
    base_mean = baseline.mean()

    cleared = base_mean.select("VH").subtract(recent_mean.select("VH")).gt(_CLEAR_DROP_DB)

    permanent = common.permanent_water_mask(50)
    new_pond = recent_mean.select("VV").lt(_POND_DARK_DB).And(permanent.Not())

    disturbed = cleared.Or(new_pond).selfMask().rename("VV").clip(geometry)

    url = common.tile_url(disturbed, {"palette": [MINING_COLOR], "min": 0, "max": 1})

    disturbed_km2 = common.area_km2(disturbed, geometry, band="VV", scale=30)
    cleared_km2 = common.area_km2(
        cleared.selfMask().rename("VV").clip(geometry), geometry, band="VV", scale=30
    )
    pond_km2 = common.area_km2(
        new_pond.selfMask().rename("VV").clip(geometry), geometry, band="VV", scale=30
    )

    data_date = common.latest_image_date(recent)
    confidence = round(min(0.85, 0.55 + 0.02 * baseline_count), 2)

    return {
        "tile_url": url,
        "result_image": disturbed,
        "disturbed_area_km2": disturbed_km2,
        "cleared_area_km2": cleared_km2,
        "pond_area_km2": pond_km2,
        "confidence": confidence,
        "data_date": data_date,
        "recent_images_used": recent_count,
        "baseline_images_used": baseline_count,
        "headline_stat": {
            "label": "Disturbed land",
            "value": disturbed_km2,
            "unit": "km²",
        },
    }
