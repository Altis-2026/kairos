import ee

from gee import common

WORLDCOVER = "ESA/WorldCover/v200"
_EXCLUDED_CLASSES = [10, 50, 70, 80]

_PALETTE = ["#8B5A2B", "#C9A227", "#E8EFE9", "#7FD8CC", "#00BFA8"]


def estimate_soil_moisture(bbox: list, start_date: str, end_date: str) -> dict:
    geometry = common.bbox_geometry(bbox)
    s1 = common.s1_collection(geometry, polarization="VV")

    current = s1.filterDate(start_date, end_date)
    current_count = common.require_images(current, f"this area between {start_date} and {end_date}")

    hist_start, _ = common.baseline_window(start_date, days=365)
    history = s1.filterDate(hist_start, end_date)
    common.require_images(history, "the 12-month reference archive")

    p = history.reduce(ee.Reducer.percentile([5, 95]))
    sigma_dry = p.select("VV_p5")
    sigma_wet = p.select("VV_p95")
    span = sigma_wet.subtract(sigma_dry)

    now = common.despeckle(current.mean())
    index = now.subtract(sigma_dry).divide(span).clamp(0, 1).updateMask(span.gt(1.5)).rename("moisture")

    landcover = ee.ImageCollection(WORLDCOVER).first().select("Map")
    valid_cover = landcover.neq(_EXCLUDED_CLASSES[0])
    for cls in _EXCLUDED_CLASSES[1:]:
        valid_cover = valid_cover.And(landcover.neq(cls))
    index = index.updateMask(valid_cover).updateMask(common.permanent_water_mask(50).Not())

    result_image = index.clip(geometry)
    url = common.tile_url(result_image, {"palette": _PALETTE, "min": 0, "max": 1})

    stats = result_image.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=geometry,
        scale=100,
        maxPixels=1e10,
        bestEffort=True,
    ).getInfo()
    mean_idx = stats.get("moisture_mean")
    mean_idx = round(float(mean_idx), 2) if mean_idx is not None else None
    if mean_idx is None:
        raise ValueError(
            "No soil-moisture-capable land in this area. The index is masked "
            "under dense forest, built-up areas, water and snow. Try an area "
            "with open soil, cropland or grassland."
        )

    data_date = common.latest_image_date(current)
    return {
        "tile_url": url,
        "result_image": index,
        "moisture_index_mean": mean_idx,
        "moisture_index_stddev": round(float(stats.get("moisture_stdDev") or 0), 2),
        "confidence": round(min(0.85, 0.55 + 0.02 * current_count), 2),
        "data_date": data_date,
        "images_used": current_count,
        "method_note": (
            "Relative surface (~5 cm) moisture via VV change detection against "
            "each pixel's own 12-month dry/wet envelope. Masked where dense "
            "canopy, urban fabric, water or snow break the retrieval."
        ),
        "headline_stat": {
            "label": "Mean surface moisture index",
            "value": mean_idx,
            "unit": "(0 dry – 1 wet)",
        },
    }
