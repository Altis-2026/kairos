"""
Ground-truth validation — how accurate is Kairos, measured, not asserted.

Each benchmark is a real historical event where an independent reference map
exists inside Earth Engine. We re-run the exact production detector over the
event window, rasterize the reference, and compute pixel-area agreement
metrics (IoU, precision, recall, F1) server-side. Numbers are computed live
on every run — nothing here is hardcoded or fabricated.

References:
    GLOBAL_FLOOD_DB/MODIS_EVENTS/V1      913 mapped flood events, 250 m
                                         (Tellman et al. 2021, Nature)
    MODIS/061/MCD64A1                    monthly burned area, 500 m
    UMD/hansen/global_forest_change_*    annual forest loss, 30 m

Honest caveats, returned with every result: the references are coarser than
Sentinel-1 (250-500 m vs 30 m), built from different sensors with their own
error, and agreement is computed at the reference's native scale. These are
indicative accuracy figures, not survey-grade truth.
"""

import ee
from gee import common
from gee.registry import ANALYSIS_REGISTRY

GLOBAL_FLOOD_DB = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
MCD64A1 = "MODIS/061/MCD64A1"
HANSEN = "UMD/hansen/global_forest_change_2023_v1_11"
_HANSEN_LAST_YEAR = 2023

BENCHMARKS = [
    {
        "id": "bangladesh-monsoon-2017",
        "analysis_type": "flood_extent",
        "region": "Brahmaputra floodplain, Bangladesh — August 2017 monsoon",
        "bbox": [89.3, 25.0, 89.9, 25.5],
        "start_date": "2017-08-10",
        "end_date": "2017-08-31",
        "reference": "Global Flood Database (MODIS, 250 m; Tellman et al. 2021)",
        "reference_scale_m": 250,
    },
    {
        "id": "camp-fire-2018",
        "analysis_type": "wildfire_burn_scar",
        "region": "Camp Fire, Butte County, California — November 2018",
        "bbox": [-121.75, 39.65, -121.35, 39.95],
        "start_date": "2018-11-08",
        "end_date": "2018-12-08",
        "reference": "MODIS MCD64A1 burned area (500 m)",
        "reference_scale_m": 500,
    },
    {
        "id": "rondonia-clearing-2020",
        "analysis_type": "deforestation",
        "region": "Rondônia, Brazil — 2020 clearing season",
        "bbox": [-63.6, -9.8, -63.1, -9.4],
        "start_date": "2020-06-01",
        "end_date": "2020-09-30",
        "reference": "Hansen Global Forest Change loss year (Landsat, 30 m)",
        "reference_scale_m": 30,
    },
]


def _reference_mask(bm: dict, geometry: ee.Geometry) -> ee.Image:
    """Binary reference mask for a benchmark, from its ground-truth dataset."""
    analysis_type = bm["analysis_type"]

    if analysis_type == "flood_extent":
        # Event rasters carry began/ended metadata; a widened date filter
        # catches events overlapping our window. Permanent water is excluded
        # the same way the detector excludes it.
        events = (
            ee.ImageCollection(GLOBAL_FLOOD_DB)
            .filterBounds(geometry)
            .filterDate(
                ee.Date(bm["start_date"]).advance(-45, "day"),
                ee.Date(bm["end_date"]).advance(45, "day"),
            )
        )
        if events.size().getInfo() == 0:
            raise ValueError(
                "No Global Flood Database event overlaps this benchmark window."
            )
        flooded = events.select("flooded").max().gt(0)
        return flooded.where(common.permanent_water_mask(75), 0)

    if analysis_type == "wildfire_burn_scar":
        burns = (
            ee.ImageCollection(MCD64A1)
            .filterBounds(geometry)
            .filterDate(
                bm["start_date"], ee.Date(bm["end_date"]).advance(60, "day")
            )
        )
        if burns.size().getInfo() == 0:
            raise ValueError("No MCD64A1 burned-area data for this window.")
        return burns.select("BurnDate").max().gt(0)

    if analysis_type == "deforestation":
        year = int(bm["start_date"][:4])
        if year > _HANSEN_LAST_YEAR:
            raise ValueError(
                f"Hansen reference currently ends at {_HANSEN_LAST_YEAR}."
            )
        lossyear = ee.Image(HANSEN).select("lossyear")
        return lossyear.eq(year - 2000)

    raise ValueError(f"No reference dataset wired for '{analysis_type}'.")


