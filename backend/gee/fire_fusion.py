import ee

from gee import common

HOTSPOT_KELVIN = 325


def fuse_fire(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VH")

    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"this area between {start_date} and {end_date}"
    )
    pre_start, pre_end = common.baseline_window(start_date, days=60)
    pre = s1.filterDate(pre_start, pre_end)
    pre_count = common.require_images(pre, "the pre-fire baseline period")

    permanent = common.permanent_water_mask(50)
    scar = (
        post.mean()
        .subtract(pre.mean())
        .gt(2.5)
        .where(permanent, 0)
        .rename("f")
    )

    thermal = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2"))
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .select("ST_B10")
    )
    thermal_count = int(thermal.size().getInfo())

    hotspot_km2 = 0.0
    max_temp_c = None
    if thermal_count > 0:
        surface_k = thermal.max().multiply(0.00341802).add(149)
        hot = surface_k.gt(HOTSPOT_KELVIN).rename("f")
        fused = scar.unmask(0).add(hot.unmask(0).multiply(2))
        hot_masked = hot.selfMask().clip(geometry)
        hotspot_km2 = common.area_km2(hot_masked, geometry, band="f", scale=30)
        temp_stats = (
            surface_k.clip(geometry)
            .reduceRegion(
                reducer=ee.Reducer.max(),
                geometry=geometry,
                scale=60,
                maxPixels=1e10,
                bestEffort=True,
            )
            .getInfo()
        )
        max_k = temp_stats.get("ST_B10")
        if max_k is not None:
            max_temp_c = round(float(max_k) - 273.15, 1)
    else:
        fused = scar.unmask(0)

    fused = fused.selfMask().clip(geometry)
    url = common.tile_url(
        fused,
        {"palette": ["#E8541E", "#FFD166", "#FF3B5C"], "min": 1, "max": 3},
    )

    scar_masked = scar.selfMask().clip(geometry)
    scar_km2 = common.area_km2(scar_masked, geometry, band="f", scale=30)

    return {
        "tile_url": url,
        "result_image": fused,
        "burn_scar_km2": scar_km2,
        "hotspot_km2": hotspot_km2,
        "max_surface_temp_c": max_temp_c,
        "thermal_scenes_used": thermal_count,
        "confidence": round(min(0.9, 0.65 + 0.02 * post_count), 2),
        "data_date": common.latest_image_date(post),
        "post_images_used": post_count,
        "pre_images_used": pre_count,
        "headline_stat": {
            "label": "Burn scar area",
            "value": scar_km2,
            "unit": "km²",
        },
    }
