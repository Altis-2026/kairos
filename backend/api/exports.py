import math
from datetime import datetime, timezone

import ee
from fastapi import APIRouter, HTTPException

from models.requests import AnalyzeRequest, BriefingRequest, ReportRequest
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()

_BASE_SCALE = {
    "flood_extent": 30,
    "ship_detection": 50,
    "wildfire_burn_scar": 30,
    "oil_spill": 50,
    "deforestation": 30,
    "sea_ice": 100,
    "surface_deformation": 30,
}

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
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = (min_lat + max_lat) / 2
    width_m = (max_lon - min_lon) * 111320 * math.cos(math.radians(mid_lat))
    height_m = (max_lat - min_lat) * 110540
    longest = max(width_m, height_m, 1)
    return int(round(max(base_scale, longest / max_px)))


@router.post("/export/geotiff")
def export_geotiff(req: AnalyzeRequest):
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
                "Could not build the GeoTIFF. The area may be too large for a "
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

    return f"""# Kairos Methodology Report: {req.display_name}

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
- **Polarization / mode:** {m.get("band", "n/a")} / {m.get("mode", "n/a")}
- **Native resolution:** {m.get("resolution", "n/a")}
- **Category:** {cfg.get("category", "n/a")}

Sentinel-1 acquires day and night and penetrates cloud, smoke and haze, giving
consistent ~12-day revisit independent of weather.

## 5. Method

- **Detection rule:** {m.get("threshold", "n/a")}
- **Baseline / reference:** {m.get("baseline", "n/a")}
- **Masking:** {m.get("masking", "n/a")}
{scenes}

## 6. Confidence & Caveats

The {conf_pct}% confidence reflects how many radar passes were available and how reliable this method is for
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
    if req.analysis_type not in ANALYSIS_REGISTRY:
        raise HTTPException(
            status_code=400, detail=f"Unknown analysis type '{req.analysis_type}'."
        )
    markdown = _build_report_markdown(req)
    return {
        "filename": f"kairos_{req.analysis_type}_{req.data_date}_report.md",
        "markdown": markdown,
    }


def _fmt_value(v: float) -> str:
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.1f}"


def _briefing_bluf(req) -> str:
    starts = [f.start_date for f in req.findings]
    ends = [f.end_date for f in req.findings]
    parts = []
    for f in req.findings:
        parts.append(
            f"{f.display_name.lower()} measured "
            f"{_fmt_value(f.headline_value)} {f.headline_unit} "
            f"({f.headline_label.lower()}, satellite pass {f.data_date})"
        )
    joined = "; ".join(parts)
    return (
        f"Sentinel-1 radar analysis of {req.area_name} covering "
        f"{min(starts)} to {max(ends)} produced {len(req.findings)} "
        f"finding{'s' if len(req.findings) != 1 else ''}: {joined}. "
        "Figures are modelled estimates from open satellite radar data and "
        "should be verified against ground reports before operational use."
    )


def _build_briefing_html(req) -> str:
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    label = f" ({req.area_label})" if req.area_label else ""
    area_line = (
        f"{_fmt_value(req.area_km2)} km² analysed"
        if req.area_km2
        else "See finding footprints"
    )
    prepared = req.prepared_for or "General distribution"

    rows = []
    for i, f in enumerate(req.findings, start=1):
        method = _METHOD.get(f.analysis_type, {})
        summary = f.summary or (
            f"{f.display_name} over the area of interest returned "
            f"{f.headline_label.lower()} of {_fmt_value(f.headline_value)} "
            f"{f.headline_unit}, based on the Sentinel-1 acquisition of "
            f"{f.data_date}."
        )
        rows.append(f"""
      <section class="finding">
        <h3>{i}. {f.display_name}</h3>
        <div class="stat">{f.headline_label}: <b>{_fmt_value(f.headline_value)} {f.headline_unit}</b>
          <span class="conf">{round(f.confidence * 100)}% confidence</span></div>
        <p>{summary}</p>
        <div class="meta">Window {f.start_date} to {f.end_date} · latest pass {f.data_date}
          · method: {method.get("threshold", "Sentinel-1 backscatter change detection")}</div>
      </section>""")

    findings_html = "\n".join(rows)

    return f"""<meta charset="utf-8">
