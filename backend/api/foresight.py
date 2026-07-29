from fastapi import APIRouter, HTTPException

from models.requests import ForesightRequest

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
