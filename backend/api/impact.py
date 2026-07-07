from fastapi import APIRouter, HTTPException

from models.requests import ImpactRequest
from gee.impact import assess_impact

router = APIRouter()


@router.post("/impact/population")
def impact_population(req: ImpactRequest):
    try:
        data = assess_impact(
            req.analysis_type, req.bbox, req.start_date, req.end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Impact assessment failed: {e}")

    return {
        "analysis_type": req.analysis_type,
        "population_affected": data["population_affected"],
        "built_up_km2": data["built_up_km2"],
        "data_date": data["data_date"],
        "headline_stat": data["headline_stat"],
    }
