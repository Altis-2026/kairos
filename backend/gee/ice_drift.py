from datetime import datetime

import ee

from gee import common


def track_ice_drift(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="HH", instrument_mode="EW")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = max((end_dt - start_dt).days, 2)
    mid_dt = start_dt + (end_dt - start_dt) / 2
    mid = mid_dt.strftime("%Y-%m-%d")

    early = s1.filterDate(start_date, mid)
    late = s1.filterDate(mid, end_date)
    early_count = common.require_images(
        early,
        f"the first half of the window ({start_date} to {mid}); drift tracking "
        "needs polar EW-mode passes in both halves of the date range",
    )
    late_count = common.require_images(
        late,
        f"the second half of the window ({mid} to {end_date}); drift tracking "
        "needs polar EW-mode passes in both halves of the date range",
    )

    reference = early.mean().clip(geometry)
    target = late.mean().clip(geometry)

    displacement = target.displacement(
        referenceImage=reference, maxOffset=20000.0, patchWidth=8000.0
    )
    gap_days = max(total_days / 2.0, 1.0)
    speed = (
        displacement.select("dx")
        .hypot(displacement.select("dy"))
        .divide(1000.0 * gap_days)
        .rename("drift")
    )

    ice = target.gt(-18)
    speed = speed.updateMask(ice).clip(geometry)

    stats = speed.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=geometry,
        scale=400,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_speed = round(float(stats.get("drift_mean") or 0), 2)
    max_speed = round(float(stats.get("drift_max") or 0), 2)

    url = common.tile_url(
        speed,
        {
            "palette": ["#0B3B5C", "#1E6FE8", "#00BFA8", "#BFEFFF", "#FFFFFF"],
            "min": 0,
            "max": 15,
        },
    )

    return {
        "tile_url": url,
        "result_image": speed,
        "mean_drift_km_day": mean_speed,
        "max_drift_km_day": max_speed,
        "tracking_gap_days": round(gap_days, 1),
        "confidence": round(min(0.78, 0.5 + 0.03 * min(early_count, late_count)), 2),
        "data_date": common.latest_image_date(late),
        "early_images_used": early_count,
        "late_images_used": late_count,
        "headline_stat": {
            "label": "Mean ice drift",
            "value": mean_speed,
            "unit": "km/day",
        },
    }
