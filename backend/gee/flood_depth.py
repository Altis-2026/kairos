import ee
from gee import common

GLO30 = "COPERNICUS/DEM/GLO30"

_MAX_DEPTH_M = 20.0
_PROPAGATE_M = 1500


def estimate_flood_depth(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    post = s1.filterDate(start_date, end_date)
    post_count = common.require_images(
        post, f"this area between {start_date} and {end_date}"
    )
    pre_start, pre_end = common.baseline_window(start_date, days=30)
    pre = s1.filterDate(pre_start, pre_end)
    if pre.size().getInfo() == 0:
        pre_start, pre_end = common.baseline_window(start_date, days=60)
        pre = s1.filterDate(pre_start, pre_end)
        common.require_images(
            pre, "the pre-event baseline period (last 60 days before start date)"
        )

    diff = post.mean().subtract(pre.mean())
    flood_mask = diff.lt(-3)
    permanent = common.permanent_water_mask(75)
    flood = flood_mask.where(permanent, 0).selfMask()

    dem = ee.ImageCollection(GLO30).select("DEM").mosaic()

    eroded = flood.focal_min(radius=30, units="meters")
    shoreline = flood.subtract(eroded.unmask(0)).gt(0)
    shore_elev = dem.updateMask(shoreline)

    water_surface = shore_elev.reduceNeighborhood(
        reducer=ee.Reducer.mean(),
        kernel=ee.Kernel.circle(_PROPAGATE_M, "meters"),
    )

    depth = (
        water_surface.subtract(dem)
        .clamp(0, _MAX_DEPTH_M)
        .updateMask(flood)
        .rename("depth")
        .clip(geometry)
    )

    url = common.tile_url(
        depth,
        {
            "min": 0,
            "max": 5,
            "palette": ["#9BF6E4", "#00BFA8", "#1E6FE8", "#0B2A8A"],
        },
    )

    stats = depth.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=geometry,
        scale=30,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_depth = round(float(stats.get("depth_mean") or 0), 2)
    max_depth = round(float(stats.get("depth_max") or 0), 2)

    flood_km2 = common.area_km2(flood.selfMask().clip(geometry), geometry, band="VV", scale=30)

    vol = (
        depth.multiply(ee.Image.pixelArea())
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=30,
            maxPixels=1e10,
            bestEffort=True,
        )
        .getInfo()
    )
    water_volume_m3 = int(round(float(vol.get("depth") or 0)))

    data_date = common.latest_image_date(post)
    confidence = round(min(0.90, 0.60 + 0.02 * post_count), 2)

    return {
        "tile_url": url,
        "result_image": depth,
        "mean_depth_m": mean_depth,
        "max_depth_m": max_depth,
        "flood_area_km2": flood_km2,
        "water_volume_m3": water_volume_m3,
        "confidence": confidence,
        "data_date": data_date,
        "post_images_used": post_count,
        "headline_stat": {
            "label": "Mean flood depth",
            "value": mean_depth,
            "unit": "m",
        },
    }
