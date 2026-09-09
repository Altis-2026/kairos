"""
Flood simulation as a Kairos analysis: AOI in, animated depth frames out.

This is the orchestration layer — it owns none of the physics (`hydraulic_route`)
and none of the fetching (`gee.raster_fetch`). Its job is to turn a bounding
box and a handful of user parameters into a solve, and the solve into the same
result envelope every other Kairos analysis returns, so the registry, the job
queue, provenance stamping, and the frontend all handle it without special
cases.

What it is not
--------------
Every result from here is **simulated**. The terrain is real and the physics
are real, but the water is not observed — it comes from a hydrograph a person
chose. That is a categorically different claim from `flood_extent`, which
measures a flood that actually happened, and the two must never be confused by
a user or by the AI layer. The result carries `mode: "simulated"` inside its
provenance hash, a `disclosure` string, and a `confidence` value that is
explicitly labelled as numerical integrity rather than forecast skill.

Testability
-----------
`dem_provider` is injectable, so the whole pipeline — parameter resolution,
inflow placement, solve, encode, result envelope — is exercised offline with
synthetic terrain and no Earth Engine credentials.
"""

import numpy as np

from solver import forcing, presets
from solver.hydraulic_route import solve
from solver.payload import (
    DEFAULT_MAX_TRANSPORT_DIM,
    MAX_TRANSPORT_DIM,
    encode_simulation,
    payload_bytes,
)

#: Depth below which a cell is not called flooded, for area statistics. Also
#: the threshold the 3D viewer uses to push a vertex under the terrain.
WET_THRESHOLD_M = 0.05

#: Wall-clock budget for one solve. The rq queue's own timeout is 600 s; this
#: leaves room for the fetch and the encode either side of it.
DEFAULT_MAX_SECONDS = 420.0

DISCLOSURE = (
    "SIMULATED — this is a forward hydraulic model, not a satellite "
    "observation. Terrain is real (Copernicus GLO-30) and the physics are a "
    "local-inertial shallow-water solver, but the water comes from an assumed "
    "inflow hydrograph. It is not a forecast and it has not been calibrated "
    "against any gauge. For an observed flood, run Flood Extent Mapping."
)

DEFAULTS = {
    "peak_discharge_m3s": 300.0,
    "rise_minutes": 30.0,
    "peak_minutes": 30.0,
    "recession_minutes": 120.0,
    "duration_hours": 6.0,
    "n_manning": 0.05,
    "scale_m": 30.0,
    "dt_max": 5.0,
    "n_frames": 48,
    "courant": 0.4,
    "rain_mm_per_hour": 0.0,
    "infiltration_mm_per_hour": 0.0,
    "open_edges": ["auto"],
    "fill_dem_pits": True,
    "inflow_cells": 12,
    "max_transport_dim": DEFAULT_MAX_TRANSPORT_DIM,   # None = native resolution
    "max_seconds": DEFAULT_MAX_SECONDS,
}

_POSITIVE = (
    "peak_discharge_m3s", "duration_hours", "n_manning", "scale_m", "dt_max",
)
_NON_NEGATIVE = (
    "rise_minutes", "peak_minutes", "recession_minutes", "rain_mm_per_hour",
    "infiltration_mm_per_hour",
)

#: Ceilings a caller may lower but not raise. `max_seconds` bounds how long one
#: request can hold a worker; `max_transport_dim` bounds the response size.
#: Both arrive over a public API, so neither can be a suggestion.
_CEILINGS = {
    "max_seconds": DEFAULT_MAX_SECONDS,
    "max_transport_dim": MAX_TRANSPORT_DIM,
    "inflow_cells": 400,
}


