"""
Deforestation and Forest Loss.

Method (per the Kairos spec):
Intact forest canopy produces consistent VH backscatter over time. Clearing
the forest changes the surface fundamentally: backscatter shifts and temporal
variance spikes. We compare the analysis period's mean VH against a 12-month
historical baseline and flag significant drops (canopy removal lowers VH).

Data source: Sentinel-1 GRD, IW mode, VH polarization time series.
"""

from datetime import datetime, timedelta
from gee import common


def detect_deforestation(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VH")

    current = s1.filterDate(start_date, end_date)
    current_count = common.require_images(
        current, f"this area between {start_date} and {end_date}"
    )

    # 12-month historical baseline before the analysis window
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    base_end = start_dt - timedelta(days=1)
    base_start = base_end - timedelta(days=365)
    baseline = s1.filterDate(
        base_start.strftime("%Y-%m-%d"), base_end.strftime("%Y-%m-%d")
    )
    baseline_count = common.require_images(
        baseline, "the 12-month historical baseline"
    )

    # Multi-look both windows, despeckle, then difference (see common.despeckle)
    diff = common.despeckle(current.mean()).subtract(
        common.despeckle(baseline.mean())
    )

    # Canopy loss: VH drop of more than 3 dB vs the annual baseline
    loss_mask = diff.lt(-3)

    permanent = common.permanent_water_mask(50)
    loss = loss_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(loss, {"palette": ["#E84855"], "min": 0, "max": 1})
    loss_km2 = common.area_km2(loss, geometry, band="VH", scale=30)
    data_date = common.latest_image_date(current)

    return {
        "tile_url": url,
        "result_image": loss,
        "forest_loss_km2": loss_km2,
        "confidence": round(min(0.90, 0.65 + 0.015 * current_count), 2),
        "data_date": data_date,
        "current_images_used": current_count,
        "baseline_images_used": baseline_count,
        "headline_stat": {"label": "Forest loss", "value": loss_km2, "unit": "km²"},
    }
