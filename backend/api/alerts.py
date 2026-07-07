from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from models.requests import AlertCheckRequest
from api.analyze import run_analysis

router = APIRouter()


@router.post("/alerts/check")
def alert_check(req: AlertCheckRequest):
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
