"""
Population & infrastructure impact assessment.

Turns a detection raster ("300 km² flooded") into a human figure ("~40,000
people and 5.2 km² of built-up surface inside the affected footprint") by
intersecting the result mask with global population and built-up datasets on
GEE — entirely server-side, never downloading raw data.

Datasets (global, free, raster — fast reduceRegion, no vector ops):
  - JRC GHSL population   (JRC/GHSL/P2023A/GHS_POP)     people per ~100 m pixel
  - JRC GHSL built-up     (JRC/GHSL/P2023A/GHS_BUILT_S) built-up m² per pixel

Both are intersected with the *detection footprint* the analysis produced.
"""

import ee
from gee import common

GHSL_POP = "JRC/GHSL/P2023A/GHS_POP"
GHSL_BUILT = "JRC/GHSL/P2023A/GHS_BUILT_S"

# Most recent GHSL epoch in the 2023A release.
_POP_EPOCH = "2020"
_BUILT_EPOCH = "2020"


def _detection_mask(analysis_type: str, bbox: list, start_date: str, end_date: str):
    """Run the analysis and return (mask_image, geometry, base_result)."""
    from gee.registry import ANALYSIS_REGISTRY

    if analysis_type not in ANALYSIS_REGISTRY:
        raise ValueError(f"Unknown analysis type '{analysis_type}'.")
    fn = ANALYSIS_REGISTRY[analysis_type]["function"]
    raw = fn(bbox=bbox, start_date=start_date, end_date=end_date)
    image = raw.get("result_image")
    if image is None:
        raise ValueError(
            "Impact assessment isn't available for this analysis type "
            "(no detection footprint was produced)."
        )
    geometry = common.bbox_geometry(bbox)
    # Reduce to a single 0/1 mask band regardless of the source band name.
    mask = image.gt(0).rename("detection")
    return mask, geometry, raw


def assess_impact(
    analysis_type: str, bbox: list, start_date: str, end_date: str
) -> dict:
    """
    Args:
        analysis_type: a registry id whose result is a footprint (flood, fire…)
        bbox / start_date / end_date: the same parameters the analysis used

    Returns:
        dict with population_affected (int), built_up_km2 (float),
        data_date, plus headline_stat.

    Raises:
        ValueError: if no satellite data is available, or the analysis type has
            no footprint to assess.
    """
    mask, geometry, raw = _detection_mask(
        analysis_type, bbox, start_date, end_date
    )

    # --- People within the detection footprint ---
    # GHSL P2023A is an ImageCollection with one image per 5-year epoch; pick
    # the 2020 epoch by date and mosaic to a single population-count raster.
    pop_img = (
        ee.ImageCollection(GHSL_POP)
        .filterDate(f"{_POP_EPOCH}-01-01", f"{_POP_EPOCH}-12-31")
        .mosaic()
        .select("population_count")
    )
    # --- Built-up surface (total m² per pixel) within the footprint ---
    built_img = (
        ee.ImageCollection(GHSL_BUILT)
        .filterDate(f"{_BUILT_EPOCH}-01-01", f"{_BUILT_EPOCH}-12-31")
        .mosaic()
        .select("built_surface")
    )

    # One combined reduction over the masked footprint (one round-trip).
    combined = pop_img.rename("pop").addBands(built_img.rename("built"))
    stats = (
        combined.updateMask(mask)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=100,
            maxPixels=1e10,
            bestEffort=True,
        )
        .getInfo()
    )

    population_affected = int(round(float(stats.get("pop") or 0)))
    built_up_km2 = round(float(stats.get("built") or 0) / 1_000_000, 2)

    return {
        "population_affected": population_affected,
        "built_up_km2": built_up_km2,
        "data_date": raw.get("data_date"),
        "headline_stat": {
            "label": "People in footprint",
            "value": float(population_affected),
            "unit": "people",
        },
    }
