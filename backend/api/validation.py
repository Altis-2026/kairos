from fastapi import APIRouter, HTTPException

from models.requests import ConfounderRequest, ValidationRunRequest

router = APIRouter()


@router.get("/validation/benchmarks")
def list_benchmarks():
    from gee.validation import BENCHMARKS

    return {"benchmarks": [{k: v for k, v in bm.items()} for bm in BENCHMARKS]}


@router.post("/validation/run")
def run_validation(request: ValidationRunRequest):
    from gee.validation import run_benchmark

    try:
        return run_benchmark(request.benchmark_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.post("/confounders")
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
