"""
POST /simulate — run a forward simulation (flood or wildfire).
GET  /simulate/scenes — the curated showcase scenes for both.

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

from fastapi import Query

from jobs.queue import get_queue
from models.requests import SimulateRequest
from solver import fire_presets, presets

router = APIRouter()

#: The two forward models, keyed by the request's `kind`. Everything around
#: the physics is shared, so adding a third model means adding a row here and
#: nothing else in this file.
KINDS = {
    "flood": {
        "analysis_type": "flood_simulation",
        "get_scene": presets.get_scene,
        "scenes": presets.scenes_as_json,
        "estimated_seconds": 120,
        "note": (
            "Every scene uses an illustrative hydrograph — a plausible "
            "flash-flood shape, not a gauge record and not a forecast."
        ),
    },
    "fire": {
        "analysis_type": "fire_simulation",
        "get_scene": fire_presets.get_scene,
        "scenes": fire_presets.scenes_as_json,
        "estimated_seconds": 90,
        "note": (
            "Every scene is an illustrative scenario — plausible fuel, wind "
            "and ignition for that landscape, not a reconstruction of any "
            "actual fire and not a forecast."
        ),
    },
}

#: Kept for callers that predate `kind`.
ANALYSIS_TYPE = KINDS["flood"]["analysis_type"]


@router.get("/simulate/scenes")
def list_scenes(kind: str = Query(None, description="flood, fire, or omit for both")):
    """
    Curated AOIs with their forcing already chosen.

    Each carries its own disclosure, because the terrain in every one of them
    is real and the event is not.
    """
    if kind is not None and kind not in KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"kind must be one of {sorted(KINDS)}; got {kind!r}.",
        )
    wanted = [kind] if kind else list(KINDS)

    scenes = []
    for name in wanted:
        for scene in KINDS[name]["scenes"]():
            scenes.append({**scene, "kind": name})

    return {
        "scenes": scenes,
        "kinds": {name: {"note": KINDS[name]["note"]} for name in wanted},
        # Flat `note` retained so existing flood-only callers keep working.
        "note": KINDS[wanted[0]]["note"],
    }


def _resolve(request: SimulateRequest) -> tuple:
    """Turn the request into (bbox, event_date, params) for the runner."""
    params = dict(request.params or {})
    bbox = request.bbox
    kind = KINDS[request.kind]

    if request.scene:
        scene = kind["get_scene"](request.scene)   # raises ValueError if unknown
        params.setdefault("scene", request.scene)
        if bbox is None:
            bbox = list(scene.bbox)

    event_date = request.start_date or date.today().isoformat()
    return bbox, event_date, params


@router.post("/simulate")
def simulate(request: SimulateRequest):
    """
    Run a forward simulation. Queued by default; poll `/status/{job_id}`.

    Returns either `{job_id, status: "queued", ...}` or, when the queue is
    unavailable or `run_async` is false, the finished analysis result.
    """
    try:
        bbox, event_date, params = _resolve(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    kind = KINDS[request.kind]
    analysis_type = kind["analysis_type"]
    queue = get_queue() if request.run_async else None

    if queue is not None:
        from jobs.worker import job_run_simulation

        job = queue.enqueue(
            job_run_simulation,
            bbox=bbox,
            start_date=event_date,
            params=params,
            analysis_type=analysis_type,
            job_timeout=900,
        )
        return {
            "job_id": job.id,
            "status": "queued",
            "poll": f"/status/{job.id}",
            "analysis_type": analysis_type,
            "kind": request.kind,
            "mode": "simulated",
            "bbox": bbox,
            "estimated_seconds": kind["estimated_seconds"],
        }

    from api.analyze import run_analysis

    try:
        return run_analysis(
            analysis_type=analysis_type,
            bbox=bbox,
            start_date=event_date,
            end_date=event_date,
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")
