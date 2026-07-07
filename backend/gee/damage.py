import ee
from datetime import datetime, timedelta
from gee import common

GHSL_BUILT = "JRC/GHSL/P2023A/GHS_BUILT_S"
_BUILT_EPOCH = "2020"

_BUILT_THRESHOLD = 1000
_CHANGE_THRESHOLD_DB = 4.0
DAMAGE_COLOR = "#FF3B5C"


def assess_damage(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"the post-event window {start_date} to {end_date}"
    )

    pre_start, pre_end = common.baseline_window(start_date, days=30)
    pre = s1.filterDate(pre_start, pre_end)
    if pre.size().getInfo() == 0:
        pre_start, pre_end = common.baseline_window(start_date, days=60)
        pre = s1.filterDate(pre_start, pre_end)
    pre_count = common.require_images(
        pre, "the pre-event baseline (30–60 days before the event date)"
    )

    change_db = post.mean().subtract(pre.mean()).abs()

    built = (
        ee.ImageCollection(GHSL_BUILT)
        .filterDate(f"{_BUILT_EPOCH}-01-01", f"{_BUILT_EPOCH}-12-31")
        .mosaic()
        .select("built_surface")
    )
    built_mask = built.gt(_BUILT_THRESHOLD)

    damaged = (
        change_db.gt(_CHANGE_THRESHOLD_DB)
        .And(built_mask)
        .selfMask()
        .rename("VV")
        .clip(geometry)
    )

    url = common.tile_url(damaged, {"palette": [DAMAGE_COLOR], "min": 0, "max": 1})
    damaged_km2 = common.area_km2(damaged, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(post)

    confidence = round(min(0.85, 0.55 + 0.03 * (pre_count + post_count)), 2)

    return {
        "tile_url": url,
        "result_image": damaged,
        "damaged_area_km2": damaged_km2,
        "confidence": confidence,
        "data_date": data_date,
        "pre_images_used": pre_count,
        "post_images_used": post_count,
        "headline_stat": {
            "label": "Likely-damaged built-up area",
            "value": damaged_km2,
            "unit": "km²",
        },
    }
