from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

import stats
from gee import common
from gee.impact import population_density_tile
from gee.optical import optical_image
from gee.registry import ANALYSIS_REGISTRY
from gee.signal import extract_series
from janus.figures import comparison_figure_svg, timeseries_figure_svg
from models.requests import (
    AnalyzeRequest,
    CompareAnalysesRequest,
    OpticalRequest,
    PopulationRequest,
    SignalRequest,
    TimeSeriesRequest,
)
from ratelimit import limit_compute

router = APIRouter()


def _bands_for(analysis_type: str):
    cfg = ANALYSIS_REGISTRY.get(analysis_type, {})
    return cfg.get("sar_polarization", "VV"), cfg.get("instrument_mode", "IW")


@router.post("/research/backscatter", dependencies=[Depends(limit_compute)])
def backscatter(req: AnalyzeRequest):
    pol, mode = _bands_for(req.analysis_type)
    try:
        data = common.backscatter_tile(req.bbox, req.start_date, req.end_date, pol, mode)
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


@router.post("/research/optical", dependencies=[Depends(limit_compute)])
def optical(req: OpticalRequest):
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


@router.post("/research/population", dependencies=[Depends(limit_compute)])
def population(req: PopulationRequest):
    try:
        data = population_density_tile(req.bbox)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Population layer failed: {e}")

    return {
        "kind": "population",
        "tile_url": data["tile_url"],
        "label": f"Population density · GHSL {data['epoch']}",
        "color": "#E8A318",
    }


@router.post("/research/compare", dependencies=[Depends(limit_compute)])
def compare(req: AnalyzeRequest):
    pol, mode = _bands_for(req.analysis_type)

    start = datetime.strptime(req.start_date, "%Y-%m-%d")
    end = datetime.strptime(req.end_date, "%Y-%m-%d")
    duration = max((end - start).days, 1)

    pre_end = start - timedelta(days=1)
    pre_start = pre_end - timedelta(days=duration)

    try:
        after = common.backscatter_tile(req.bbox, req.start_date, req.end_date, pol, mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compare (after) failed: {e}")

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
            raise HTTPException(status_code=500, detail=f"Compare (before) failed: {e}")

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


@router.post("/research/timeseries", dependencies=[Depends(limit_compute)])
def timeseries(req: TimeSeriesRequest):
    if req.analysis_type not in ANALYSIS_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown analysis type '{req.analysis_type}'.")
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

    frames.reverse()

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


@router.post("/research/signal", dependencies=[Depends(limit_compute)])
def signal(req: SignalRequest):
    try:
        series = extract_series(req.bbox, req.start_date, req.end_date, req.variable, req.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal extraction failed: {e}")

    trend = None
    if len(series["points"]) >= 4:
        try:
            trend = stats.trend_report(series["points"])
        except ValueError:
            trend = None

    csv_lines = ["date,value"] + [f"{p['date']},{p['value']}" for p in series["points"]]
    chart = timeseries_figure_svg(
        series["points"],
        series["variable"],
        series["unit"],
        series["source"],
        trend,
    )

    return {
        **series,
        "trend": trend,
        "csv": "\n".join(csv_lines),
        "chart_svg": chart,
    }


@router.post("/research/compare_analyses", dependencies=[Depends(limit_compute)])
def compare_analyses(req: CompareAnalysesRequest):
    if req.analysis_type not in ANALYSIS_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown analysis type '{req.analysis_type}'.")
    cfg = ANALYSIS_REGISTRY[req.analysis_type]
    fn = cfg["function"]

    results = {}
    for side, spec in (("a", req.a), ("b", req.b)):
        try:
            raw = fn(
                bbox=spec.bbox,
                start_date=spec.start_date,
                end_date=spec.end_date,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Side {side.upper()}: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Side {side.upper()} failed: {e}")
        raw.pop("result_image", None)
        results[side] = raw

    hs_a = results["a"].get("headline_stat", {})
    hs_b = results["b"].get("headline_stat", {})
    label_a = req.a.label or f"A · {req.a.start_date}"
    label_b = req.b.label or f"B · {req.b.start_date}"

    delta = None
    delta_pct = None
    try:
        va, vb = float(hs_a.get("value")), float(hs_b.get("value"))
        delta = round(vb - va, 3)
        delta_pct = round(100 * (vb - va) / va, 1) if va else None
    except (TypeError, ValueError):
        pass

    figure = comparison_figure_svg(
        {"label": label_a, "value": float(hs_a.get("value") or 0)},
        {"label": label_b, "value": float(hs_b.get("value") or 0)},
        hs_a.get("label") or cfg["display_name"],
        hs_a.get("unit") or "",
    )

    return {
        "analysis_type": req.analysis_type,
        "display_name": cfg["display_name"],
        "a": {"label": label_a, **results["a"]},
        "b": {"label": label_b, **results["b"]},
        "delta": delta,
        "delta_pct": delta_pct,
        "figure_svg": figure,
    }


@router.post("/research/cog_preview", dependencies=[Depends(limit_compute)])
def cog_preview(body: dict):
    import ee

    import gee_ready
    from gee import common as gee_common

    gee_ready.wait()
    uri = (body.get("uri") or "").strip()
    if not uri.startswith("gs://"):
        raise HTTPException(
            status_code=400,
            detail="Provide a gs:// URI to a Cloud-Optimized GeoTIFF. (Other "
            "hosts aren't supported yet, GEE's loadGeoTIFF reads from GCS.)",
        )
    try:
        img = ee.Image.loadGeoTIFF(uri)
        band_names = img.bandNames().getInfo()
        band = body.get("band") or band_names[0]
        pct = (
            img.select(band)
            .reduceRegion(
                reducer=ee.Reducer.percentile([2, 98]),
                geometry=img.geometry(),
                scale=body.get("scale", 60),
                maxPixels=1e9,
                bestEffort=True,
            )
            .getInfo()
        )
        vmin = body.get("min", pct.get(f"{band}_p2", 0))
        vmax = body.get("max", pct.get(f"{band}_p98", 1))
        url = gee_common.tile_url(img.select(band), {"min": vmin, "max": vmax})
        return {
            "tile_url": url,
            "bands": band_names,
            "band": band,
            "stretch": {"min": vmin, "max": vmax},
            "note": "Rendered directly from your COG. Nothing was copied or ingested.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not load that COG: {e}. Check the URI and that the "
            "Kairos service account (or allUsers) can read it.",
        )
