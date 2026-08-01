import json
import math
import os
from datetime import datetime, timezone

import ee

from gee import common

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ais")

# Radar detections are matched to the AIS position nearest in time. Because a
# ship keeps moving between its last broadcast and the radar pass, the match
# radius grows with that time gap at 10 m/s, roughly 19 knots, which is faster
# than most commercial traffic.
BASE_RADIUS_M = 300
DRIFT_SPEED_MS = 10.0
MAX_RADIUS_M = 2000

CASES = [
    {
        "id": "gulf-delta-2023",
        "name": "Mississippi River delta, Gulf of Mexico",
        "region": "Offshore Louisiana, United States",
        "bbox": [-89.6, 28.6, -88.9, 29.2],
        "target_date": "2023-01-15",
        "why": (
            "Heavy commercial traffic, active fishing grounds and hundreds of "
            "fixed platforms sit in one place, so it is a hard, realistic test "
            "of whether radar detections can be matched to transponders."
        ),
        "ais_source": "MarineCadastre.gov (NOAA and BOEM) daily AIS archive",
        "ais_url": "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2023/",
    },
]


def get_case(case_id: str) -> dict:
    for case in CASES:
        if case["id"] == case_id:
            return case
    raise ValueError(
        f"Unknown case '{case_id}'. Available: {[c['id'] for c in CASES]}"
    )


def ais_path(case_id: str) -> str:
    return os.path.join(DATA_DIR, f"{case_id}.json")


def case_available(case_id: str) -> bool:
    return os.path.exists(ais_path(case_id))


def _load_ais(case_id: str) -> dict:
    path = ais_path(case_id)
    if not os.path.exists(path):
        raise ValueError(
            "The AIS record for this case is not installed on this server. "
            "Run tools/get_ais_case.py to download it from MarineCadastre."
        )
    with open(path) as f:
        return json.load(f)


def _haversine_m(lon1, lat1, lon2, lat2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _radar_detections(case: dict, window_days: int = 2) -> dict:
    """Run the production ship detector and keep the acquisition timestamp."""
    geometry = common.bbox_geometry(case["bbox"])
    target = ee.Date(case["target_date"])
    period = (
        common.s1_collection(geometry, polarization="VV")
        .filterDate(
            target.advance(-window_days, "day"), target.advance(window_days, "day")
        )
        .sort("system:time_start", False)
    )
    count = period.size().getInfo()
    if count == 0:
        raise ValueError(
            f"No Sentinel-1 acquisition within {window_days} days of "
            f"{case['target_date']} over this area."
        )

    latest = ee.Image(period.first())
    epoch_ms = latest.get("system:time_start").getInfo()

    water = common.permanent_water_mask(50)
    ocean_vv = latest.updateMask(water)

    stats = ocean_vv.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
        geometry=geometry,
        scale=100,
        maxPixels=1e10,
        bestEffort=True,
    )
    mean = ee.Number(stats.get("VV_mean"))
    std = ee.Number(stats.get("VV_stdDev"))
    threshold = mean.add(std.multiply(5))
    detections = ocean_vv.gt(ee.Image.constant(threshold)).selfMask().clip(geometry)

    vectors = detections.reduceToVectors(
        geometry=geometry,
        scale=50,
        geometryType="centroid",
        maxPixels=1e10,
        bestEffort=True,
    )
    features = vectors.limit(600).getInfo().get("features", [])
    points = []
    for f in features:
        coords = f.get("geometry", {}).get("coordinates")
        if coords and len(coords) == 2:
            points.append((float(coords[0]), float(coords[1])))

    return {
        "points": points,
        "epoch_ms": int(epoch_ms),
        "tile_url": common.tile_url(
            detections, {"palette": [common.AMBER], "min": 0, "max": 1}
        ),
    }


def _nearest_in_time(records: list, epoch_ms: int) -> dict:
    """One position per vessel: the broadcast closest to the radar pass."""
    best = {}
    for r in records:
        key = r.get("mmsi")
        if key is None:
            continue
        gap = abs(int(r["t"]) - epoch_ms)
        prev = best.get(key)
        if prev is None or gap < prev["gap_ms"]:
            best[key] = {
                "mmsi": key,
                "name": r.get("name"),
                "length_m": r.get("length_m"),
                "lon": float(r["lon"]),
                "lat": float(r["lat"]),
                "gap_ms": gap,
            }
    return best


def screen_case(case_id: str) -> dict:
    case = get_case(case_id)
    ais = _load_ais(case_id)
    radar = _radar_detections(case)

    epoch_ms = radar["epoch_ms"]
    broadcasts = _nearest_in_time(ais.get("records", []), epoch_ms)

    matched_points = []
    unmatched_points = []
    matched_mmsi = set()
    radii = []

    for lon, lat in radar["points"]:
        best_dist = None
        best_vessel = None
        for vessel in broadcasts.values():
            gap_s = vessel["gap_ms"] / 1000.0
            radius = min(
                MAX_RADIUS_M, BASE_RADIUS_M + gap_s * DRIFT_SPEED_MS
            )
            dist = _haversine_m(lon, lat, vessel["lon"], vessel["lat"])
            if dist <= radius and (best_dist is None or dist < best_dist):
                best_dist = dist
                best_vessel = vessel
                radii.append(radius)
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {},
        }
        if best_vessel is not None:
            matched_mmsi.add(best_vessel["mmsi"])
            feature["properties"] = {
                "status": "broadcasting",
                "name": best_vessel.get("name") or "unnamed",
                "distance_m": round(best_dist),
                "ais_gap_minutes": round(best_vessel["gap_ms"] / 60000, 1),
            }
            matched_points.append(feature)
        else:
            feature["properties"] = {"status": "unmatched"}
            unmatched_points.append(feature)

    total = len(radar["points"])
    unmatched = len(unmatched_points)
    radar_time = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)

    return {
        "case": {k: v for k, v in case.items()},
        "radar_time_utc": radar_time.strftime("%Y-%m-%d %H:%M UTC"),
        "data_date": radar_time.strftime("%Y-%m-%d"),
        "tile_url": radar["tile_url"],
        "detections_total": total,
        "matched_count": len(matched_points),
        "unmatched_count": unmatched,
        "ais_vessels_in_window": len(broadcasts),
        "match_radius_m": {
            "base": BASE_RADIUS_M,
            "typical": round(sum(radii) / len(radii)) if radii else BASE_RADIUS_M,
            "max": MAX_RADIUS_M,
        },
        "matched": {"type": "FeatureCollection", "features": matched_points},
        "unmatched": {"type": "FeatureCollection", "features": unmatched_points},
        "ais_window": ais.get("window"),
        "headline_stat": {
            "label": "Radar returns with no matching transponder",
            "value": unmatched,
            "unit": "of " + str(total),
        },
        "caveats": [
            "An unmatched radar return is not evidence of wrongdoing. Only "
            "larger commercial vessels are required to broadcast AIS, so small "
            "boats legitimately appear dark.",
            "Fixed structures put permanent bright returns on the radar. This "
            "area has hundreds of oil and gas platforms, and each one reads as "
            "an unmatched detection.",
            "Radar also picks up breaking waves and clutter, which inflates "
            "the unmatched count.",
            "AIS positions are broadcasts, not continuous tracks. Each "
            "detection is matched to the broadcast nearest in time, with the "
            "radius widened for how far the ship could have travelled.",
            "This is what a screening pass looks like, on one historical date, "
            "in one place. It is a method demonstration, not surveillance.",
        ],
    }
