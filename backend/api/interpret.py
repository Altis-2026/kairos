"""
POST /interpret          — plain-language interpretation of a finished result,
                           grounded only in the computed numbers (instant).
POST /interpret/context  — on-demand: recent regional news / trends / concerns
                           pulled via web search.

Both degrade gracefully: /interpret falls back to a rule-based summary when no
AI provider is configured, and /interpret/context reports unavailability rather
than erroring.
"""

from fastapi import APIRouter

from models.requests import InterpretRequest
from gee.registry import ANALYSIS_REGISTRY
from ai.client import (
    interpret_result,
    search_regional_context,
    fallback_interpretation,
)

router = APIRouter()


def _result_dict(req: InterpretRequest) -> dict:
    return {
        "analysis_type": req.analysis_type,
        "display_name": req.display_name,
        "bbox": req.bbox,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "data_date": req.data_date,
        "confidence": req.confidence,
        "headline_stat": {
            "label": req.headline_label,
            "value": req.headline_value,
            "unit": req.headline_unit,
        },
        "stats": req.stats or {},
    }


@router.post("/interpret")
def interpret(req: InterpretRequest):
    """Instant, grounded interpretation — works with or without an AI key."""
    result = _result_dict(req)
    description = ANALYSIS_REGISTRY.get(req.analysis_type, {}).get("description", "")
    try:
        text = interpret_result(result, description, req.place_name)
        return {"available": True, "text": text, "source": "ai"}
    except RuntimeError:
        # No OPENROUTER_API_KEY — still useful via the rule-based summary.
        return {
            "available": True,
            "text": fallback_interpretation(result, description),
            "source": "template",
        }
    except Exception as e:
        return {
            "available": True,
            "text": fallback_interpretation(result, description),
            "source": "template",
            "note": f"AI interpretation failed, showing a rule-based summary: {e}",
        }


@router.post("/interpret/context")
def interpret_context(req: InterpretRequest):
    """Web-search-backed regional context — only runs when the user asks."""
    result = _result_dict(req)
    try:
        text = search_regional_context(result, req.place_name)
        return {"available": True, "text": text, "source": "web"}
    except RuntimeError:
        return {
            "available": False,
            "text": "",
            "note": "Live regional context needs OPENROUTER_API_KEY on the backend.",
        }
    except Exception as e:
        return {
            "available": False,
            "text": "",
            "note": f"Regional search is unavailable right now: {e}",
        }
