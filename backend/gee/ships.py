"""
Ship Detection.

Method (per the Kairos spec):
Ship hulls act as corner reflectors and appear as anomalously bright points
on an otherwise dark ocean. We implement a CFAR-style adaptive detector:
a pixel is a detection when it exceeds the local ocean statistics
(mean + k * stddev) computed over the AOI, restricted to water.

Data source: Sentinel-1 GRD, IW mode, VV polarization.
Output: tile layer of detections + vessel count + detection centroids (GeoJSON).
"""

import ee
from gee import common


def detect_ships(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    period = s1.filterDate(start_date, end_date)
    image_count = common.require_images(
        period, f"this area between {start_date} and {end_date}"
    )

    # Use the most recent acquisition (ships move; compositing smears them)
    latest = ee.Image(period.sort("system:time_start", False).first())

    # Restrict to water: JRC occurrence > 50% covers ocean + large rivers/lakes
    water = common.permanent_water_mask(50)
    ocean_vv = latest.updateMask(water)

    # Local ocean statistics over the AOI
    stats = ocean_vv.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=geometry,
        scale=100,
        maxPixels=1e10,
        bestEffort=True,
    )
    mean = ee.Number(stats.get("VV_mean"))
    std = ee.Number(stats.get("VV_stdDev"))

    # CFAR-style threshold: bright outliers are vessels. k=5 keeps false alarms low.
    threshold = mean.add(std.multiply(5))
    detections = ocean_vv.gt(ee.Image.constant(threshold)).selfMask().clip(geometry)

    url = common.tile_url(detections, {"palette": [common.AMBER], "min": 0, "max": 1})

    # Vectorize detections to count vessels and return their positions
    vectors = detections.reduceToVectors(
        geometry=geometry,
        scale=50,
        geometryType="centroid",
        maxPixels=1e10,
        bestEffort=True,
    )
    vessel_count = vectors.size().getInfo()

    # Centroid coordinates for the frontend point layer (cap at 500 for payload size)
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
