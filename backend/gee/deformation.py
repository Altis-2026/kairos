"""
Surface Deformation / Change Detection (amplitude coherence proxy).

Method:
True InSAR measures the *phase* of the radar wave to detect millimetre-scale
ground movement, but Sentinel-1 GRD (the only Sentinel-1 product on Earth
Engine) ships amplitude only — the phase is discarded during ground-range
detection. So instead of phase interferometry we use an *amplitude temporal
coherence* proxy, which is the standard GRD-feasible technique:

  1. Build a 12-month baseline and measure, per pixel, how *stable* the VV
     backscatter is (its mean and standard deviation over time). Man-made and
     bare-rock surfaces are temporally stable (low σ); they are the pixels
     where a real change is meaningful.
  2. Compare the recent window's mean against that baseline. A pixel that
     deviates from its own historical mean by more than `Z_THRESHOLD` baseline
     standard deviations has undergone a genuine surface change — subsidence,
     construction, landslide scarring, ground disturbance — rather than normal
     seasonal noise.

This is honestly an amplitude change detector, not phase InSAR; the methodology
report states this explicitly. It still surfaces the same events of interest
(subsidence, sinkholes, ground strain) where they alter surface roughness.

Data source: Sentinel-1 GRD, IW mode, VV polarization time series.
"""

from datetime import datetime, timedelta
from gee import common

# A pixel must deviate from its own historical mean by more than this many
# baseline standard deviations to count as a genuine surface change.
Z_THRESHOLD = 2.0

# Floor for the baseline σ (dB). Perfectly stable pixels would otherwise give a
# near-zero denominator and explode the z-score; this keeps it well-behaved.
_SIGMA_FLOOR = 0.5

# Purple reads as "ground movement" and stays distinct from the teal/amber and
# water palettes already on the globe.
DEFORM_COLOR = "#C77DFF"


def detect_deformation(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the recent window to test

    Returns:
        tile_url, result_image, change_area_km2, confidence, data_date,
        recent_images_used, baseline_images_used, headline_stat

    Raises:
        ValueError: if no Sentinel-1 data is available
    """
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    # --- Recent window ---
    recent = s1.filterDate(start_date, end_date)
    recent_count = common.require_images(
        recent, f"this area between {start_date} and {end_date}"
    )

    # --- 12-month stability baseline before the recent window ---
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
    # Per-pixel temporal standard deviation = how noisy this pixel normally is.
    base_sigma = baseline.reduce("stdDev").rename("VV").max(_SIGMA_FLOOR)

    recent_mean = recent.mean()

    # z = (recent - historical mean) / historical σ. Magnitude > threshold means
    # the surface changed beyond its own normal variability.
    z = recent_mean.subtract(base_mean).divide(base_sigma).abs()
    change_mask = z.gt(Z_THRESHOLD)

    # Permanent water is always "changing" to SAR (waves); exclude it.
    permanent = common.permanent_water_mask(50)
    change = change_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(change, {"palette": [DEFORM_COLOR], "min": 0, "max": 1})
    change_km2 = common.area_km2(change, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(recent)

    # More baseline scenes => a more trustworthy stability estimate.
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
