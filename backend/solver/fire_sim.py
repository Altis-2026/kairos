"""
Wildfire simulation as a Kairos analysis: AOI in, an animated burn out.

Orchestration only — the physics is in `fire_behavior` and `fire_spread`, the
fetching in `gee.raster_fetch`. Its job is to turn a bounding box and a handful
of parameters into a solve, and the solve into the same result envelope every
other Kairos analysis returns, so the registry, job queue, provenance stamping
and frontend handle it with no special cases.

What it is not
--------------
Every result from here is **simulated**. The terrain is real and the fire
behaviour equations are the ones fire agencies use, but the fuel, the wind and
the ignition are choices a person made. That is categorically different from
`wildfire_burn_scar`, which maps a fire that actually happened. The result
carries `mode: "simulated"` inside its provenance hash, a disclosure string,
and a confidence value explicitly labelled as numerical integrity rather than
forecast skill.

Transport
---------
The flood simulator ships one frame per timestep. A fire does not need that:
the solve produces an *arrival time* per cell, and every frame of the
animation is a threshold of that one array. So a fire ships a single uint16
grid of arrival minutes instead of dozens of depth grids — roughly fifty times
smaller for the same animation, and smoother, because the client can threshold
at any instant rather than stepping between precomputed frames.
"""

import base64

import numpy as np

from solver import fire_presets
from solver.fire_behavior import DEFAULT_MOISTURE, FUEL_MODELS, prepare
from solver.fire_spread import spread

#: Arrival time is stored as minutes in a uint16, so 65535 minutes — six weeks
#: — is the ceiling. `duration_hours` is capped far below that.
_ARRIVAL_UNBURNED = 65535
#: Flame length in decimetres, uint16. A decimetre is finer than the model's
#: own error bars and gives a 6.5 km ceiling nothing will approach.
FLAME_SCALE = 10.0

#: Wall-clock budget for one solve, leaving room for fetch and encode either
#: side of the rq queue's own 600 s timeout.
DEFAULT_MAX_SECONDS = 420.0

#: Past this many cells a Dijkstra pass in Python stops being interactive.
MAX_CELLS = 640_000

DISCLOSURE = (
    "SIMULATED — this is a forward fire behaviour model, not a satellite "
    "observation and not a forecast. Terrain is real (Copernicus GLO-30) and "
    "the physics are Rothermel surface spread propagated by minimum travel "
    "time, but the fuel model, wind, moisture and ignition point are assumed "
    "inputs. It models a surface fire only — no crown fire, no spotting, no "
    "fire-atmosphere coupling and no suppression — and it has not been "
    "calibrated against any observed fire. For a fire that actually happened, "
    "run Wildfire Burn Scar Mapping."
)

DEFAULTS = {
    "fuel_model": "sh5",
    "wind_ms": 5.0,
    "wind_from_bearing": 270.0,
    "duration_hours": 8.0,
    "moisture_1h": DEFAULT_MOISTURE["dead_1h"],
    "moisture_10h": DEFAULT_MOISTURE["dead_10h"],
    "moisture_100h": DEFAULT_MOISTURE["dead_100h"],
    "moisture_live": DEFAULT_MOISTURE["live"],
    "scale_m": 30.0,
    "neighbours": 32,
    "max_seconds": DEFAULT_MAX_SECONDS,
}

_POSITIVE = ("duration_hours", "scale_m")
_NON_NEGATIVE = ("wind_ms",)
_MOISTURES = ("moisture_1h", "moisture_10h", "moisture_100h", "moisture_live")


