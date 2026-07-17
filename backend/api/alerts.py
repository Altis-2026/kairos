"""
Alert mode — "watch this area; tell me when something new is detected".

The persistent list of alerts lives in Firestore (per signed-in user, client
side). This endpoint is the *checking* half: given a watched area + analysis
type and the last acquisition we already saw, it asks Earth Engine whether a
newer Sentinel-1 pass exists and, if so, runs the analysis on the fresh window
and returns the result.

It is callable on demand ("Check now" in the UI) and is also the exact call a
scheduler (Cloud Scheduler -> this endpoint, one hit per alert) would make to
turn Kairos from "check when you remember" into "tells you when it happens".
Notification delivery (email/Slack) is intentionally left to the integration
layer — this endpoint just reports whether there is something worth notifying.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from models.requests import AlertCheckRequest
from api.analyze import run_analysis

router = APIRouter()


@router.post("/alerts/check")
def alert_check(req: AlertCheckRequest):
    """Run the watched analysis on the most recent window; flag if it's new."""
    end = (
        datetime.strptime(req.end_date, "%Y-%m-%d")
        if req.end_date
        else datetime.now(timezone.utc)
    )
    start = end - timedelta(days=req.lookback_days)

    try:
        result = run_analysis(
            analysis_type=req.analysis_type,
            bbox=req.bbox,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )
    except ValueError:
        # No Sentinel-1 acquisition in the recent window yet — nothing new.
        return {
            "new": False,
            "data_date": None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "note": "No new Sentinel-1 pass in the lookback window yet.",
            "result": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert check failed: {e}")

    data_date = result["data_date"]
    is_new = req.since_date is None or data_date > req.since_date

    return {
        "new": is_new,
        "data_date": data_date,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "headline_stat": result["headline_stat"],
        # Only ship the full (heavier) result when there's actually something new.
        "result": result if is_new else None,
    }


# --- outbound webhooks -------------------------------------------------------

from pydantic import BaseModel, Field  # noqa: E402


class WebhookRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=8, max_length=500)


class WebhookOwner(BaseModel):
    owner: str = Field(min_length=1, max_length=128)


@router.post("/alerts/webhook")
def set_webhook(req: WebhookRequest):
    """
    Register (or replace) the owner's outbound webhook. Watch findings are
    POSTed here — Slack incoming webhooks get Slack formatting automatically;
    any other URL receives the raw JSON event.
    """
    import notify
    from janus import store as janus_store

    try:
        notify.validate_webhook_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    janus_store.set_webhook(req.owner, req.url)
    return {"saved": True}


@router.get("/alerts/webhook")
def get_webhook(owner: str):
    from janus import store as janus_store

    return {"url": janus_store.get_webhook(owner)}


@router.delete("/alerts/webhook")
def delete_webhook(owner: str):
    from janus import store as janus_store

    janus_store.delete_webhook(owner)
    return {"deleted": True}


@router.post("/alerts/webhook/test")
def test_webhook(req: WebhookOwner):
    """Send a sample event so the user can prove their webhook works."""
    import notify

    ok = notify.notify_owner(
        req.owner,
        {
            "title": "Kairos: webhook test",
            "summary": "If you can read this, your Kairos alerts are wired up.",
            "kind": "test",
        },
    )
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Delivery failed — no webhook registered, or the URL did "
            "not accept the POST.",
        )
    return {"delivered": True}
