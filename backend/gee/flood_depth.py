"""
Flood Depth Estimation.

Flood *extent* (where the water is) is only half the story for impact — a
field under 10 cm of water and a street under 3 m of water read identically on
a binary flood mask. This analysis extends flood extent with the Copernicus
GLO-30 digital elevation model to estimate how *deep* the water is.

Method (a simplified, GRD-feasible FwDET-style approach — honestly an
approximation, not a hydraulic model):
  1. Detect the flood mask exactly as the flood-extent analysis does (a >3 dB
     drop in Sentinel-1 VV backscatter against a pre-flood baseline, minus
     permanent water).
  2. Sample the terrain elevation along the flood's shoreline — the water
     surface meets dry land there, so the shoreline elevation approximates the
     local water-surface elevation.
  3. Propagate that water-surface elevation inland and subtract the ground
     elevation underneath each flooded pixel. The positive difference is the
     estimated water depth, clamped to a sane range.

Data sources: Sentinel-1 GRD (IW, VV) + COPERNICUS/DEM/GLO30.
"""

import ee
from gee import common

GLO30 = "COPERNICUS/DEM/GLO30"

# Depth is an approximation; clamp to a physically sane window so DEM noise at
# the shoreline can't produce absurd values.
_MAX_DEPTH_M = 20.0
# Radius (m) over which shoreline water-surface elevation is propagated inland.
_PROPAGATE_M = 1500


def estimate_flood_depth(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD' — the flood period to analyze

    Returns:
        tile_url, result_image, mean_depth_m, max_depth_m, flood_area_km2,
        water_volume_m3, confidence, data_date, headline_stat

    Raises:
        ValueError: if no Sentinel-1 data is available
    """
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    # --- Flood mask (same logic as flood extent) ---
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

    # --- Terrain ---
    dem = ee.ImageCollection(GLO30).select("DEM").mosaic()

    # Shoreline = flooded pixels adjacent to dry land (flood edge). The DEM there
    # is our best read on the water-surface elevation.
    eroded = flood.focal_min(radius=30, units="meters")
    shoreline = flood.subtract(eroded.unmask(0)).gt(0)
    shore_elev = dem.updateMask(shoreline)

    # Propagate the shoreline elevation inland: a neighborhood mean fills the
    # flooded interior with the nearest plausible water-surface height.
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

    # Palette: shallow teal -> deep blue, so depth reads intuitively.
    url = common.tile_url(
        depth,
        {
            "min": 0,
            "max": 5,
            "palette": ["#9BF6E4", "#00BFA8", "#1E6FE8", "#0B2A8A"],
        },
    )

    # --- Stats: mean/max depth over flooded pixels + total water volume ---
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

    # Volume = sum(depth * pixel area) over the flooded footprint.
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
