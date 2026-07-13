"""
Flood Extent Mapping.

Method (per the Kairos spec):
Water reflects radar away from the satellite, so flooded land appears
anomalously dark in Sentinel-1 VV backscatter. We compare the flood period
against a pre-flood baseline and flag pixels that dropped by more than 3 dB,
then remove permanent water so only NEW inundation is shown.

Rigour upgrades layered on the core method:
- Speckle suppression: temporal multi-look (window mean) plus a 50 m focal
  median despeckle on both composites before differencing (UN-SPIDER practice).
- Uncertainty: the detection is re-run at -2.5/-3/-3.5 dB and the area spread
  is reported; threshold-fragile results lose confidence.
- Optical fusion: where cloud-free Sentinel-2 exists in the window, the SAR
  flood mask is checked against NDWI water and the agreement adjusts
  confidence. Clouds are expected — the SAR result stands alone without it.

Data source: Sentinel-1 GRD, IW mode, VV polarization.
"""

from gee import common, fusion

# Ensemble members around the primary -3 dB drop threshold.
_THRESHOLDS = [-2.5, -3.0, -3.5]


def detect_flood(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the flood period to analyze

    Returns:
        tile_url, flood_area_km2, confidence, data_date,
        post_images_used, pre_images_used, uncertainty, optical stats

    Raises:
        ValueError: if no Sentinel-1 data is available
    """
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    # --- Post-event (flood period) ---
    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"this area between {start_date} and {end_date}"
    )

    # --- Pre-event baseline: 30 days before, extend to 60 if empty ---
    pre_start, pre_end = common.baseline_window(start_date, days=30)
    pre = s1.filterDate(pre_start, pre_end)
    pre_count = pre.size().getInfo()
    if pre_count == 0:
        pre_start, pre_end = common.baseline_window(start_date, days=60)
        pre = s1.filterDate(pre_start, pre_end)
        pre_count = common.require_images(
            pre, "the pre-event baseline period (last 60 days before start date)"
        )

    # Temporal multi-look, then spatial despeckle, then difference
    post_mean = common.despeckle(post.mean())
    pre_mean = common.despeckle(pre.mean())
    diff = post_mean.subtract(pre_mean)

    # Backscatter drop > 3 dB => likely new surface water
    flood_mask = diff.lt(-3)

    # Remove permanent water bodies (rivers, lakes, ocean)
    permanent = common.permanent_water_mask(75)
    new_flood = flood_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(new_flood, {"palette": [common.TEAL], "min": 0, "max": 1})
    flood_km2 = common.area_km2(new_flood, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(post)

    # Uncertainty: how much does the answer move when the threshold moves?
    uncertainty = common.ensemble_area(
        diff,
        _THRESHOLDS,
        geometry,
        band="VV",
        exclude_mask=permanent,
        direction="lt",
        scale=30,
    )

    # Confidence: more passes = better composite; fragile thresholds cost it.
    base_conf = min(0.95, 0.70 + 0.02 * post_count)
    confidence = max(0.3, base_conf - common.spread_penalty(uncertainty["relative_spread"]))

    # Optical cross-check (best-effort; clouds are the norm during floods)
    optical = {}
    try:
        optical = fusion.confirm_water(new_flood, geometry, start_date, end_date)
        confidence += fusion.confidence_adjustment(
            optical.get("optical_agreement_pct"),
            optical.get("optical_coverage_pct", 0),
        )
    except Exception:
        optical = {"optical_confirmation": "unavailable (no cloud-free Sentinel-2)"}

    return {
        "tile_url": url,
        "result_image": new_flood,
        "flood_area_km2": flood_km2,
        "confidence": round(min(0.97, max(0.3, confidence)), 2),
        "data_date": data_date,
        "post_images_used": post_count,
        "pre_images_used": pre_count,
        "flood_area_low_km2": uncertainty["area_low_km2"],
        "flood_area_high_km2": uncertainty["area_high_km2"],
        "threshold_spread": uncertainty["relative_spread"],
        **optical,
        "headline_stat": {"label": "Flood extent", "value": flood_km2, "unit": "km²"},
    }
