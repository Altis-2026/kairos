"""
Earthquake / Building Damage Assessment (SAR change proxy).

After a major earthquake (or explosion, conflict strike, etc.) the single most
urgent question is *which neighbourhoods are flattened* — and the answer is
needed within hours, through the dust, smoke and cloud that blind optical
satellites. Radar sees through all of it.

Method (a GRD-feasible damage proxy, not InSAR coherence):
Intact buildings act as stable corner reflectors with a characteristic, steady
radar signature. When a building collapses, that signature changes abruptly —
the double-bounce return is destroyed and replaced by rubble with a different
roughness. We therefore:
  1. Composite a short PRE-event window and a short POST-event window.
  2. Measure the per-pixel magnitude of backscatter change |post - pre|.
  3. Restrict attention to built-up areas (JRC GHSL built-up surface), because
     a damage map is only meaningful where there are structures.
  4. Flag built-up pixels whose change exceeds a threshold as likely-damaged.

This is honestly a rapid amplitude change detector focused on settlements; it
flags candidate damage for responders to prioritise, not a verified census.

Data sources: Sentinel-1 GRD (IW, VV) + JRC/GHSL/P2023A/GHS_BUILT_S.
"""

import ee
from datetime import datetime, timedelta
from gee import common

GHSL_BUILT = "JRC/GHSL/P2023A/GHS_BUILT_S"
_BUILT_EPOCH = "2020"

# Built-up surface (m² per ~100 m pixel) above which a pixel counts as settled.
_BUILT_THRESHOLD = 1000
# Backscatter change (dB) beyond which a built-up pixel is flagged as damaged.
_CHANGE_THRESHOLD_DB = 4.0
# Damage red — distinct from the fire orange and deformation purple.
DAMAGE_COLOR = "#FF3B5C"


def assess_damage(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date: 'YYYY-MM-DD' — the event date (post-event window starts here)
        end_date: 'YYYY-MM-DD'   — end of the post-event window

    Returns:
        tile_url, result_image, damaged_area_km2, confidence, data_date,
        pre_images_used, post_images_used, headline_stat

    Raises:
        ValueError: if no Sentinel-1 data is available
    """
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    # --- Post-event window (event onward) ---
    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"the post-event window {start_date} to {end_date}"
    )

    # --- Pre-event window: the 30 days before the event, widening to 60 ---
    pre_start, pre_end = common.baseline_window(start_date, days=30)
    pre = s1.filterDate(pre_start, pre_end)
    if pre.size().getInfo() == 0:
        pre_start, pre_end = common.baseline_window(start_date, days=60)
        pre = s1.filterDate(pre_start, pre_end)
    pre_count = common.require_images(
        pre, "the pre-event baseline (30–60 days before the event date)"
    )

    # Absolute backscatter change — collapse changes the signature in either
    # direction (loss of double-bounce, or rubble brightening).
    change_db = post.mean().subtract(pre.mean()).abs()

    # Restrict to built-up settlements.
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
