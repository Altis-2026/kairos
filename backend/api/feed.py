from fastapi import APIRouter, Query

from watch import store, sweeper

router = APIRouter()


@router.get("/feed")
def get_feed(limit: int = Query(default=40, ge=1, le=100)):
    status = sweeper.sweep_status()
    return {
        "available": True,
        "findings": store.recent_findings(limit),
        "count": status["finding_count"],
        "sweeping": status["sweeping"],
        "last_sweep": status["last_sweep"],
        "next_sweep_at": status["next_sweep_at"],
        "interval_hours": status["interval_hours"],
    }


@router.get("/feed/status")
def feed_status():
    return sweeper.sweep_status()


@router.post("/feed/sweep")
def trigger_sweep():
    return sweeper.trigger_sweep_async()