<title>Kairos briefing: {req.area_name}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #111;
         background: #fff; max-width: 760px; margin: 40px auto; padding: 0 24px;
         line-height: 1.55; }}
  .letterhead {{ display: flex; justify-content: space-between; align-items: baseline;
         border-bottom: 3px double #111; padding-bottom: 10px; }}
  .letterhead .org {{ font-size: 13px; letter-spacing: 3px; font-weight: bold; }}
  .letterhead .date {{ font-size: 12px; color: #444; }}
  h1 {{ font-size: 26px; margin: 26px 0 4px; }}
  .subtitle {{ font-size: 13px; color: #444; margin-bottom: 22px; }}
  table.meta-block {{ font-size: 13px; border-collapse: collapse; margin-bottom: 24px; }}
  table.meta-block td {{ padding: 3px 18px 3px 0; vertical-align: top; }}
  table.meta-block td:first-child {{ font-weight: bold; width: 110px; }}
  h2 {{ font-size: 13px; letter-spacing: 2px; text-transform: uppercase;
        border-bottom: 1px solid #999; padding-bottom: 4px; margin-top: 30px; }}
  .bluf {{ background: #f4f4f0; border-left: 4px solid #0d7a6e; padding: 12px 16px;
        font-size: 14px; }}
  .finding {{ margin-top: 18px; }}
  .finding h3 {{ font-size: 15px; margin: 0 0 4px; }}
  .finding .stat {{ font-size: 14px; }}
  .finding .stat b {{ color: #0d7a6e; }}
  .finding .conf {{ font-size: 11px; color: #666; margin-left: 10px; }}
  .finding p {{ font-size: 13px; margin: 6px 0; }}
  .finding .meta {{ font-size: 11px; color: #666; }}
  .footer {{ margin-top: 36px; border-top: 1px solid #999; padding-top: 10px;
        font-size: 11px; color: #555; }}
  .print-btn {{ position: fixed; top: 14px; right: 14px; padding: 8px 16px;
        background: #0d7a6e; color: #fff; border: 0; border-radius: 6px;
        font-size: 13px; cursor: pointer; }}
  @media print {{ .print-btn {{ display: none; }} body {{ margin: 0; }} }}
</style>
<button class="print-btn" onclick="window.print()">Print / save as PDF</button>
<div class="letterhead">
  <span class="org">KAIROS EARTH OBSERVATION</span>
  <span class="date">{generated}</span>
</div>
<h1>Situation Briefing</h1>
<div class="subtitle">Open-source satellite radar assessment</div>
<table class="meta-block">
  <tr><td>Subject</td><td>{req.area_name}{label}</td></tr>
  <tr><td>Prepared for</td><td>{prepared}</td></tr>
  <tr><td>Coverage</td><td>{area_line}</td></tr>
  <tr><td>Data source</td><td>Copernicus Sentinel-1 C-band SAR via Google Earth Engine</td></tr>
</table>
<h2>Bottom line</h2>
<p class="bluf">{_briefing_bluf(req)}</p>
<h2>Findings</h2>
{findings_html}
<h2>Methodology</h2>
<p style="font-size:13px">Each finding is derived from Sentinel-1 synthetic aperture radar
backscatter, comparing the analysis window against a historical baseline for the same
area. Radar imaging is independent of cloud cover and daylight, so acquisitions are
consistent regardless of weather. Computation runs server-side on Google Earth Engine
against the full Copernicus archive; no imagery is modified by hand.</p>
<h2>Caveats</h2>
<p style="font-size:13px">Radar backscatter responds to surface roughness and moisture,
not directly to the phenomenon of interest. Wet farmland can resemble flooding, calm water
can resemble an oil slick, and terrain shadowing can mask detections. Confidence figures
reflect data availability and method reliability, not ground-truth validation. Treat this
briefing as decision support, not as a verified assessment.</p>
<div class="footer">
  Generated by Kairos, a student-built Earth observation platform.
  Contains modified Copernicus Sentinel data processed by the European Space Agency,
  analysed on Google Earth Engine. Population and district figures where shown are
  modelled estimates.
</div>
"""


@router.post("/export/briefing")
def export_briefing(req: BriefingRequest):
    html = _build_briefing_html(req)
    safe = "".join(c if c.isalnum() else "-" for c in req.area_name.lower())[:40]
    return {
        "filename": f"kairos_briefing_{safe}.html",
        "html": html,
    }
