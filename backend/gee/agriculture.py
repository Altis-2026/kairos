import ee
from gee import common

_VEG_THRESHOLD = 0.5
RVI_PALETTE = ["#C2A878", "#D9E07E", "#7BC043", "#1E7A33", "#0B3D1A"]


def _to_linear(img, band):
    return ee.Image(10.0).pow(img.select(band).divide(10.0))


def monitor_crops(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)

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
