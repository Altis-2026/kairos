"""
Urban Growth / New Construction Monitoring.

New buildings, roads and infrastructure are some of the brightest things in a
radar scene: their hard right-angled surfaces act as corner reflectors that
bounce the signal straight back to the satellite. Bare land, fields and water
are comparatively dark. So when land is built on, its VV backscatter jumps and
stays high.

Method:
Compare a recent window against a baseline ~12 months earlier and flag pixels
whose VV backscatter rose by more than a threshold and that are now bright
enough to be built structures (filtering out, e.g., a wet field drying out).
The persistent brightening pattern of construction is distinct from transient
seasonal change.

Data source: Sentinel-1 GRD (IW, VV).
"""

from datetime import datetime, timedelta
from gee import common

# Required VV increase (dB) from baseline to recent to count as new structure.
_RISE_THRESHOLD_DB = 3.0
# The recent return must also be at least this bright (dB) — real built surfaces
# are strong reflectors, which screens out dark-to-less-dark noise.
_BRIGHT_FLOOR_DB = -12.0
# Construction amber.
URBAN_COLOR = "#E8A318"


def detect_urban_growth(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the recent window to test for new build

    Returns:
        tile_url, result_image, new_builtup_km2, confidence, data_date,
        recent_images_used, baseline_images_used, headline_stat

    Raises:
        ValueError: if no Sentinel-1 data is available
    """
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    recent = s1.filterDate(start_date, end_date)
    recent_count = common.require_images(
        recent, f"this area between {start_date} and {end_date}"
    )

    # Baseline: a window of equal-ish length ending ~12 months before start.
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    base_end = start_dt - timedelta(days=365)
    base_start = base_end - timedelta(days=90)
    baseline = s1.filterDate(
        base_start.strftime("%Y-%m-%d"), base_end.strftime("%Y-%m-%d")
    )
    if baseline.size().getInfo() == 0:
        # Fall back to 18 months back if the 12-month window is empty.
        base_end = start_dt - timedelta(days=540)
        base_start = base_end - timedelta(days=120)
        baseline = s1.filterDate(
            base_start.strftime("%Y-%m-%d"), base_end.strftime("%Y-%m-%d")
        )
    baseline_count = common.require_images(
        baseline, "the ~12-month-prior construction baseline"
    )

    recent_mean = recent.mean()
    base_mean = baseline.mean()

    rise = recent_mean.subtract(base_mean)
    new_build = (
        rise.gt(_RISE_THRESHOLD_DB)
        .And(recent_mean.gt(_BRIGHT_FLOOR_DB))
    )

    # Exclude permanent water (rough water can brighten transiently).
    permanent = common.permanent_water_mask(50)
    new_build = new_build.where(permanent, 0).selfMask().rename("VV").clip(geometry)

    url = common.tile_url(new_build, {"palette": [URBAN_COLOR], "min": 0, "max": 1})
    new_km2 = common.area_km2(new_build, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(recent)

    confidence = round(min(0.88, 0.60 + 0.02 * baseline_count), 2)

    return {
        "tile_url": url,
        "result_image": new_build,
        "new_builtup_km2": new_km2,
        "confidence": confidence,
        "data_date": data_date,
        "recent_images_used": recent_count,
        "baseline_images_used": baseline_count,
        "headline_stat": {
            "label": "New built-up area",
            "value": new_km2,
            "unit": "km²",
        },
    }