def _agreement_metrics(
    ours: ee.Image, ref: ee.Image, geometry: ee.Geometry, scale: int
) -> dict:
    """
    IoU / precision / recall / F1 by pixel area, in ONE combined reduceRegion
    (a 4-band area image) so the whole comparison is a single round-trip.
    """
    ours_b = ours.unmask(0).gt(0).rename("ours")
    ref_b = ref.unmask(0).gt(0).rename("ref")
    inter = ours_b.And(ref_b).rename("inter")
    union = ours_b.Or(ref_b).rename("union")

    sums = (
        ee.Image.cat([ours_b, ref_b, inter, union])
        .multiply(ee.Image.pixelArea())
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=scale,
            maxPixels=1e10,
            bestEffort=True,
        )
        .getInfo()
    )

    to_km2 = lambda v: round(float(v or 0) / 1_000_000, 2)  # noqa: E731
    a_ours = to_km2(sums.get("ours"))
    a_ref = to_km2(sums.get("ref"))
    a_int = to_km2(sums.get("inter"))
    a_uni = to_km2(sums.get("union"))

    precision = round(a_int / a_ours, 3) if a_ours > 0 else None
    recall = round(a_int / a_ref, 3) if a_ref > 0 else None
    iou = round(a_int / a_uni, 3) if a_uni > 0 else None
    f1 = (
        round(2 * precision * recall / (precision + recall), 3)
        if precision and recall and (precision + recall) > 0
        else None
    )
    return {
        "kairos_area_km2": a_ours,
        "reference_area_km2": a_ref,
        "intersection_km2": a_int,
        "union_km2": a_uni,
        "precision": precision,
        "recall": recall,
        "iou": iou,
        "f1": f1,
    }


def get_benchmark(benchmark_id: str) -> dict:
    for bm in BENCHMARKS:
        if bm["id"] == benchmark_id:
            return bm
    raise ValueError(
        f"Unknown benchmark '{benchmark_id}'. "
        f"Available: {[b['id'] for b in BENCHMARKS]}"
    )


def run_benchmark(benchmark_id: str) -> dict:
    """
    Run one benchmark end-to-end: production detector vs reference dataset.
    Slow (one full GEE analysis + comparison, typically 30-90 s).
    """
    bm = get_benchmark(benchmark_id)
    geometry = common.bbox_geometry(bm["bbox"])

    # The exact production detector — not a special validation path.
    detector = ANALYSIS_REGISTRY[bm["analysis_type"]]["function"]
    raw = detector(
        bbox=bm["bbox"], start_date=bm["start_date"], end_date=bm["end_date"]
    )
    ours = raw["result_image"]

    ref = _reference_mask(bm, geometry).clip(geometry)
    metrics = _agreement_metrics(ours, ref, geometry, bm["reference_scale_m"])

    ref_tile = common.tile_url(
        ref.selfMask(), {"palette": ["#E8A318"], "min": 0, "max": 1}
    )

    return {
        "benchmark": {k: v for k, v in bm.items()},
        "metrics": metrics,
        "kairos_tile_url": raw["tile_url"],
        "reference_tile_url": ref_tile,
        "data_date": raw.get("data_date"),
        "caveats": (
            "Reference maps are coarser than Sentinel-1 and come from "
            "different sensors with their own error. Agreement is computed at "
            f"the reference's native {bm['reference_scale_m']} m scale — "
            "indicative accuracy, not absolute truth."
        ),
    }
