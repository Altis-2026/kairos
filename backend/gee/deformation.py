from datetime import datetime, timedelta
from gee import common

Z_THRESHOLD = 2.0

_SIGMA_FLOOR = 0.5

DEFORM_COLOR = "#C77DFF"


def detect_deformation(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    recent = s1.filterDate(start_date, end_date)
    recent_count = common.require_images(
        recent, f"this area between {start_date} and {end_date}"
    )

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    base_end = start_dt - timedelta(days=1)
    base_start = base_end - timedelta(days=365)
    baseline = s1.filterDate(
        base_start.strftime("%Y-%m-%d"), base_end.strftime("%Y-%m-%d")
    )
    baseline_count = common.require_images(
        baseline, "the 12-month stability baseline"
    )

    base_mean = baseline.mean()
    base_sigma = baseline.reduce("stdDev").rename("VV").max(_SIGMA_FLOOR)

    recent_mean = recent.mean()

    z = recent_mean.subtract(base_mean).divide(base_sigma).abs()
    change_mask = z.gt(Z_THRESHOLD)

    permanent = common.permanent_water_mask(50)
    change = change_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(change, {"palette": [DEFORM_COLOR], "min": 0, "max": 1})
    change_km2 = common.area_km2(change, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(recent)

    confidence = round(min(0.90, 0.60 + 0.01 * baseline_count), 2)

    return {
        "tile_url": url,
        "result_image": change,
        "change_area_km2": change_km2,
        "confidence": confidence,
        "data_date": data_date,
        "recent_images_used": recent_count,
        "baseline_images_used": baseline_count,
        "headline_stat": {
            "label": "Surface change",
            "value": change_km2,
            "unit": "km²",
        },
    }
