"""
Export & research-rigor endpoints:

  POST /export/geotiff  — a GeoTIFF download URL of the computed result image
  POST /export/report   — a citation-ready methodology report (markdown)

GeoTIFF exports the *analysis result* (the detection raster), computed on Earth
Engine — never raw satellite data, in line with the platform rules.
"""

import math
from datetime import datetime, timezone

import ee
from fastapi import APIRouter, HTTPException

from models.requests import AnalyzeRequest, ReportRequest
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()

# Base native resolution per analysis (m). Adaptive scaling bumps this up for
# large AOIs so the GeoTIFF stays within Earth Engine's direct-download limits.
_BASE_SCALE = {
    "flood_extent": 30,
    "ship_detection": 50,
    "wildfire_burn_scar": 30,
    "oil_spill": 50,
    "deforestation": 30,
    "sea_ice": 100,
    "surface_deformation": 30,
}

# Quantitative method detail for the methodology report, keyed by analysis type.
_METHOD = {
    "flood_extent": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "VV",
        "mode": "IW",
        "threshold": "VV backscatter drop > 3 dB versus the pre-event baseline",
        "baseline": "30-day pre-event window (extended to 60 days when sparse)",
        "masking": "JRC Global Surface Water permanent water (occurrence > 75%) removed",
        "resolution": "30 m",
    },
    "ship_detection": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "VV",
        "mode": "IW",
        "threshold": "CFAR-style adaptive: pixels > local mean + 5σ over water",
        "baseline": "Single most-recent acquisition (vessels move; no compositing)",
        "masking": "Restricted to water (JRC occurrence > 50%)",
        "resolution": "10 m native; detections vectorized at 50 m",
    },
    "wildfire_burn_scar": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "VH",
        "mode": "IW",
        "threshold": "VH backscatter rise > 2.5 dB versus the pre-fire baseline",
        "baseline": "60-day pre-fire window",
        "masking": "Permanent water (occurrence > 50%) excluded",
        "resolution": "30 m",
    },
    "oil_spill": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "VV",
        "mode": "IW",
        "threshold": "Dark anomalies > 2σ below the local ocean mean",
        "baseline": "Single most-recent acquisition",
        "masking": "Restricted to ocean / permanent water (occurrence > 50%)",
        "resolution": "10 m native; assessed at 50 m",
    },
    "deforestation": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "VH",
        "mode": "IW",
        "threshold": "VH backscatter drop > 3 dB versus a 12-month baseline",
        "baseline": "365-day historical window before the analysis period",
        "masking": "Permanent water (occurrence > 50%) excluded",
        "resolution": "30 m",
    },
    "sea_ice": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "HH",
        "mode": "EW",
        "threshold": "HH backscatter > -18 dB classified as ice",
        "baseline": "Mean composite over the analysis window",
        "masking": "None (polar EW acquisitions)",
        "resolution": "100 m",
    },
    "surface_deformation": {
        "collection": "COPERNICUS/S1_GRD",
        "band": "VV",
        "mode": "IW",
        "threshold": (
            "Recent VV deviates from its 12-month mean by > 2 baseline σ "
            "(amplitude temporal-coherence proxy, not phase InSAR)"
        ),
        "baseline": "365-day per-pixel mean + standard deviation",
        "masking": "Permanent water (occurrence > 50%) excluded",
        "resolution": "30 m",
    },
}


def _export_scale(bbox: list, base_scale: int, max_px: int = 2048) -> int:
    """Pick a scale (m) that keeps the long side of the export under max_px."""
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = (min_lat + max_lat) / 2
    width_m = (max_lon - min_lon) * 111320 * math.cos(math.radians(mid_lat))
    height_m = (max_lat - min_lat) * 110540
    longest = max(width_m, height_m, 1)
    return int(round(max(base_scale, longest / max_px)))


