import ee
from gee import common


def detect_oil_spill(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    period = s1.filterDate(start_date, end_date)
    image_count = common.require_images(
        period, f"this area between {start_date} and {end_date}"
    )

    latest = ee.Image(period.sort("system:time_start", False).first())

    water = common.permanent_water_mask(50)
    ocean_vv = latest.updateMask(water)

    stats = ocean_vv.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=geometry,
        scale=100,
        maxPixels=1e10,
        bestEffort=True,
    )
    mean = ee.Number(stats.get("VV_mean"))
    std = ee.Number(stats.get("VV_stdDev"))

    threshold = mean.subtract(std.multiply(2))
    slick = ocean_vv.lt(ee.Image.constant(threshold)).selfMask().clip(geometry)

    url = common.tile_url(slick, {"palette": ["#7B61FF"], "min": 0, "max": 1})
    slick_km2 = common.area_km2(slick, geometry, band="VV", scale=50)
    data_date = common.latest_image_date(period)

    return {
        "tile_url": url,
        "result_image": slick,
        "suspected_oil_km2": slick_km2,
        "confidence": 0.70,
        "data_date": data_date,
        "images_used": image_count,
        "headline_stat": {"label": "Suspected oil coverage", "value": slick_km2, "unit": "km²"},
    }
