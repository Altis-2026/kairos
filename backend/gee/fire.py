from gee import common


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

    diff = post.mean().subtract(pre.mean())

    burn_mask = diff.gt(2.5)

    permanent = common.permanent_water_mask(50)
    burn = burn_mask.where(permanent, 0).selfMask().clip(geometry)

    url = common.tile_url(burn, {"palette": ["#E8541E"], "min": 0, "max": 1})
    burn_km2 = common.area_km2(burn, geometry, band="VH", scale=30)
    data_date = common.latest_image_date(post)

    return {
        "tile_url": url,
        "result_image": burn,
        "burn_area_km2": burn_km2,
        "confidence": round(min(0.92, 0.68 + 0.02 * post_count), 2),
        "data_date": data_date,
        "post_images_used": post_count,
        "pre_images_used": pre_count,
        "headline_stat": {"label": "Burn scar area", "value": burn_km2, "unit": "km²"},
    }
