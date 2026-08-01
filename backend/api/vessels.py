"""
Dark-vessel screening: radar ship detections matched against AIS broadcasts.

GET  /vessels/cases   — the curated screening cases and whether their AIS
                        record is installed on this server
POST /vessels/screen  — run the screening pass for one case
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ScreenRequest(BaseModel):
    case_id: str


@router.get("/vessels/cases")
def list_cases():
    from gee.dark_vessels import CASES, case_available

    return {
        "cases": [
            {**{k: v for k, v in case.items()}, "available": case_available(case["id"])}
            for case in CASES
        ]
    }


@router.post("/vessels/screen")
def screen(request: ScreenRequest):
    from gee.dark_vessels import screen_case

    try:
        return screen_case(request.case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {e}")
