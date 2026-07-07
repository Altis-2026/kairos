from gee import common


def detect_flood(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"this area between {start_date} and {end_date}"
    )

    pre_start, pre_end = common.baseline_window(start_date, days=30)
    pre = s1.filterDate(pre_start, pre_end)
    pre_count = pre.size().getInfo()
    if pre_count == 0:
        pre_start, pre_end = common.baseline_window(start_date, days=60)
        pre = s1.filterDate(pre_start, pre_end)
        pre_count = common.require_images(
            pre, "the pre-event baseline period (last 60 days before start date)"
        )

    post_mean = post.mean()
    pre_mean = pre.mean()

    diff = post_mean.subtract(pre_mean)
    flood_mask = diff.lt(-3)

    permanent = common.permanent_water_mask(75)
    new_flood = flood_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(new_flood, {"palette": [common.TEAL], "min": 0, "max": 1})
    flood_km2 = common.area_km2(new_flood, geometry, band="VV", scale=30)
    data_date = common.latest_image_date(post)

    confidence = round(min(0.95, 0.70 + 0.02 * post_count), 2)

    return {
        "tile_url": url,
        "result_image": new_flood,
        "flood_area_km2": flood_km2,
        "confidence": confidence,
        "data_date": data_date,
        "post_images_used": post_count,
        "pre_images_used": pre_count,
        "headline_stat": {"label": "Flood extent", "value": flood_km2, "unit": "km²"},
    }
