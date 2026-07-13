"""
Wildfire Burn Scar Mapping.

Method (per the Kairos spec):
Fire removes vegetation and exposes bare rough soil, which INCREASES
VH backscatter relative to the pre-fire state. We compare the post-fire
period to a pre-fire baseline and flag pixels with a significant VH rise.
Works through smoke that blinds optical satellites.

Rigour upgrades layered on the core method:
- Speckle suppression: 50 m focal median despeckle on both multi-looked
  composites before differencing.
- Uncertainty: re-run at +2/+2.5/+3 dB, report the area spread, and dock
  confidence for threshold-fragile results.
- Optical fusion: when cloud-free Sentinel-2 exists both pre- and post-fire,
  the SAR scar is checked against dNBR and agreement adjusts confidence.

Data source: Sentinel-1 GRD, IW mode, VH polarization.
"""

from gee import common, fusion

_THRESHOLDS = [2.0, 2.5, 3.0]


def detect_burn_scar(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VH")

    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"this area between {start_date} and {end_date}"
    )

    pre_start, pre_end = common.baseline_window(start_date, days=60)
    pre = s1.filterDate(pre_start, pre_end)
    pre_count = common.require_images(pre, "the pre-fire baseline period")

    diff = common.despeckle(post.mean()).subtract(common.despeckle(pre.mean()))

    # Burned areas: VH backscatter rise of more than 2.5 dB
    burn_mask = diff.gt(2.5)

    # Exclude water (low backscatter, irrelevant for fire)
    permanent = common.permanent_water_mask(50)
    burn = burn_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(burn, {"palette": ["#E8541E"], "min": 0, "max": 1})
    burn_km2 = common.area_km2(burn, geometry, band="VH", scale=30)
    data_date = common.latest_image_date(post)

    uncertainty = common.ensemble_area(
        diff,
        _THRESHOLDS,
        geometry,
        band="VH",
        exclude_mask=permanent,
        direction="gt",
        scale=30,
    )

    base_conf = min(0.92, 0.68 + 0.02 * post_count)
    confidence = max(0.3, base_conf - common.spread_penalty(uncertainty["relative_spread"]))

    optical = {}
    try:
        optical = fusion.confirm_burn(
            burn, geometry, start_date, end_date, pre_start, pre_end
        )
        confidence += fusion.confidence_adjustment(
            optical.get("optical_agreement_pct"),
            optical.get("optical_coverage_pct", 0),
        )
    except Exception:
        optical = {"optical_confirmation": "unavailable (no cloud-free Sentinel-2)"}

    return {
        "tile_url": url,
        "result_image": burn,
        "burn_area_km2": burn_km2,
        "confidence": round(min(0.97, max(0.3, confidence)), 2),
        "data_date": data_date,
        "post_images_used": post_count,
        "pre_images_used": pre_count,
        "burn_area_low_km2": uncertainty["area_low_km2"],
        "burn_area_high_km2": uncertainty["area_high_km2"],
        "threshold_spread": uncertainty["relative_spread"],
        **optical,
        "headline_stat": {"label": "Burn scar area", "value": burn_km2, "unit": "km²"},
    }
