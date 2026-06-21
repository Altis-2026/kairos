"""
Research-grade SAR views layered on top of the core detections:

  POST /research/backscatter  — grayscale raw SAR composite (the physics)
  POST /research/optical      — Sentinel-2 true-color for the same window
  POST /research/compare      — before/after grayscale composites (for a slider)
  POST /research/timeseries   — the analysis run across stepped time windows

All operate on the same {analysis_type, bbox, dates} an analysis already used,
so they apply to any result regardless of how it was produced.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from models.requests import AnalyzeRequest, OpticalRequest, TimeSeriesRequest
from gee import common
from gee.optical import optical_image
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()


def _bands_for(analysis_type: str):
    """(polarization, instrument_mode) for an analysis, with safe defaults."""
    cfg = ANALYSIS_REGISTRY.get(analysis_type, {})
    return cfg.get("sar_polarization", "VV"), cfg.get("instrument_mode", "IW")


@router.post("/research/backscatter")
def backscatter(req: AnalyzeRequest):
    """Raw calibrated SAR backscatter as a grayscale layer."""
    pol, mode = _bands_for(req.analysis_type)
    try:
        data = common.backscatter_tile(
            req.bbox, req.start_date, req.end_date, pol, mode
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backscatter failed: {e}")

    return {
        "kind": "backscatter",
        "tile_url": data["tile_url"],
        "data_date": data["data_date"],
        "label": f"Raw SAR backscatter · {pol}",
        "color": "#9CA3AF",
    }


@router.post("/research/optical")
def optical(req: OpticalRequest):
    """Least-cloudy Sentinel-2 true-color scene for the window."""
    try:
        data = optical_image(req.bbox, req.start_date, req.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optical lookup failed: {e}")

    return {
        "kind": "optical",
        "tile_url": data["tile_url"],
        "data_date": data["data_date"],
        "cloud_percent": data["cloud_percent"],
        "label": f"Optical · Sentinel-2 · {data['data_date']}",
        "color": "#34D399",
    }


@router.post("/research/compare")
def compare(req: AnalyzeRequest):
    """
    Before/after grayscale composites: the analysis window ('after') and the
    equally long window immediately preceding it ('before'). The frontend
    cross-fades between them with a slider.
    """
    pol, mode = _bands_for(req.analysis_type)

    start = datetime.strptime(req.start_date, "%Y-%m-%d")
    end = datetime.strptime(req.end_date, "%Y-%m-%d")
    duration = max((end - start).days, 1)

    pre_end = start - timedelta(days=1)
    pre_start = pre_end - timedelta(days=duration)

    try:
        after = common.backscatter_tile(
            req.bbox, req.start_date, req.end_date, pol, mode
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compare (after) failed: {e}")

    # The 'before' window may be empty at this duration; widen once before giving up.
    before = None
    for widen in (0, duration + 30):
        b_start = (pre_start - timedelta(days=widen)).strftime("%Y-%m-%d")
        b_end = pre_end.strftime("%Y-%m-%d")
        try:
            before = common.backscatter_tile(req.bbox, b_start, b_end, pol, mode)
            break
        except ValueError:
            continue
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Compare (before) failed: {e}"
            )

    if before is None:
        raise HTTPException(
            status_code=400,
            detail="No Sentinel-1 data in the pre-event window to compare against. "
            "Try a more recent area or a longer date range.",
        )

    return {
        "polarization": pol,
        "before": {
            "tile_url": before["tile_url"],
            "data_date": before["data_date"],
            "label": f"Before · {before['data_date']}",
        },
        "after": {
            "tile_url": after["tile_url"],
            "data_date": after["data_date"],
            "label": f"After · {after['data_date']}",
        },
    }


@router.post("/research/timeseries")
def timeseries(req: TimeSeriesRequest):
    """
    Run the same analysis across `steps` consecutive `interval_days` windows
    ending at end_date. Returns one frame per window with the detection tile and
    its headline value, oldest first — the frontend scrubs/animates through them.
    Frames with no available data are skipped rather than failing the request.
    """
    if req.analysis_type not in ANALYSIS_REGISTRY:
        raise HTTPException(
            status_code=400, detail=f"Unknown analysis type '{req.analysis_type}'."
        )
    fn = ANALYSIS_REGISTRY[req.analysis_type]["function"]
    end = datetime.strptime(req.end_date, "%Y-%m-%d")

    frames = []
    for i in range(req.steps):
        frame_end = end - timedelta(days=i * req.interval_days)
        frame_start = frame_end - timedelta(days=req.interval_days)
        try:
            raw = fn(
                bbox=req.bbox,
                start_date=frame_start.strftime("%Y-%m-%d"),
                end_date=frame_end.strftime("%Y-%m-%d"),
            )
        except Exception:
            # No data (or transient issue) for this window — skip the frame.
            continue
        hs = raw.get("headline_stat", {"label": "Result", "value": 0, "unit": ""})
        frames.append(
            {
                "date": raw["data_date"],
                "tile_url": raw["tile_url"],
                "value": hs["value"],
                "label": hs["label"],
                "unit": hs["unit"],
            }
        )

    frames.reverse()  # chronological: oldest -> newest

    if len(frames) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough data across the range to build a time series. "
            "Try a longer interval or a different area.",
        )

    return {
        "frames": frames,
        "metric": frames[-1]["label"],
        "unit": frames[-1]["unit"],
    }