def _as_number(key: str, value) -> float:
    """Coerce to float, failing as a user error rather than a 500."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number; got {value!r}.") from None
    if not np.isfinite(number):
        raise ValueError(f"{key} must be a finite number; got {value!r}.")
    return number


def resolve_params(params: dict | None) -> dict:
    """
    Merge user parameters over the scene preset over the defaults.

    Precedence is explicit-parameter > scene > default, so a user can pick a
    showcase scene and still turn the wind up without losing its other tuning.
    """
    supplied = dict(params or {})
    scene_id = supplied.pop("scene", None)

    resolved = dict(DEFAULTS)
    scene = None
    if scene_id:
        scene = fire_presets.get_scene(scene_id)
        resolved.update({
            "fuel_model": scene.fuel_model,
            "wind_ms": scene.wind_ms,
            "wind_from_bearing": scene.wind_from_bearing,
            "duration_hours": scene.duration_hours,
            "moisture_1h": scene.moisture_1h,
            "moisture_10h": scene.moisture_10h,
            "moisture_100h": scene.moisture_100h,
            "moisture_live": scene.moisture_live,
            "scale_m": scene.scale_m,
        })

    allowed = set(DEFAULTS) | {"scene", "ignition_point"}
    unknown = set(supplied) - allowed
    if unknown:
        raise ValueError(
            f"Unknown simulation parameter(s) {sorted(unknown)}. "
            f"Valid: {sorted(allowed)}"
        )
    resolved.update(supplied)

    if resolved["fuel_model"] not in FUEL_MODELS:
        raise ValueError(
            f"Unknown fuel_model {resolved['fuel_model']!r}. "
            f"Available: {sorted(FUEL_MODELS)}"
        )

    for key in _POSITIVE:
        resolved[key] = _as_number(key, resolved[key])
        if resolved[key] <= 0:
            raise ValueError(f"{key} must be positive; got {resolved[key]}.")
    for key in _NON_NEGATIVE:
        resolved[key] = _as_number(key, resolved[key])
        if resolved[key] < 0:
            raise ValueError(f"{key} must be non-negative; got {resolved[key]}.")

    for key in _MOISTURES:
        value = _as_number(key, resolved[key])
        if not (0.0 < value <= 5.0):
            raise ValueError(
                f"{key} is a fraction, not a percentage: 0.06 means 6%. "
                f"Got {value}."
            )
        resolved[key] = value

    bearing = _as_number("wind_from_bearing", resolved["wind_from_bearing"])
    resolved["wind_from_bearing"] = bearing % 360.0

    if resolved["duration_hours"] > 72:
        raise ValueError(
            f"duration_hours is capped at 72; got {resolved['duration_hours']}. "
            f"This is a demonstration solver, not an operational one."
        )

    # A midflame wind above gale force is almost always a 10 m weather wind
    # passed in by mistake, which would overstate spread by a factor of
    # several. Reject it with the reason rather than silently modelling it.
    if resolved["wind_ms"] > 25.0:
        raise ValueError(
            f"wind_ms is the MIDFLAME wind, typically a third to a half of "
            f"the 10 m weather-station wind. {resolved['wind_ms']} m/s is "
            f"implausible as a midflame value."
        )

    neighbours = int(resolved["neighbours"])
    if neighbours not in (8, 16, 32):
        raise ValueError(f"neighbours must be 8, 16 or 32; got {neighbours}.")
    resolved["neighbours"] = neighbours

    resolved["max_seconds"] = min(
        _as_number("max_seconds", resolved["max_seconds"]), DEFAULT_MAX_SECONDS
    )
    resolved["scene"] = scene
    return resolved


def ignition_mask_for(dem: np.ndarray, ignition_point=None, bbox=None) -> tuple:
    """
    Where the fire starts. Returns ``(mask, description)``.

    A single cell, deliberately. A fire starts at a point, and spreading the
    ignition over a patch would hide exactly the thing the elliptical model
    exists to show — the shape the fire takes as it grows away from its
    origin. With no explicit point the domain centre is used.
    """
    ny, nx = dem.shape
    mask = np.zeros(dem.shape, dtype=bool)

    if ignition_point is None:
        row, col = ny // 2, nx // 2
        mask[row, col] = True
        return mask, "domain centre (no ignition point given)"

    if bbox is None:
        raise ValueError("ignition_point requires the AOI bbox to place it.")
    lon, lat = float(ignition_point[0]), float(ignition_point[1])
    min_lon, min_lat, max_lon, max_lat = bbox
    if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
        raise ValueError(
            f"Ignition point ({lon}, {lat}) is outside the AOI {list(bbox)}."
        )
    fx = (lon - min_lon) / (max_lon - min_lon)
    fy = (max_lat - lat) / (max_lat - min_lat)      # row 0 is north
    row = min(max(int(round(fy * (ny - 1))), 0), ny - 1)
    col = min(max(int(round(fx * (nx - 1))), 0), nx - 1)
    mask[row, col] = True
    return mask, f"user-placed at ({lon:.4f}, {lat:.4f})"


def _b64(arr: np.ndarray, dtype: str) -> str:
    return base64.b64encode(np.ascontiguousarray(arr, dtype=dtype).tobytes()).decode()


def encode_fire(result, bed, extra_meta: dict | None = None) -> dict:
    """
    Pack a solved fire into ``{meta, dem_b64, arrival_b64, flame_b64}``.

    Arrival time carries the whole animation in one array: the client renders
    the burn at minute *t* by thresholding it, so there are no frames to step
    between and no interpolation artefacts at frame boundaries. Unburned cells
    are stored as the uint16 sentinel rather than as a separate mask, which
    costs nothing and cannot drift out of sync with the data it describes.
    """
    arrival = result.arrival_min
    burned = np.isfinite(arrival)
    quantised = np.full(arrival.shape, _ARRIVAL_UNBURNED, dtype=np.uint16)
    quantised[burned] = np.clip(
        np.rint(arrival[burned]), 0, _ARRIVAL_UNBURNED - 1
    ).astype(np.uint16)

    flame = np.clip(
        np.rint(result.flame_length_m * FLAME_SCALE), 0, 65535
    ).astype(np.uint16)

    ny, nx = arrival.shape
    meta = {
        "ny": ny,
        "nx": nx,
        "dx": float(result.dx),
        "duration_min": float(result.duration_min),
        "arrival_unburned": _ARRIVAL_UNBURNED,
        "arrival_units": "minutes, uint16",
        "flame_scale": FLAME_SCALE,
        "flame_units": "decimetres, uint16",
        "dem_units": "metres, float32",
        "flame_max_m": float(result.flame_length_m.max()),
        "burned_cells": int(burned.sum()),
        "fuel_model": bed.fuel.id,
        "fuel_name": bed.fuel.name,
        "mode": "simulated",
    }
    if extra_meta:
        meta.update(extra_meta)

    return {
        "meta": meta,
        "arrival_b64": _b64(quantised, "<u2"),
        "flame_b64": _b64(flame, "<u2"),
    }


def decode_fire(payload: dict) -> tuple:
    """Inverse of `encode_fire` — ``(arrival_min, flame_m)``, unburned as inf."""
    meta = payload["meta"]
    ny, nx = meta["ny"], meta["nx"]
    arrival = np.frombuffer(
        base64.b64decode(payload["arrival_b64"]), dtype="<u2"
    ).reshape(ny, nx).astype(np.float64)
    arrival[arrival >= meta["arrival_unburned"]] = np.inf
    flame = np.frombuffer(
        base64.b64decode(payload["flame_b64"]), dtype="<u2"
    ).reshape(ny, nx) / meta["flame_scale"]
    return arrival, flame


def _fetch_dem(bbox, scale_m):
    """Default DEM provider. Imported here so Earth Engine stays optional."""
    from gee.raster_fetch import fetch_dem

    return fetch_dem(bbox, scale_m=scale_m)


def simulate_fire(
    bbox: list,
    start_date: str,
    end_date: str,
    params: dict | None = None,
    dem_provider=None,
) -> dict:
    """
    Run a wildfire simulation over an AOI and return a Kairos analysis result.

    `start_date` labels the simulated event; it selects no imagery, because
    nothing here is observed. The signature matches every other registry
    function so the shared runner needs no special case.
    """
    p = resolve_params(params)
    scene = p.pop("scene", None)

    provider = dem_provider or _fetch_dem
    tile = provider(list(bbox), p["scale_m"])

    cells = int(np.prod(tile.dem.shape))
    if cells > MAX_CELLS:
        raise ValueError(
            f"This AOI is {tile.dem.shape[0]}x{tile.dem.shape[1]} = {cells:,} "
            f"cells at {p['scale_m']} m, above the {MAX_CELLS:,} cell limit. "
            f"Draw a smaller box or raise scale_m."
        )

    bed = prepare(FUEL_MODELS[p["fuel_model"]], {
        "dead_1h": p["moisture_1h"],
        "dead_10h": p["moisture_10h"],
        "dead_100h": p["moisture_100h"],
        "live": p["moisture_live"],
    })
    if not bed.burnable or bed.r0_m_min <= 0:
        raise ValueError(
            f"Fuel model {p['fuel_model']} will not carry a fire at this "
            f"moisture — the dead fuel is at or above its moisture of "
            f"extinction ({bed.fuel.mx_dead:.0%}). Lower the moisture or "
            f"choose a drier fuel model."
        )

    ignition_point = (params or {}).get("ignition_point")
    if ignition_point is None and scene is not None:
        ignition_point = list(scene.ignition_point)
    mask, ignition_note = ignition_mask_for(
        tile.dem, ignition_point=ignition_point, bbox=list(bbox)
    )

    duration_min = p["duration_hours"] * 60.0
    result = spread(
        bed,
        tile.dem,
        tile.dx,
        mask,
        wind_ms=p["wind_ms"],
        wind_from_bearing=p["wind_from_bearing"],
        duration_min=duration_min,
        neighbours=p["neighbours"],
    )

    burned = result.burned
    if burned.sum() <= 1:
        raise ValueError(
            "The fire did not spread beyond its ignition cell. The fuel is "
            "too wet, the duration too short, or the AOI too coarse for the "
            "spread rate."
        )

    cell_ha = tile.dx * tile.dx / 1e4
    area_ha = float(burned.sum()) * cell_ha
    # Growth curve: burned area at evenly spaced instants. This is what the
    # scrubber plots, and what makes a wind-driven run legible as a rate
    # rather than as a final outline.
    checkpoints = np.linspace(0.0, duration_min, 25)
    growth = [
        [float(t), round(float(result.burned_at(t).sum()) * cell_ha, 2)]
        for t in checkpoints
    ]

    flame = result.flame_length_m[burned]
    intensity = result.intensity_kw_m[burned]
    ros = result.ros_m_min[burned]

    payload = encode_fire(result, bed, extra_meta={
        "scene_id": scene.id if scene else None,
        "scene_name": scene.name if scene else None,
        "disclosure": DISCLOSURE,
        "bbox": list(bbox),
        "event_date": start_date,
        "dem_min": float(tile.dem.min()),
        "dem_max": float(tile.dem.max()),
        "wind_ms": p["wind_ms"],
        "wind_from_bearing": p["wind_from_bearing"],
    })
    payload["dem_b64"] = _b64(tile.dem, "<f4")

    # Byram's flame length is the number fire agencies use to decide whether a
    # fire can be fought directly, so the thresholds are reported rather than
    # left for the reader to look up.
    p90_flame = float(np.percentile(flame, 90))
    if p90_flame < 1.2:
        containment = "Direct attack by hand crews is generally feasible."
    elif p90_flame < 2.4:
        containment = "Too intense for hand tools; equipment or aircraft needed."
    elif p90_flame < 3.4:
        containment = "Direct attack is likely to fail; expect torching."
    else:
        containment = (
            "Crowning and major runs likely. Control efforts at the head are "
            "generally ineffective."
        )

    stats = {
        "mode": "simulated",
        "disclosure": DISCLOSURE,
        "scene_id": scene.id if scene else None,
        "scene_name": scene.name if scene else None,
        "fuel_model": bed.fuel.id,
        "fuel_name": bed.fuel.name,
        "fuel_description": bed.fuel.description,
        "ignition_placement": ignition_note,
        "wind_ms": p["wind_ms"],
        "wind_from_bearing": p["wind_from_bearing"],
        "duration_hours": p["duration_hours"],
        "moisture": {k: p[k] for k in _MOISTURES},
        "burned_area_ha": round(area_ha, 2),
        "burned_area_km2": round(area_ha / 100.0, 4),
        "perimeter_growth_ha": growth,
        "head_ros_m_min_max": round(float(ros.max()), 2),
        "head_ros_m_min_median": round(float(np.median(ros)), 2),
        "flame_length_m_max": round(float(flame.max()), 2),
        "flame_length_m_p90": round(p90_flame, 2),
        "fireline_intensity_kw_m_max": round(float(intensity.max()), 1),
        "containment_note": containment,
        "no_wind_no_slope_ros_m_min": round(bed.r0_m_min, 3),
        "reaction_intensity_btu_ft2_min": round(bed.reaction_intensity, 1),
        "neighbours": p["neighbours"],
        "angular_error_note": (
            f"Spread is resolved along {p['neighbours']} bearings; travel "
            f"time on a discrete graph can only overestimate, by at most "
            f"{ {8: '8.2', 16: '2.8', 32: '1.3'}[p['neighbours']] }% "
            f"measured against an analytic circle."
        ),
        "confidence_meaning": (
            "Numerical integrity of the solve — NOT forecast skill or "
            "agreement with any observed fire."
        ),
        "payload_bytes": (
            len(payload["arrival_b64"]) + len(payload["flame_b64"])
            + len(payload["dem_b64"])
        ),
        "method": (
            "Rothermel (1972) surface spread on Anderson (1982) fuel models "
            "with Albini (1976) dynamic live moisture of extinction, "
            "propagated by Finney (2002) minimum travel time with Richards "
            "(1990) elliptical templates."
        ),
        "limitations": (
            "Surface fire only. No crown fire, no spotting, no fire-atmosphere "
            "coupling, no suppression, no fuel moisture dynamics. Fuel is "
            "uniform across the domain and wind is steady in space and time."
        ),
        **tile.as_dict(),
    }

    return {
        "tile_url": "",   # nothing server-rendered: the client draws the burn
        "result_image": None,
        "data_date": start_date,
        "confidence": 0.9,
        "mode": "simulated",
        "simulation": payload,
        "headline_stat": {
            "label": "Simulated area burned",
            "value": round(area_ha, 1),
            "unit": "ha",
        },
        # Spread, not nested: `run_analysis` promotes a fixed set of keys and
        # files everything else under `stats` itself, so a literal "stats" key
        # here would arrive at the client one level too deep.
        **stats,
    }
