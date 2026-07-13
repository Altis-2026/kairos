import math
import threading

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

TIGERWEB_BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer"
MAX_RING_POINTS = 900

FIPS_TO_STATE = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "72": "PR",
}
STATE_TO_FIPS = {v: k for k, v in FIPS_TO_STATE.items()}

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "PR": "Puerto Rico",
}

_lock = threading.Lock()
_layer_cache: dict = {}
_result_cache: dict = {}


def _discover_layer(client: httpx.Client) -> dict:
    with _lock:
        if _layer_cache:
            return _layer_cache
    resp = client.get(TIGERWEB_BASE, params={"f": "json"})
    resp.raise_for_status()
    layers = resp.json().get("layers", [])
    layer_id = None
    for layer in layers:
        name = (layer.get("name") or "").lower()
        if "congressional" in name and "district" in name:
            layer_id = layer["id"]
            break
    if layer_id is None:
        raise RuntimeError("No congressional district layer found on TIGERweb")

    meta = client.get(f"{TIGERWEB_BASE}/{layer_id}", params={"f": "json"})
    meta.raise_for_status()
    fields = [f["name"] for f in meta.json().get("fields", [])]
    cd_field = next(
        (f for f in fields if f.upper().startswith("CD") and f.upper() != "CDSESSN"),
        "CD",
    )
    state_field = "STATE" if "STATE" in fields else next(
        (f for f in fields if f.upper() == "STATE"), "STATE"
    )
    with _lock:
        _layer_cache.update(
            {"layer_id": layer_id, "cd_field": cd_field, "state_field": state_field}
        )
        return _layer_cache


def _ring_area(ring: list) -> float:
    total = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def _largest_ring(geometry: dict) -> list:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    rings = []
    if gtype == "Polygon":
        rings = [coords[0]] if coords else []
    elif gtype == "MultiPolygon":
        rings = [poly[0] for poly in coords if poly]
    if not rings:
        return []
    ring = max(rings, key=_ring_area)
    if len(ring) > MAX_RING_POINTS:
        step = math.ceil(len(ring) / MAX_RING_POINTS)
        ring = ring[::step]
    return [[round(float(p[0]), 5), round(float(p[1]), 5)] for p in ring]


def _ring_bbox(ring: list) -> list:
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return [min(lons), min(lats), max(lons), max(lats)]


def _shape_district(feature: dict) -> dict:
    props = feature.get("properties") or {}
    fips = str(props.get("STATE", "")).zfill(2)
    abbr = FIPS_TO_STATE.get(fips, "US")
    state_name = STATE_NAMES.get(abbr, abbr)
    basename = str(props.get("BASENAME", "")).strip()
    if basename.isdigit():
        label = f"{abbr}-{int(basename):02d}"
        name = f"{state_name} District {int(basename)}"
    else:
        label = f"{abbr}-AL"
        name = f"{state_name} At-Large District"
    ring = _largest_ring(feature.get("geometry") or {})
    if len(ring) < 4:
        return {"found": False, "note": "District boundary was empty."}
    return {
        "found": True,
        "name": name,
        "label": label,
        "state_abbr": abbr,
        "state_name": state_name,
        "district_number": basename,
        "ring": ring,
        "bbox": _ring_bbox(ring),
        "vertex_count": len(ring),
    }


def _query_features(client: httpx.Client, layer: dict, params: dict) -> list:
    base_params = {
        "outFields": "STATE,BASENAME,NAME,GEOID",
        "returnGeometry": "true",
        "outSR": "4326",
        "maxAllowableOffset": "0.01",
        "f": "geojson",
    }
    base_params.update(params)
    resp = client.get(
        f"{TIGERWEB_BASE}/{layer['layer_id']}/query", params=base_params
    )
    resp.raise_for_status()
    return resp.json().get("features", [])


@router.get("/districts/locate")
def locate_district(
    lon: float = Query(ge=-180, le=180), lat: float = Query(ge=-90, le=90)
):
    cache_key = ("locate", round(lon, 3), round(lat, 3))
    if cache_key in _result_cache:
        return _result_cache[cache_key]
    try:
        with httpx.Client(timeout=25.0) as client:
            layer = _discover_layer(client)
            features = _query_features(
                client,
                layer,
                {
                    "geometry": f"{lon},{lat}",
                    "geometryType": "esriGeometryPoint",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                },
            )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach the Census district boundary service "
                f"({type(e).__name__}). Try again in a moment."
            ),
        )
    if not features:
        result = {
            "found": False,
            "note": "That point is not inside a US congressional district.",
        }
    else:
        result = _shape_district(features[0])
    _result_cache[cache_key] = result
    return result


@router.get("/districts/lookup")
def lookup_district(state: str, number: str):
    abbr = state.strip().upper()
    fips = STATE_TO_FIPS.get(abbr)
    if not fips:
        raise HTTPException(status_code=400, detail=f"Unknown state '{state}'.")
    num = number.strip().upper()
    cache_key = ("lookup", abbr, num)
    if cache_key in _result_cache:
        return _result_cache[cache_key]
    try:
        with httpx.Client(timeout=25.0) as client:
            layer = _discover_layer(client)
            if num in ("AL", "0", "00", "98"):
                where = f"{layer['state_field']} = '{fips}'"
            else:
                padded = num.zfill(2) if num.isdigit() else num
                where = (
                    f"{layer['state_field']} = '{fips}' AND "
                    f"{layer['cd_field']} = '{padded}'"
                )
            features = _query_features(client, layer, {"where": where})
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach the Census district boundary service "
                f"({type(e).__name__}). Try again in a moment."
            ),
        )
    if not features:
        result = {
            "found": False,
            "note": f"No district found for {abbr}-{num}.",
        }
    else:
        result = _shape_district(features[0])
    _result_cache[cache_key] = result
    return result
