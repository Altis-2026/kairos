from fastapi import APIRouter, HTTPException

import foresight_answers
from models.requests import ForesightAskRequest, ForesightRequest

router = APIRouter()

MAX_SPAN_DEG = 3.0


@router.post("/foresight")
def run_foresight(request: ForesightRequest):
    from gee.risk import RISK_FUNCTIONS

    bbox = request.bbox
    if bbox[2] - bbox[0] > MAX_SPAN_DEG or bbox[3] - bbox[1] > MAX_SPAN_DEG:
        raise HTTPException(
            status_code=400,
            detail=(
                "Risk outlooks work on areas up to about 3 degrees across. "
                "Zoom in to a city or county scale and try again."
            ),
        )

    fn = RISK_FUNCTIONS[request.hazard]
    try:
        return fn(bbox)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk outlook failed: {e}")


@router.post("/foresight/ask")
def ask_foresight(request: ForesightAskRequest):
    ctx = request.model_dump()
    try:
        from ai.client import answer_foresight_question

        return {
            "answer": answer_foresight_question(ctx),
            "source": "ai",
        }
    except Exception:
        # The outlook's own numbers are enough to answer the common questions,
        # so a missing key or an exhausted quota degrades instead of failing.
        return {
            "answer": foresight_answers.fallback_answer(ctx),
            "source": "data",
        }
