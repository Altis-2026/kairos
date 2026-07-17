"""POST /analyze — run a SAR analysis for a bbox + date range.
POST /verify — check the provenance signature of a previously issued result."""

from fastapi import APIRouter, HTTPException
from models.requests import AnalyzeRequest
from gee.registry import ANALYSIS_REGISTRY
import provenance

router = APIRouter()

# Keys that are promoted to top-level response fields; everything else
# the GEE function returns goes into the `stats` dict.
TOP_LEVEL_KEYS = {"tile_url", "data_date", "confidence", "headline_stat"}

# Keys that must never be serialized into the JSON response (e.g. the raw
# ee.Image kept for GeoTIFF export).
NON_SERIALIZED_KEYS = {"result_image"}

# Analyses whose whole point is distinguishing anomalous dark water from water
# that is permanently there. For these we attach a permanent-water reference
# layer so a single query returns the detection PLUS its context, not one
# isolated overlay.
WATER_CONTEXT_TYPES = {"flood_extent", "oil_spill"}


def _context_layers(analysis_type: str, bbox: list) -> list:
    """
    Build optional reference layers shipped alongside the detection result.
    Always non-fatal: if GEE hiccups building context, we return the core
    analysis without it rather than failing the whole request.
    """
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

    stats = {
        k: v
        for k, v in raw.items()
        if k not in TOP_LEVEL_KEYS and k not in NON_SERIALIZED_KEYS
    }

    return provenance.stamp(
        {
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
            "context_layers": _context_layers(analysis_type, bbox),
            "stats": stats,
        }
    )


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


@router.post("/verify")
def verify_result(result: dict):
    """
    Verify a previously issued analysis result's provenance: recomputes the
    content hash over the scientific fields and checks the HMAC signature.
    Never raises — the verdict says exactly what (if anything) is wrong.
    """
    return provenance.verify(result)
