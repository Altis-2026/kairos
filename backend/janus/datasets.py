"""
Bring-your-own-data (v1): user vectors as first-class project inputs.

A researcher's own field data is the most valuable data they have. This lets
them attach it to a project — GeoJSON polygons/points, or a CSV of lat/lon
points — and use it two ways:

  * as an AOI: "run the analysis over MY study plots" (bbox derived from the
    data's extent);
  * as ground truth: score any Kairos detection against their own mapped
    polygons with the same IoU/precision/recall/F1 machinery the public
    benchmarks use. Your field campaign becomes a private validation set.

Geometries are passed to Earth Engine inline (no asset ingestion, no GCS
plumbing), which is exactly why v1 caps uploads at 1 MB — enough for
thousands of plot polygons, small enough to ship inside a request. Rasters
(your own GeoTIFFs) are the separate BYO-imagery path (research/cog_preview).
"""

from __future__ import annotations

import csv
import io
import json
import time

from janus import store

MAX_BYTES = 1_000_000


# --------------------------------------------------------------------------- #
# Parsing / normalizing.
# --------------------------------------------------------------------------- #
def csv_to_geojson(text: str) -> dict:
    """
    CSV with lon/lat (or longitude/latitude, x/y) columns -> Point
    FeatureCollection. Any other columns ride along as properties.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV appears to be empty.")
    lower = {c.lower().strip(): c for c in reader.fieldnames}
    lon_col = next((lower[k] for k in ("lon", "longitude", "x") if k in lower), None)
    lat_col = next((lower[k] for k in ("lat", "latitude", "y") if k in lower), None)
    if not lon_col or not lat_col:
        raise ValueError(
            "CSV needs lon/lat columns (accepted names: lon/longitude/x and "
            "lat/latitude/y)."
        )
    features = []
    for i, row in enumerate(reader):
        if i >= 20_000:
            raise ValueError("CSV has more than 20,000 rows — split it up.")
        try:
            lon, lat = float(row[lon_col]), float(row[lat_col])
        except (TypeError, ValueError):
            continue
        props = {
            k: v for k, v in row.items() if k not in (lon_col, lat_col)
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )
    if not features:
        raise ValueError("No rows with valid coordinates found in the CSV.")
    return {"type": "FeatureCollection", "features": features}


def _iter_coords(geom: dict):
    t = geom.get("type")
    c = geom.get("coordinates", [])
    if t == "Point":
        yield c
    elif t in ("MultiPoint", "LineString"):
        yield from c
    elif t in ("MultiLineString", "Polygon"):
        for part in c:
            yield from part
    elif t == "MultiPolygon":
        for poly in c:
            for ring in poly:
                yield from ring
    elif t == "GeometryCollection":
        for g in geom.get("geometries", []):
            yield from _iter_coords(g)


def geojson_bbox(geojson: dict) -> list:
    """[min_lon, min_lat, max_lon, max_lat] over every geometry present."""
    feats = (
        geojson.get("features", [])
        if geojson.get("type") == "FeatureCollection"
        else [geojson]
    )
    lons, lats = [], []
    for f in feats:
        geom = f.get("geometry") or f
        for lon, lat in _iter_coords(geom):
            lons.append(float(lon))
            lats.append(float(lat))
    if not lons:
        raise ValueError("No coordinates found in the GeoJSON.")
    return [min(lons), min(lats), max(lons), max(lats)]


def validate_geojson(geojson: dict) -> dict:
    if not isinstance(geojson, dict) or geojson.get("type") not in (
        "FeatureCollection",
        "Feature",
    ):
        raise ValueError("Expected a GeoJSON Feature or FeatureCollection.")
    if len(json.dumps(geojson)) > MAX_BYTES:
        raise ValueError("Dataset is over the 1 MB inline limit — simplify or split it.")
    geojson_bbox(geojson)  # raises if empty/degenerate
    return geojson


# --------------------------------------------------------------------------- #
# Storage (own table in the Janus store DB).
# --------------------------------------------------------------------------- #
def _init():
    with store._lock, store._connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                feature_count INTEGER,
                bbox TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()


def add_dataset(project_id: int, name: str, geojson: dict) -> dict:
    _init()
    validate_geojson(geojson)
    bbox = geojson_bbox(geojson)
    feats = (
        geojson.get("features", [geojson])
        if geojson.get("type") == "FeatureCollection"
        else [geojson]
    )
    with store._lock, store._connect() as conn:
        cur = conn.execute(
            "INSERT INTO datasets (project_id, name, content, feature_count, "
            "bbox, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                project_id,
                name[:120],
                json.dumps(geojson),
                len(feats),
                json.dumps(bbox),
                time.time(),
            ),
        )
        conn.commit()
        ds_id = int(cur.lastrowid)
    return {
        "id": ds_id,
        "name": name[:120],
        "feature_count": len(feats),
        "bbox": bbox,
    }


def list_datasets(project_id: int) -> list:
    _init()
    with store._lock, store._connect() as conn:
        rows = conn.execute(
            "SELECT id, name, feature_count, bbox, created_at FROM datasets "
            "WHERE project_id = ? ORDER BY id DESC",
            (project_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "feature_count": r["feature_count"],
            "bbox": json.loads(r["bbox"]) if r["bbox"] else None,
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_dataset(dataset_id: int, project_id: int) -> dict:
    _init()
    with store._lock, store._connect() as conn:
        row = conn.execute(
            "SELECT * FROM datasets WHERE id = ? AND project_id = ?",
            (dataset_id, project_id),
        ).fetchone()
    if not row:
        raise ValueError(f"No dataset {dataset_id} in this project.")
    return {
        "id": row["id"],
        "name": row["name"],
        "geojson": json.loads(row["content"]),
        "feature_count": row["feature_count"],
        "bbox": json.loads(row["bbox"]) if row["bbox"] else None,
    }


def delete_dataset(dataset_id: int, project_id: int):
    _init()
    with store._lock, store._connect() as conn:
        conn.execute(
            "DELETE FROM datasets WHERE id = ? AND project_id = ?",
            (dataset_id, project_id),
        )
        conn.commit()


# --------------------------------------------------------------------------- #
# Using a dataset as ground truth against any analysis.
# --------------------------------------------------------------------------- #
def validate_against_dataset(
    dataset_id: int,
    project_id: int,
    analysis_type: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Run the production detector over the dataset's extent, rasterize the
    user's polygons as reference truth, and score with the same
    IoU/precision/recall/F1 machinery as the public benchmarks.
    """
    import ee
    from gee import common
    from gee.registry import ANALYSIS_REGISTRY
    from gee.validation import _agreement_metrics

    ds = get_dataset(dataset_id, project_id)
    if analysis_type not in ANALYSIS_REGISTRY:
        raise ValueError(f"Unknown analysis type '{analysis_type}'.")

    # Pad the data extent slightly so edge polygons aren't clipped.
    b = ds["bbox"]
    pad = max(0.02, (b[2] - b[0]) * 0.1)
    bbox = [b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad]
    geometry = common.bbox_geometry(bbox)

    raw = ANALYSIS_REGISTRY[analysis_type]["function"](
        bbox=bbox, start_date=start_date, end_date=end_date
    )
    ours = raw["result_image"]

    feats = ds["geojson"].get("features", [ds["geojson"]])
    ee_feats = [
        ee.Feature(ee.Geometry(f["geometry"])) for f in feats if f.get("geometry")
    ]
    reference = (
        ee.FeatureCollection(ee_feats)
        .map(lambda f: f.set("v", 1))
        .reduceToImage(["v"], ee.Reducer.first())
        .unmask(0)
        .gt(0)
        .clip(geometry)
    )

    metrics = _agreement_metrics(ours, reference, geometry, scale=30)
    return {
        "dataset": {"id": ds["id"], "name": ds["name"], "features": ds["feature_count"]},
        "analysis_type": analysis_type,
        "window": f"{start_date} to {end_date}",
        "metrics": metrics,
        "data_date": raw.get("data_date"),
        "note": (
            "Your polygons were rasterized as reference truth and compared "
            "against the production detector over the same extent — the same "
            "scoring as Kairos's public benchmarks, on your own field data."
        ),
    }
