from fastapi import APIRouter, HTTPException
from models.requests import AnalyzeRequest
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()

TOP_LEVEL_KEYS = {"tile_url", "data_date", "confidence", "headline_stat"}

NON_SERIALIZED_KEYS = {"result_image"}

WATER_CONTEXT_TYPES = {"flood_extent", "oil_spill"}


def _context_layers(analysis_type: str, bbox: list) -> list:
    layers: list = []
    if analysis_type in WATER_CONTEXT_TYPES:
        try:
            from gee import common

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


def run_analysis(
    analysis_type: str,
    bbox: list,
    start_date: str,
    end_date: str,
    polygon: list = None,
) -> dict:
    if analysis_type not in ANALYSIS_REGISTRY:
        available = list(ANALYSIS_REGISTRY.keys())
        raise ValueError(
            f"Unknown analysis type '{analysis_type}'. Available: {available}"
        )

    aoi = polygon if polygon else bbox
    config = ANALYSIS_REGISTRY[analysis_type]
    raw = config["function"](bbox=aoi, start_date=start_date, end_date=end_date)

    stats = {
        k: v
        for k, v in raw.items()
        if k not in TOP_LEVEL_KEYS and k not in NON_SERIALIZED_KEYS
    }

    return {
        "analysis_type": analysis_type,
        "display_name": config["display_name"],
        "bbox": bbox,
        "start_date": start_date,
        "end_date": end_date,
        "tile_url": raw["tile_url"],
        "data_date": raw["data_date"],
        "confidence": raw.get("confidence", 0.8),
        "headline_stat": raw.get(
            "headline_stat", {"label": "Result", "value": 0, "unit": ""}
        ),
        "context_layers": _context_layers(analysis_type, aoi),
        "stats": stats,
    }


@router.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        return run_analysis(
            analysis_type=request.analysis_type,
            bbox=request.bbox,
            start_date=request.start_date,
            end_date=request.end_date,
            polygon=request.polygon,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
