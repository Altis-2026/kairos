"""POST /analyze — run a SAR analysis for a bbox + date range."""

from fastapi import APIRouter, HTTPException
from models.requests import AnalyzeRequest
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()

# Keys that are promoted to top-level response fields; everything else
# the GEE function returns goes into the `stats` dict.
TOP_LEVEL_KEYS = {"tile_url", "data_date", "confidence", "headline_stat"}


def run_analysis(analysis_type: str, bbox: list, start_date: str, end_date: str) -> dict:
    """
    Shared analysis runner used by both /analyze and /query.
    Raises ValueError for user-facing problems (caller maps to HTTP 400).
    """
    if analysis_type not in ANALYSIS_REGISTRY:
        available = list(ANALYSIS_REGISTRY.keys())
        raise ValueError(
            f"Unknown analysis type '{analysis_type}'. Available: {available}"
        )

    config = ANALYSIS_REGISTRY[analysis_type]
    raw = config["function"](bbox=bbox, start_date=start_date, end_date=end_date)

    stats = {k: v for k, v in raw.items() if k not in TOP_LEVEL_KEYS}

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
        "stats": stats,
    }


@router.post("/analyze")
def analyze(request: AnalyzeRequest):
    """
    Run a SAR analysis. Returns a Mapbox-compatible tile URL plus statistics.
    GEE calls are blocking, so this endpoint is intentionally synchronous
    (`def`, not `async def`) — FastAPI runs it in a threadpool.
    """
    try:
        return run_analysis(
            analysis_type=request.analysis_type,
            bbox=request.bbox,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except ValueError as e:
        # User-facing: no data available, unknown type, bad parameters
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Server-side: GEE failure, timeout, quota
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
