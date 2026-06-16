"""
Flood Extent Mapping.

Method (per the Kairos spec):
Water reflects radar away from the satellite, so flooded land appears
anomalously dark in Sentinel-1 VV backscatter. We compare the flood period
against a pre-flood baseline and flag pixels that dropped by more than 3 dB,
then remove permanent water so only NEW inundation is shown.

Data source: Sentinel-1 GRD, IW mode, VV polarization.
"""

from gee import common


def detect_flood(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the flood period to analyze

    Returns:
        tile_url, flood_area_km2, confidence, data_date,
        post_images_used, pre_images_used

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

    # Mean composites suppress speckle noise inherent to SAR
    post_mean = post.mean()
    pre_mean = pre.mean()

    # Backscatter drop > 3 dB => likely new surface water
    diff = post_mean.subtract(pre_mean)
    flood_mask = diff.lt(-3)

    # Remove permanent water bodies (rivers, lakes, ocean)
    permanent = common.permanent_water_mask(75)
    new_flood = flood_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(new_flood, {"palette": [common.TEAL], "min": 0, "max": 1})
    flood_km2 = common.area_km2(new_flood, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(post)

    # Confidence heuristic: more post-event acquisitions = more reliable composite
    confidence = round(min(0.95, 0.70 + 0.02 * post_count), 2)

    return {
        "tile_url": url,
        "flood_area_km2": flood_km2,
        "confidence": confidence,
        "data_date": data_date,
        "post_images_used": post_count,
        "pre_images_used": pre_count,
        "headline_stat": {"label": "Flood extent", "value": flood_km2, "unit": "km²"},
    }
