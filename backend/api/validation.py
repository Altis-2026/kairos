from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from gee.validation import BENCHMARKS, run_benchmark
from models.requests import ConfounderRequest
from ratelimit import limit_compute

router = APIRouter()


class ValidationRequest(BaseModel):
    benchmark_id: str


@router.get("/validation/benchmarks")
def list_benchmarks():
    return {"benchmarks": [{k: v for k, v in bm.items()} for bm in BENCHMARKS]}


@router.post("/validation/run")
def run_validation(request: ValidationRequest):
    try:
        return run_benchmark(request.benchmark_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.get("/scoreboard")
def public_scoreboard():
    import scoreboard

    return scoreboard.summary()


@router.post("/confounders", dependencies=[Depends(limit_compute)])
def check_confounders(request: ConfounderRequest):
    from gee.confounders import analyze_confounders

    try:
        return analyze_confounders(
            request.analysis_type,
            request.bbox,
            request.start_date,
            request.end_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Confounder check failed: {e}")
