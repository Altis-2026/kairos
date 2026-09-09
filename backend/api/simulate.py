"""
POST /simulate — run a forward flood simulation.
GET  /simulate/scenes — the curated showcase scenes.

Simulations are slow by the standards of a request handler (a real solve is
tens of seconds to a couple of minutes) and they return megabytes of frame
data, so the default path enqueues the work on the existing Redis queue and
hands back a job id to poll at `/status/{job_id}`. When Redis is not running —
the documented development fallback in `jobs/queue.py` — the solve runs inline
instead, so the feature works on a laptop with nothing else set up.

Everything returned from here is a MODEL RESULT, not an observation. The
`mode: "simulated"` field is inside the provenance hash rather than beside it,
and the disclosure text travels in `stats` all the way to the UI.
"""

from datetime import date

from fastapi import APIRouter, HTTPException

from jobs.queue import get_queue
from models.requests import SimulateRequest
from solver.presets import get_scene, scenes_as_json

router = APIRouter()

ANALYSIS_TYPE = "flood_simulation"


@router.get("/simulate/scenes")
def list_scenes():
    """
    Curated AOIs with pre-shaped hydrographs.

    Each carries its own disclosure: the terrain is real, the water is not.
    """
    return {
        "scenes": scenes_as_json(),
        "note": (
            "Every scene uses an illustrative hydrograph — a plausible "
            "flash-flood shape, not a gauge record and not a forecast."
        ),
    }


def _resolve(request: SimulateRequest) -> tuple:
    """Turn the request into (bbox, event_date, params) for the runner."""
    params = dict(request.params or {})
    bbox = request.bbox

    if request.scene:
        scene = get_scene(request.scene)          # raises ValueError if unknown
        params.setdefault("scene", request.scene)
        if bbox is None:
            bbox = list(scene.bbox)

    event_date = request.start_date or date.today().isoformat()
    return bbox, event_date, params


@router.post("/simulate")
def simulate(request: SimulateRequest):
    """
    Run a flood simulation. Queued by default; poll `/status/{job_id}`.

    Returns either `{job_id, status: "queued", ...}` or, when the queue is
    unavailable or `run_async` is false, the finished analysis result.
    """
    try:
        bbox, event_date, params = _resolve(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    queue = get_queue() if request.run_async else None

    if queue is not None:
        from jobs.worker import job_run_simulation

        job = queue.enqueue(
            job_run_simulation,
            bbox=bbox,
            start_date=event_date,
            params=params,
            job_timeout=900,
        )
        return {
            "job_id": job.id,
            "status": "queued",
            "poll": f"/status/{job.id}",
            "analysis_type": ANALYSIS_TYPE,
            "mode": "simulated",
            "bbox": bbox,
            "estimated_seconds": 120,
        }

    from api.analyze import run_analysis

    try:
        return run_analysis(
            analysis_type=ANALYSIS_TYPE,
            bbox=bbox,
            start_date=event_date,
            end_date=event_date,
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")
