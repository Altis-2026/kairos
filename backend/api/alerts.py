from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from api.analyze import run_analysis
from models.requests import AlertCheckRequest

router = APIRouter()


@router.post("/alerts/check")
def alert_check(req: AlertCheckRequest):
    end = datetime.strptime(req.end_date, "%Y-%m-%d") if req.end_date else datetime.now(timezone.utc)
    start = end - timedelta(days=req.lookback_days)

    try:
        result = run_analysis(
            analysis_type=req.analysis_type,
            bbox=req.bbox,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )
    except ValueError:
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
        "result": result if is_new else None,
    }


from pydantic import BaseModel, Field  # noqa: E402


class WebhookRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=8, max_length=500)


class WebhookOwner(BaseModel):
    owner: str = Field(min_length=1, max_length=128)


@router.post("/alerts/webhook")
def set_webhook(req: WebhookRequest):
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
            detail="Delivery failed, no webhook registered, or the URL did not accept the POST.",
        )
    return {"delivered": True}
