import ee
from gee import common


def detect_ships(bbox: list, start_date: str, end_date: str) -> dict:
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

    threshold = mean.add(std.multiply(5))
    detections = ocean_vv.gt(ee.Image.constant(threshold)).selfMask().clip(geometry)

    url = common.tile_url(detections, {"palette": [common.AMBER], "min": 0, "max": 1})

    vectors = detections.reduceToVectors(
        geometry=geometry,
        scale=50,
        geometryType="centroid",
        maxPixels=1e10,
        bestEffort=True,
    )
    vessel_count = vectors.size().getInfo()

    features = vectors.limit(500).getInfo().get("features", [])
    vessel_points = [
        {
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {"id": i},
        }
        for i, f in enumerate(features)
    ]

    data_date = common.latest_image_date(period)

    return {
        "tile_url": url,
        "result_image": detections,
        "vessel_count": vessel_count,
        "vessel_points": {"type": "FeatureCollection", "features": vessel_points},
        "confidence": 0.82,
        "data_date": data_date,
        "images_used": image_count,
        "headline_stat": {"label": "Vessels detected", "value": vessel_count, "unit": ""},
    }
