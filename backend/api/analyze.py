import json

from fastapi import APIRouter, Depends, HTTPException

import provenance
import result_cache
from gee import common
from gee.registry import ANALYSIS_REGISTRY
from models.requests import AnalyzeRequest
from ratelimit import limit_compute

router = APIRouter()

TOP_LEVEL_KEYS = {
    "tile_url",
    "data_date",
    "confidence",
    "headline_stat",
    "mode",
    "simulation",
}

NON_SERIALIZED_KEYS = {"result_image"}

WATER_CONTEXT_TYPES = {"flood_extent", "oil_spill"}


def _context_layers(analysis_type: str, bbox: list) -> list:
    layers: list = []
    if analysis_type in WATER_CONTEXT_TYPES:
        try:
            geometry = common.bbox_geometry(bbox)
            layers.append(
                {
                    "id": f"{analysis_type}-permanent-water",
                    "name": "Permanent water (reference)",
                    "tile_url": common.permanent_water_tile(geometry),
                    "color": common.WATER_BLUE,
                    "kind": "reference",
                }
            )
        except Exception:
            pass
    return layers


def _cache_key(analysis_type, bbox, start_date, end_date, params, polygon):
    return json.dumps(
        [
            analysis_type,
            [round(v, 4) for v in bbox],
            start_date,
            end_date,
            params or {},
            [[round(x, 4), round(y, 4)] for x, y in polygon] if polygon else None,
        ],
        sort_keys=True,
    )


def run_analysis(
    analysis_type: str,
    bbox: list,
    start_date: str,
    end_date: str,
    params: dict | None = None,
    polygon: list | None = None,
) -> dict:
    if analysis_type not in ANALYSIS_REGISTRY:
        raise ValueError(
            f"Unknown analysis type '{analysis_type}'. Available: {list(ANALYSIS_REGISTRY.keys())}"
        )
    config = ANALYSIS_REGISTRY[analysis_type]

    call_kwargs = {"bbox": bbox, "start_date": start_date, "end_date": end_date}
    if config.get("accepts_params"):
        call_kwargs["params"] = params or {}
    elif params:
        raise ValueError(
            f"'{analysis_type}' does not take extra parameters. Analyses that do: "
            f"{[k for k, c in ANALYSIS_REGISTRY.items() if c.get('accepts_params')]}"
        )

    if polygon:
        bbox = common.polygon_envelope(polygon)
        call_kwargs["bbox"] = bbox

    key = _cache_key(analysis_type, bbox, start_date, end_date, params, polygon)
    cached = result_cache.get(key)
    if cached is not None:
        return cached

    token = common.active_polygon.set(polygon)
    try:
        raw = config["function"](**call_kwargs)
        context = _context_layers(analysis_type, bbox)
    finally:
        common.active_polygon.reset(token)

    stats = {k: v for k, v in raw.items() if k not in TOP_LEVEL_KEYS and k not in NON_SERIALIZED_KEYS}
    response = {
        "analysis_type": analysis_type,
        "display_name": config["display_name"],
        "bbox": bbox,
        "start_date": start_date,
        "end_date": end_date,
        "tile_url": raw["tile_url"],
        "data_date": raw["data_date"],
        "confidence": raw.get("confidence", 0.8),
        "headline_stat": raw.get("headline_stat", {"label": "Result", "value": 0, "unit": ""}),
        "context_layers": context,
        "mode": raw.get("mode", config.get("mode", "observed")),
        "stats": stats,
    }
    if polygon:
        response["polygon"] = polygon
    if "simulation" in raw:
        response["simulation"] = raw["simulation"]
    stamped = provenance.stamp(response)
    result_cache.put(key, stamped)
    return stamped


@router.post("/analyze", dependencies=[Depends(limit_compute)])
def analyze(request: AnalyzeRequest):
    try:
        return run_analysis(
            analysis_type=request.analysis_type,
            bbox=request.bbox,
            start_date=request.start_date,
            end_date=request.end_date,
            params=request.params,
            polygon=request.polygon,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/verify")
def verify_result(result: dict):
    return provenance.verify(result)
