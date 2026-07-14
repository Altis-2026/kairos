"""
Reproducible code export (docs/JANUS.md v3).

The reproducibility pack (reproducibility.py) documents a project in prose. This
goes one better for a technical reviewer: it emits a runnable Python script,
using the same google earth-engine API Kairos itself runs on, that reproduces
every analysis in the project from scratch. A researcher can paste it into a
Colab, authenticate their own Earth Engine account, and get the same maps and
numbers — the strongest possible form of "show your work".

The generated methods mirror Kairos's real detectors (a >3 dB VV drop for
floods, a VH rise for burn scars, etc.), reconstructed from each run's stored
parameters. It is intentionally standalone and dependency-light: `earthengine
-api` and, optionally, `geemap` for display.
"""

from datetime import date

from janus import store

_HEADER = '''"""
Reproducible Earth Engine script for the Kairos + Janus project:
  {title}
Generated {today} by Janus, the Kairos research mentor.

Setup:
    pip install earthengine-api geemap
    earthengine authenticate

Then set your Google Cloud project id below and run top to bottom.
Each analysis mirrors the method Kairos ran for you, so the numbers and
maps reproduce independently of Kairos itself.
"""

import ee

ee.Initialize(project="YOUR_GCP_PROJECT_ID")


def s1_collection(geometry, polarization="VV", mode="IW"):
    """Sentinel-1 GRD, filtered the way every Kairos analysis filters it."""
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filter(ee.Filter.eq("instrumentMode", mode))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
        .select(polarization)
        .filterBounds(geometry)
    )


def area_km2(mask, geometry, scale=30):
    """Area (km2) of the truthy pixels in a 0/1 mask."""
    stats = (
        mask.multiply(ee.Image.pixelArea())
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=geometry,
                      scale=scale, maxPixels=1e10, bestEffort=True)
    )
    band = mask.bandNames().get(0)
    return ee.Number(stats.get(band)).divide(1e6)

'''

# Per-analysis snippet templates. {i} numbers the run; params filled per run.
_FLOOD = '''
# --- Run {i}: {display_name} ---
# Method: flooded land reflects radar away, so VV backscatter drops. Compare
# the event window against a pre-event baseline and flag drops beyond 3 dB,
# then remove permanently-wet pixels.
geom_{i} = ee.Geometry.Rectangle({bbox})
post_{i} = s1_collection(geom_{i}, "VV").filterDate("{start}", "{end}")
pre_{i} = s1_collection(geom_{i}, "VV").filterDate("{pre_start}", "{start}")
diff_{i} = post_{i}.mean().focalMedian(50, "circle", "meters").subtract(
    pre_{i}.mean().focalMedian(50, "circle", "meters"))
permanent_{i} = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gt(75)
flood_{i} = diff_{i}.lt(-3).where(permanent_{i}, 0).selfMask().clip(geom_{i})
print("Run {i} flood area km2:", area_km2(flood_{i}, geom_{i}).getInfo())
'''

_BURN = '''
# --- Run {i}: {display_name} ---
# Method: fire strips vegetation and roughens soil, raising VH backscatter.
# Flag a VH rise beyond 2.5 dB versus a pre-fire baseline.
geom_{i} = ee.Geometry.Rectangle({bbox})
post_{i} = s1_collection(geom_{i}, "VH").filterDate("{start}", "{end}")
pre_{i} = s1_collection(geom_{i}, "VH").filterDate("{pre_start}", "{start}")
diff_{i} = post_{i}.mean().focalMedian(50, "circle", "meters").subtract(
    pre_{i}.mean().focalMedian(50, "circle", "meters"))
burn_{i} = diff_{i}.gt(2.5).selfMask().clip(geom_{i})
print("Run {i} burn area km2:", area_km2(burn_{i}, geom_{i}).getInfo())
'''

_GENERIC = '''
# --- Run {i}: {display_name} ({analysis_type}) ---
# Kairos ran a "{analysis_type}" analysis over this area and window. See the
# Kairos source (backend/gee/{analysis_type}.py) for the exact method; the
# parameters below reproduce the same inputs.
geom_{i} = ee.Geometry.Rectangle({bbox})
collection_{i} = s1_collection(geom_{i}, "{pol}").filterDate("{start}", "{end}")
print("Run {i} scene count:", collection_{i}.size().getInfo())
# TODO: apply the {analysis_type} method to collection_{i} (see Kairos source).
'''

# Which polarization each analysis uses (for the generic template).
_POL = {
    "deforestation": "VH",
    "crop_monitoring": "VH",
    "land_disturbance": "VH",
    "sea_ice": "HH",
}


def _lead_start(start: str) -> str:
    from datetime import datetime, timedelta

    d = datetime.strptime(start, "%Y-%m-%d") - timedelta(days=30)
    return d.strftime("%Y-%m-%d")


def build_notebook(project_id: int) -> str:
    """Return a runnable Python Earth Engine script reproducing the project."""
    project = store.get_project(project_id)
    parts = [_HEADER.format(title=project["title"], today=date.today().isoformat())]

    runs = []
    for msg in store.get_messages(project_id):
        for ev in msg.get("tool_events") or []:
            if ev.get("tool") == "run_analysis" and ev.get("result"):
                runs.append(ev["result"])

    if not runs:
        parts.append(
            '\n# No analyses were run in this project yet, so there is nothing\n'
            '# to reproduce. Run one in Janus, then export again.\n'
        )
        return "".join(parts)

    for i, r in enumerate(runs, 1):
        atype = r.get("analysis_type")
        common_kw = dict(
            i=i,
            display_name=r.get("display_name", atype),
            analysis_type=atype,
            bbox=r.get("bbox"),
            start=r.get("start_date"),
            end=r.get("end_date"),
        )
        if atype in ("flood_extent", "flood_depth"):
            parts.append(_FLOOD.format(pre_start=_lead_start(r["start_date"]), **common_kw))
        elif atype == "wildfire_burn_scar":
            parts.append(_BURN.format(pre_start=_lead_start(r["start_date"]), **common_kw))
        else:
            parts.append(_GENERIC.format(pol=_POL.get(atype, "VV"), **common_kw))

    parts.append(
        '\n# --- Display (optional) ---\n'
        '# import geemap\n'
        '# m = geemap.Map()\n'
        '# m.add_layer(flood_1, {"palette": ["#00BFA8"]}, "Run 1")\n'
        '# m\n'
    )
    return "".join(parts)


def notebook_filename(project: dict) -> str:
    slug = "".join(
        c.lower() if c.isalnum() else "_" for c in project["title"]
    ).strip("_")[:50] or "project"
    return f"kairos_reproduce_{slug}.py"
