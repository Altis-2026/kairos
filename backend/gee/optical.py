"""
Sentinel-2 optical imagery — true-color context for SAR analyses.

Pure radar is powerful but visually abstract. Pairing a SAR result with a
true-color optical image from a nearby date makes interpretation far easier for
non-experts. We pick the least-cloudy Sentinel-2 scene in the window. When none
is clear enough, we raise a user-facing message that doubles as the pitch for
why Kairos uses radar in the first place: optical can't see through cloud.

Data source: COPERNICUS/S2_SR_HARMONIZED (free, on Earth Engine).
"""

import ee
from gee import common

S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"


def optical_image(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD'

    Returns:
        dict: tile_url, data_date, cloud_percent

    Raises:
        ValueError: if no sufficiently cloud-free optical scene is available.
    """
    geometry = common.bbox_geometry(bbox)
    collection = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    if collection.size().getInfo() == 0:
        raise ValueError(
            "No clear Sentinel-2 optical imagery for this area and time window. "
            "Optical satellites can't see through clouds — which is exactly why "
            "Kairos analyses run on radar instead."
        )

    best = ee.Image(collection.first())
    rgb = best.select(["B4", "B3", "B2"]).clip(geometry)
    url = common.tile_url(
        rgb, {"min": 0, "max": 3000, "bands": ["B4", "B3", "B2"]}
    )

    data_date = (
        ee.Date(best.get("system:time_start")).format("YYYY-MM-dd").getInfo()
    )
    cloud = best.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()

    return {
        "tile_url": url,
        "data_date": data_date,
        "cloud_percent": round(float(cloud), 1),
    }