@router.post("/export/geotiff")
def export_geotiff(req: AnalyzeRequest):
    """Return a direct GeoTIFF download URL for the analysis result raster."""
    if req.analysis_type not in ANALYSIS_REGISTRY:
        raise HTTPException(
            status_code=400, detail=f"Unknown analysis type '{req.analysis_type}'."
        )

    fn = ANALYSIS_REGISTRY[req.analysis_type]["function"]
    try:
        raw = fn(bbox=req.bbox, start_date=req.start_date, end_date=req.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export computation failed: {e}")

    image = raw.get("result_image")
    if image is None:
        raise HTTPException(
            status_code=400,
            detail="GeoTIFF export is not available for this analysis type.",
        )

    region = ee.Geometry.Rectangle(req.bbox)
    scale = _export_scale(req.bbox, _BASE_SCALE.get(req.analysis_type, 30))
    name = f"kairos_{req.analysis_type}_{raw.get('data_date', 'result')}"

    try:
        # unmask(0) -> a clean 0/1 byte raster covering the AOI (GIS-friendly).
        url = image.unmask(0).toByte().getDownloadURL(
            {
                "name": name,
                "scale": scale,
                "region": region,
                "format": "GEO_TIFF",
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not build the GeoTIFF — the area may be too large for a "
                f"direct download. Try a smaller AOI. ({e})"
            ),
        )

    return {
        "download_url": url,
        "filename": f"{name}.tif",
        "scale_m": scale,
        "data_date": raw.get("data_date"),
    }


def _build_report_markdown(req: ReportRequest) -> str:
    m = _METHOD.get(req.analysis_type, {})
    cfg = ANALYSIS_REGISTRY.get(req.analysis_type, {})
    bbox = req.bbox
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    value = (
        f"{req.headline_value:,.2f}".rstrip("0").rstrip(".")
        if isinstance(req.headline_value, float)
        else req.headline_value
    )
    conf_pct = round(req.confidence * 100)

    scenes = ""
    stats = req.stats or {}
    image_keys = [k for k in stats if k.endswith("_used")]
    if image_keys:
        scenes = "\n".join(
            f"- {k.replace('_', ' ').replace('used', 'used:').capitalize()} "
            f"{stats[k]}"
            for k in image_keys
        )

    return f"""# Kairos Methodology Report — {req.display_name}

**Generated:** {generated}
**Platform:** Kairos SAR Analysis Platform

---

## 1. Summary

**{req.headline_label}: {value} {req.headline_unit}**

{cfg.get("description", "")}

Result confidence: **{conf_pct}%**.

## 2. Area of Interest

| | Longitude | Latitude |
|---|---|---|
| Min | {bbox[0]} | {bbox[1]} |
| Max | {bbox[2]} | {bbox[3]} |

Bounding box (min_lon, min_lat, max_lon, max_lat): `{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}`

## 3. Temporal Window

- **Analysis period:** {req.start_date} → {req.end_date}
- **Most recent acquisition used:** {req.data_date}

## 4. Data Source

- **Sensor:** {m.get("collection", "COPERNICUS/S1_GRD")} (Sentinel-1 C-band SAR)
- **Polarization / mode:** {m.get("band", "—")} / {m.get("mode", "—")}
- **Native resolution:** {m.get("resolution", "—")}
- **Category:** {cfg.get("category", "—")}

Sentinel-1 acquires day and night and penetrates cloud, smoke and haze, giving
consistent ~12-day revisit independent of weather.

## 5. Method

- **Detection rule:** {m.get("threshold", "—")}
- **Baseline / reference:** {m.get("baseline", "—")}
- **Masking:** {m.get("masking", "—")}
{scenes}

## 6. Confidence & Caveats

The {conf_pct}% confidence reflects acquisition density and method robustness for
this run. SAR detections can be affected by terrain, very low wind (over water),
and seasonal vegetation; treat results as decision-support, not ground truth.

## 7. Provenance & Reproducibility

- **Earth Engine collection:** `{m.get("collection", "COPERNICUS/S1_GRD")}`
- **Analysis type id:** `{req.analysis_type}`
- **Reproduce:** run the same analysis type over the bounding box and dates above.

## 8. Citation

Contains modified Copernicus Sentinel data ({req.data_date}), processed by the
European Space Agency and analysed on Google Earth Engine via Kairos.
"""


@router.post("/export/report")
def export_report(req: ReportRequest):
    """Return a citation-ready methodology report as markdown."""
    if req.analysis_type not in ANALYSIS_REGISTRY:
        raise HTTPException(
            status_code=400, detail=f"Unknown analysis type '{req.analysis_type}'."
        )
    markdown = _build_report_markdown(req)
    return {
        "filename": f"kairos_{req.analysis_type}_{req.data_date}_report.md",
        "markdown": markdown,
    }