def _as_number(key: str, value):
    """
    Coerce a parameter to float, failing as a user error rather than a crash.

    These values arrive as JSON from the network: a string where a number
    belongs must produce a 400 that names the field, not a TypeError deep in
    the solver that surfaces as a 500.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{key} must be a number; got {value!r}."
        ) from None
    if not np.isfinite(number):
        raise ValueError(f"{key} must be a finite number; got {value!r}.")
    return number


def resolve_params(params: dict | None) -> dict:
    """
    Merge user parameters over the scene preset (if any) over the defaults.

    Precedence is explicit-parameter > scene > default, so a user can pick a
    showcase scene and still override its peak discharge without losing the
    rest of the scene's tuning.
    """
    supplied = dict(params or {})
    scene_id = supplied.pop("scene", None)

    resolved = dict(DEFAULTS)
    scene = None
    if scene_id:
        scene = presets.get_scene(scene_id)
        for key in (
            "peak_discharge_m3s", "rise_minutes", "peak_minutes",
            "recession_minutes", "duration_hours", "n_manning", "scale_m",
            "dt_max", "rain_mm_per_hour",
        ):
            resolved[key] = getattr(scene, key)

    unknown = set(supplied) - set(DEFAULTS) - {"inflow_point"}
    if unknown:
        raise ValueError(
            f"Unknown simulation parameter(s) {sorted(unknown)}. "
            f"Valid: {sorted(set(DEFAULTS) | {'scene', 'inflow_point'})}"
        )
    resolved.update(supplied)

    for key in _POSITIVE:
        resolved[key] = _as_number(key, resolved[key])
        if resolved[key] <= 0:
            raise ValueError(f"{key} must be positive; got {resolved[key]}.")
    for key in _NON_NEGATIVE:
        resolved[key] = _as_number(key, resolved[key])
        if resolved[key] < 0:
            raise ValueError(f"{key} must be non-negative; got {resolved[key]}.")

    try:
        frames = int(resolved["n_frames"])
    except (TypeError, ValueError):
        raise ValueError(
            f"n_frames must be a whole number; got {resolved['n_frames']!r}."
        ) from None
    if not (1 <= frames <= 240):
        raise ValueError(f"n_frames must be between 1 and 240; got {frames}.")
    resolved["n_frames"] = frames

    if resolved["duration_hours"] > 72:
        raise ValueError(
            f"duration_hours is capped at 72; got {resolved['duration_hours']}. "
            f"This is a demonstration solver, not an operational one."
        )

    # Resource ceilings clamp rather than reject: a caller asking for a bigger
    # payload or a longer solve gets the maximum, not an error.
    for key, ceiling in _CEILINGS.items():
        if key == "max_transport_dim" and resolved[key] is None:
            continue    # None is the default and means "ship native resolution"
        resolved[key] = min(_as_number(key, resolved[key]), ceiling)
        if resolved[key] <= 0:
            raise ValueError(f"{key} must be positive; got {resolved[key]}.")
    resolved["scene"] = scene
    return resolved


def build_hydrograph(p: dict) -> list:
    """Piecewise-linear rise / plateau / recession from the shape parameters."""
    rise = p["rise_minutes"] * 60.0
    plateau = rise + p["peak_minutes"] * 60.0
    end = plateau + p["recession_minutes"] * 60.0
    peak = p["peak_discharge_m3s"]
    knots = [(0.0, 0.0), (rise, peak), (plateau, peak), (end, 0.0)]

    # Collapse coincident breakpoints (a zero-length rise or plateau) so the
    # hydrograph stays strictly increasing in time.
    cleaned = [knots[0]]
    for t, q in knots[1:]:
        if t > cleaned[-1][0]:
            cleaned.append((t, q))
        else:
            cleaned[-1] = (cleaned[-1][0], max(cleaned[-1][1], q))
    return cleaned


def upstream_edge(dem: np.ndarray, open_edges: tuple) -> str:
    """
    The edge water should enter through: the highest-lying closed edge.

    Picking it from the terrain rather than asking the user to nominate one
    means a scene needs no hand-placed inflow coordinate — the domain's own
    relief says which side is upstream.
    """
    from solver.grid import EDGES

    candidates = {
        name: float(np.mean(dem[sl]))
        for name, sl in EDGES.items()
        if name not in open_edges
    }
    if not candidates:  # every edge open — fall back to the full set
        candidates = {name: float(np.mean(dem[sl])) for name, sl in EDGES.items()}
    return max(candidates, key=candidates.get)


def inflow_mask_for(
    dem: np.ndarray, open_edges: tuple, n_cells: int, inflow_point=None, bbox=None
) -> tuple:
    """
    Where the hydrograph enters. Returns ``(mask, description)``.

    With no explicit point, the injection sits on the lowest ground along the
    upstream edge — i.e. in the channel where it crosses into the domain. An
    explicit ``[lon, lat]`` is mapped through the bbox and then snapped to the
    local topographic low, so a click that lands on a bank still puts water in
    the channel rather than on a hillside.
    """
    ny, nx = dem.shape
    radius = max(3, int(np.sqrt(n_cells)) + 2)

    if inflow_point is not None:
        if bbox is None:
            raise ValueError("inflow_point requires the AOI bbox to place it.")
        lon, lat = float(inflow_point[0]), float(inflow_point[1])
        min_lon, min_lat, max_lon, max_lat = bbox
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            raise ValueError(
                f"Inflow point ({lon}, {lat}) is outside the AOI {list(bbox)}."
            )
        fx = (lon - min_lon) / (max_lon - min_lon)
        fy = (max_lat - lat) / (max_lat - min_lat)      # row 0 is north
        row = min(max(int(round(fy * (ny - 1))), 0), ny - 1)
        col = min(max(int(round(fx * (nx - 1))), 0), nx - 1)
        mask = forcing.lowest_cells_mask(dem, row, col, n_cells, radius)
        return mask, f"user-placed at ({lon:.4f}, {lat:.4f}), snapped to the local low"

    edge = upstream_edge(dem, open_edges)
    if edge in ("north", "south"):
        row = 0 if edge == "north" else ny - 1
        col = int(np.argmin(dem[row, :]))
    else:
        col = 0 if edge == "west" else nx - 1
        row = int(np.argmin(dem[:, col]))
    mask = forcing.lowest_cells_mask(dem, row, col, n_cells, radius)
    return mask, f"lowest ground on the {edge} (upstream) edge"


def _fetch_dem(bbox, scale_m):
    """Default DEM provider. Imported here so Earth Engine stays optional."""
    from gee.raster_fetch import fetch_dem

    return fetch_dem(bbox, scale_m=scale_m)


def simulate_flood(
    bbox: list,
    start_date: str,
    end_date: str,
    params: dict | None = None,
    dem_provider=None,
) -> dict:
    """
    Run a flood simulation over an AOI and return a Kairos analysis result.

    `start_date` is the date the simulated event is labelled with; it does not
    select imagery, because nothing here is observed. The signature matches
    every other registry function so the shared runner needs no special case.
    """
    p = resolve_params(params)
    scene = p.pop("scene", None)

    provider = dem_provider or _fetch_dem
    tile = provider(list(bbox), p["scale_m"])

    hydrograph = build_hydrograph(p)
    open_edges = tuple(p["open_edges"]) if p["open_edges"] else ()
    mask, inflow_note = inflow_mask_for(
        tile.dem, open_edges, int(p["inflow_cells"]),
        inflow_point=(params or {}).get("inflow_point"), bbox=list(bbox),
    )

    result = solve(
        tile.dem,
        tile.dx,
        inflow_mask=mask,
        hydrograph=hydrograph,
        n_manning=p["n_manning"],
        dt_max=p["dt_max"],
        n_frames=p["n_frames"],
        courant=p["courant"],
        open_edges=open_edges,
        duration_s=p["duration_hours"] * 3600.0,
        rain_mm_per_hour=p["rain_mm_per_hour"],
        infiltration_mm_per_hour=p["infiltration_mm_per_hour"],
        fill_dem_pits=bool(p["fill_dem_pits"]),
        max_seconds=p["max_seconds"],
    )

    if not result.depths:
        raise ValueError(
            "The simulation produced no frames. "
            f"{result.truncation_reason or 'Unknown cause.'}"
        )

    # ---- derived statistics -------------------------------------------------
    cell_area = tile.dx * tile.dx
    wet_per_frame = [int((d > WET_THRESHOLD_M).sum()) for d in result.depths]
    peak_frame = int(np.argmax([float(d.max()) for d in result.depths]))
    peak_depth = float(result.depths[peak_frame].max())
    max_extent_km2 = max(wet_per_frame) * cell_area / 1e6
    # Envelope of everything that was ever wet — the footprint an impact
    # assessment would use, not the extent at any single instant.
    ever_wet = np.zeros(tile.dem.shape, dtype=bool)
    for d in result.depths:
        ever_wet |= d > WET_THRESHOLD_M
    inundated_km2 = float(ever_wet.sum()) * cell_area / 1e6

    mass_error = abs(result.ledger.mass_error)
    clean = (not result.truncated) and mass_error < 1e-9
    confidence = 0.95 if clean else (0.6 if not result.truncated else 0.4)

    payload = encode_simulation(
        result,
        max_transport_dim=(
            None if p["max_transport_dim"] is None else int(p["max_transport_dim"])
        ),
        extra_meta={
            "scene_id": scene.id if scene else None,
            "scene_name": scene.name if scene else None,
            "disclosure": DISCLOSURE,
            "bbox": list(bbox),
            "event_date": start_date,
            "wet_threshold_m": WET_THRESHOLD_M,
        },
    )

    stats = {
        "mode": "simulated",
        "disclosure": DISCLOSURE,
        "scene_id": scene.id if scene else None,
        "scene_name": scene.name if scene else None,
        "hydrograph": [[float(t), float(q)] for t, q in hydrograph],
        "hydrograph_note": (
            scene.disclosure if scene
            else "Synthetic rise/peak/recession hydrograph chosen by the user."
        ),
        "inflow_placement": inflow_note,
        "inflow_cells": int(mask.sum()),
        "peak_depth_m": round(peak_depth, 3),
        "peak_depth_frame": peak_frame,
        "peak_depth_time_s": float(result.times[peak_frame]),
        "max_instantaneous_extent_km2": round(max_extent_km2, 4),
        "total_inundated_km2": round(inundated_km2, 4),
        "injected_volume_m3": round(result.ledger.injected, 1),
        "discharged_volume_m3": round(result.ledger.discharged, 1),
        "retained_volume_m3": round(result.ledger.stored, 1),
        "mass_error": result.ledger.mass_error,
        "solver_steps": result.steps,
        "limiter_activations": result.limited_steps,
        "truncated": result.truncated,
        "truncation_reason": result.truncation_reason,
        "dem_pits_filled": result.pits_filled,
        "dem_conditioning_note": (
            "Depressions in the DEM were filled before solving (priority-flood). "
            "Unfilled sensor artefacts trap water permanently and prevent the "
            "flood from receding; this changes the terrain and is reported here "
            "because of it."
            if result.pits_filled
            else "Raw DEM, unconditioned."
        ),
        "confidence_meaning": (
            "Numerical integrity of the solve — mass closure and completion — "
            "NOT forecast skill or agreement with any observation."
        ),
        "payload_bytes": payload_bytes(payload),
        "method": (
            "Local-inertial shallow-water solver (Bates et al. 2010; de Almeida "
            "et al. 2012) on a staggered grid, adaptive CFL step, Froude-capped "
            "faces, globally scaled flux limiter for exact non-negativity, "
            "critical-flow free-overfall open boundaries."
        ),
        **tile.as_dict(),
    }

    return {
        "tile_url": "",   # nothing server-rendered: the client draws the frames
        "result_image": None,
        "data_date": start_date,
        "confidence": confidence,
        "mode": "simulated",
        "simulation": payload,
        "headline_stat": {
            "label": "Peak simulated depth",
            "value": round(peak_depth, 2),
            "unit": "m",
        },
        **stats,
    }
