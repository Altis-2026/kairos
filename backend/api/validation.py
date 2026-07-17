"""
GET  /validation/benchmarks — the benchmark suite (instant, no GEE)
POST /validation/run        — run one benchmark live against ground truth

Every metric is computed server-side on Earth Engine at request time, so the
accuracy numbers Kairos quotes are reproducible by anyone who presses the
button — the opposite of a hardcoded marketing claim.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gee.validation import BENCHMARKS, run_benchmark

router = APIRouter()


class ValidationRequest(BaseModel):
    benchmark_id: str


@router.get("/validation/benchmarks")
def list_benchmarks():
    return {
        "benchmarks": [
            {k: v for k, v in bm.items()} for bm in BENCHMARKS
        ]
    }


@router.post("/validation/run")
def run_validation(request: ValidationRequest):
    """
    Slow endpoint (one full production analysis + reference comparison,
    typically 30-90 s). Synchronous by design: GEE calls block, so FastAPI
    runs this in its threadpool.
    """
    try:
        return run_benchmark(request.benchmark_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}")


@router.get("/scoreboard")
def public_scoreboard():
    """
    The public accuracy scoreboard: aggregated skill (IoU/precision/recall/F1)
    per benchmark across every validation run ever executed. No auth — being
    public is the point.
    """
    import scoreboard

    return scoreboard.summary()
