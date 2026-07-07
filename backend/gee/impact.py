import ee
from gee import common

GHSL_POP = "JRC/GHSL/P2023A/GHS_POP"
GHSL_BUILT = "JRC/GHSL/P2023A/GHS_BUILT_S"

_POP_EPOCH = "2020"
_BUILT_EPOCH = "2020"

POP_DENSITY_PALETTE = ["#13324A", "#1E6FE8", "#00BFA8", "#E8A318", "#FF3B5C"]


def population_density_tile(bbox: list, year: str = _POP_EPOCH) -> dict:
    geometry = common.bbox_geometry(bbox)
    pop = (
        ee.ImageCollection(GHSL_POP)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .mosaic()
        .select("population_count")
    )
    density = pop.updateMask(pop.gt(0)).clip(geometry)
    url = common.tile_url(
        density, {"min": 0, "max": 200, "palette": POP_DENSITY_PALETTE}
    )
    return {"tile_url": url, "epoch": year}


def _detection_mask(analysis_type: str, bbox: list, start_date: str, end_date: str):
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
    mask = image.gt(0).rename("detection")
    return mask, geometry, raw


def assess_impact(
    analysis_type: str, bbox: list, start_date: str, end_date: str
) -> dict:
    mask, geometry, raw = _detection_mask(
        analysis_type, bbox, start_date, end_date
    )

    pop_img = (
        ee.ImageCollection(GHSL_POP)
        .filterDate(f"{_POP_EPOCH}-01-01", f"{_POP_EPOCH}-12-31")
        .mosaic()
        .select("population_count")
    )
    built_img = (
        ee.ImageCollection(GHSL_BUILT)
        .filterDate(f"{_BUILT_EPOCH}-01-01", f"{_BUILT_EPOCH}-12-31")
        .mosaic()
        .select("built_surface")
    )

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
