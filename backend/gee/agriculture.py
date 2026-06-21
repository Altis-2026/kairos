"""
Agriculture / Crop Vigour Monitoring (Radar Vegetation Index).

Optical crop indices like NDVI are the standard — but they go blind under the
clouds that sit over farmland for weeks at a time in monsoon and temperate
climates. Radar doesn't care about clouds, so it can track crops continuously.

Method (Radar Vegetation Index):
A growing crop canopy scatters radar in many directions ("volume scattering"),
which raises the cross-polarised VH return relative to the co-polarised VV
return; bare soil and water do the opposite. The dual-pol RVI captures this:

    RVI = 4 · σ°VH / (σ°VV + σ°VH)        (computed in linear power, not dB)

RVI runs from near 0 over bare soil / water to ~0.7–1 over a dense canopy, so
the map reads directly as crop vigour. We also report mean RVI and the area of
actively vegetated ground in the footprint.

Data source: Sentinel-1 GRD (IW, VV + VH).
"""

import ee
from gee import common

# RVI above this counts a pixel as actively vegetated (crops/canopy vs bare/water).
_VEG_THRESHOLD = 0.5
# Bare-soil tan -> vigorous green, so the map reads as a crop-health gradient.
RVI_PALETTE = ["#C2A878", "#D9E07E", "#7BC043", "#1E7A33", "#0B3D1A"]


def _to_linear(img, band):
    """Sentinel-1 GRD bands are in dB; RVI must be computed in linear power."""
    return ee.Image(10.0).pow(img.select(band).divide(10.0))


def monitor_crops(bbox: list, start_date: str, end_date: str) -> dict:
    """
    Args:
        bbox: [min_lon, min_lat, max_lon, max_lat]
        start_date / end_date: 'YYYY-MM-DD'

    Returns:
        tile_url, result_image, mean_rvi, vegetated_area_km2, confidence,
        data_date, images_used, headline_stat

    Raises:
        ValueError: if no dual-pol Sentinel-1 data is available
    """
    geometry = common.bbox_geometry(bbox)

    # Need BOTH polarisations for RVI, so build the collection directly.
    coll = (
        ee.ImageCollection(common.S1_COLLECTION)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    count = common.require_images(
        coll, f"dual-pol (VV+VH) coverage of this area between {start_date} and {end_date}"
    )

    composite = coll.mean()
    vv_lin = _to_linear(composite, "VV")
    vh_lin = _to_linear(composite, "VH")

    rvi = (
        vh_lin.multiply(4.0)
        .divide(vv_lin.add(vh_lin))
        .clamp(0, 1)
        .rename("rvi")
        .clip(geometry)
    )

    url = common.tile_url(rvi, {"min": 0, "max": 1, "palette": RVI_PALETTE})

    mean_stats = rvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=30,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_rvi = round(float(mean_stats.get("rvi") or 0), 3)

    vegetated = rvi.gt(_VEG_THRESHOLD).selfMask().rename("rvi").clip(geometry)
    veg_km2 = common.area_km2(vegetated, geometry, band="rvi", scale=30)

    data_date = common.latest_image_date(coll)
    confidence = round(min(0.90, 0.65 + 0.02 * count), 2)

    return {
        "tile_url": url,
        "result_image": vegetated,
        "mean_rvi": mean_rvi,
        "vegetated_area_km2": veg_km2,
        "confidence": confidence,
        "data_date": data_date,
        "images_used": count,
        "headline_stat": {
            "label": "Vegetated cropland",
            "value": veg_km2,
            "unit": "km²",
        },
    }
