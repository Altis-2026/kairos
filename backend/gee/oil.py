"""
Oil Spill Detection.

Method (per the Kairos spec):
Oil films suppress the capillary waves that produce ocean radar backscatter,
so oil-covered water appears anomalously DARK against the surrounding sea.
We threshold low ocean backscatter relative to local statistics.

Caveat encoded in confidence: very low wind also darkens the ocean,
so detections in calm conditions can be false positives.

Data source: Sentinel-1 GRD, IW mode, VV polarization.
"""

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

    # Restrict to ocean / permanent water
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

    # Dark anomalies: more than 2 stddev below the local ocean mean
    threshold = mean.subtract(std.multiply(2))
    slick = ocean_vv.lt(ee.Image.constant(threshold)).selfMask().clip(geometry)

    url = common.tile_url(slick, {"palette": ["#7B61FF"], "min": 0, "max": 1})
    slick_km2 = common.area_km2(slick, geometry, band="VV", scale=50)
    data_date = common.latest_image_date(period)

    return {
        "tile_url": url,
        "result_image": slick,
        "suspected_oil_km2": slick_km2,
        "confidence": 0.70,  # low-wind false positives are inherent to this method
        "data_date": data_date,
        "images_used": image_count,
        "headline_stat": {"label": "Suspected oil coverage", "value": slick_km2, "unit": "km²"},
    }
