"""
POST /impact/population — translate a detection footprint into human impact.

Cross-references the result mask of any footprint-producing analysis (flood,
fire, deforestation, deformation…) against global population and building data
to answer "how many people / buildings are inside the affected area?".
"""

from fastapi import APIRouter, HTTPException

from models.requests import ImpactRequest
from gee.impact import assess_impact

router = APIRouter()


@router.post("/impact/population")
def impact_population(req: ImpactRequest):
    """People (and, where covered, buildings) within the detection footprint."""
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
