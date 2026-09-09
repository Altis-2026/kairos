"""
Pack a solved flood into one JSON-safe payload the browser can animate.

Two arrays travel: the terrain (float32 metres) and the depth frames (uint16
centimetres). Centimetres are plenty — the solver's own error bars are far
wider than a centimetre — and halve the payload against float32 while keeping
a 655 m ceiling no flood will reach.

Transport resolution vs solve resolution
---------------------------------------
Frames ship at the solver's native grid by default. Decimation exists for
grids too large to send, but it is deliberately OFF unless asked for, because
area-averaging flattens exactly what a flood viewer is for: on a confined
channel, halving the grid dropped a measured peak from 8.8 m to 4.8 m. That
made the headline depth statistic and the animation a user actually looks at
disagree by nearly a factor of two — a quiet credibility problem, not a
rounding difference.

When decimation IS requested, square blocks are area-averaged (unbiased in
volume, unlike a block maximum, which would inflate every depth read off the
map) and the DEM is decimated identically, so terrain and water stay on one
shared grid the 3D viewer can build a single mesh from. In that case `dx` is
the transport cell size, and both `depth_max` (what is rendered) and
`depth_max_solve` (what the solver computed) are reported, so the two numbers
can never silently drift apart again.
"""

import base64

import numpy as np

#: Depth is stored as centimetres in a uint16.
DEPTH_SCALE = 100.0
_DEPTH_MAX_CM = 65535

#: Default: no decimation. Frames ship at the solver's own resolution so the
#: rendered animation matches the reported statistics exactly. gzip carries
#: the cost — a real scene measured 2.2 MB raw and 0.17 MB over the wire,
#: because most of a flood grid is dry and compresses away.
DEFAULT_MAX_TRANSPORT_DIM = None

#: Hard ceiling regardless of what a caller asks for: past this, a payload
#: stops being something a browser should be asked to hold in memory.
MAX_TRANSPORT_DIM = 1024


def transport_factor(shape: tuple, max_dim=DEFAULT_MAX_TRANSPORT_DIM) -> int:
    """
    Integer decimation factor that brings the longest edge under `max_dim`.

    `None` means ship at native resolution, subject only to MAX_TRANSPORT_DIM.
    """
    ceiling = MAX_TRANSPORT_DIM if max_dim is None else min(int(max_dim), MAX_TRANSPORT_DIM)
    if ceiling < 8:
        raise ValueError(f"max_dim must be at least 8; got {max_dim}.")
    longest = max(shape)
    factor = 1
    while longest // factor > ceiling:
        factor += 1
    return factor


def block_mean(arr: np.ndarray, factor: int) -> np.ndarray:
    """
    Area-average `arr` over factor x factor blocks.

    Trailing rows/columns that do not fill a whole block are dropped rather
    than partially averaged, so every output cell covers exactly the same
    ground area — a partial edge block would be a cell whose value means
    something different from its neighbours'.
    """
    if factor <= 1:
        return arr
    ny, nx = arr.shape
    ny_t, nx_t = (ny // factor) * factor, (nx // factor) * factor
    if ny_t < factor or nx_t < factor:
        return arr
    trimmed = arr[:ny_t, :nx_t]
    return trimmed.reshape(ny_t // factor, factor, nx_t // factor, factor).mean(
        axis=(1, 3)
    )


def _b64(arr: np.ndarray, dtype: str) -> str:
    """Little-endian raw bytes, base64'd. Explicit endianness: the browser
    reads these with typed arrays, which are always host order (LE in
    practice), so the producer must not depend on the server's."""
    return base64.b64encode(np.ascontiguousarray(arr, dtype=dtype).tobytes()).decode()


def quantize_depth(depth: np.ndarray) -> np.ndarray:
    """Depth in metres -> centimetres as uint16, clamped at the type's ceiling."""
    cm = np.rint(np.asarray(depth) * DEPTH_SCALE)
    return np.clip(cm, 0, _DEPTH_MAX_CM).astype("<u2")


def encode_simulation(
    result,
    max_transport_dim=DEFAULT_MAX_TRANSPORT_DIM,
    extra_meta: dict | None = None,
) -> dict:
    """
    Turn a `SolveResult` into ``{meta, dem_b64, depth_b64}``.

    `depth_b64` is all frames concatenated in order, C-contiguous, so the
    client slices frame *k* at ``k * ny * nx``.
    """
    if not result.depths:
        raise ValueError(
            "The solve produced no frames — nothing to encode. "
            f"{result.truncation_reason or 'Unknown cause.'}"
        )

    factor = transport_factor(result.dem.shape, max_transport_dim)
    dem_t = block_mean(result.dem, factor)
    frames = [block_mean(d, factor) for d in result.depths]
    ny, nx = dem_t.shape

    stacked = np.stack([quantize_depth(f) for f in frames])
    peak_cm = int(stacked.max()) if stacked.size else 0
    # What the solver computed, before any decimation. Identical to depth_max
    # at native resolution; reported always so the two can never drift apart
    # unnoticed when decimation IS in play.
    peak_solve = float(max((float(d.max()) for d in result.depths), default=0.0))

    meta = {
        "ny": ny,
        "nx": nx,
        "dx": float(result.dx * factor),
        "times": [float(t) for t in result.times],
        "n_frames": len(frames),
        "dem_min": float(dem_t.min()),
        "dem_max": float(dem_t.max()),
        "depth_max": peak_cm / DEPTH_SCALE,
        "depth_max_solve": peak_solve,
        "decimated": factor > 1,
        "depth_units": "centimetres, uint16",
        "dem_units": "metres, float32",
        "solve_dx": float(result.dx),
        "solve_shape": list(result.dem.shape),
        "transport_factor": factor,
        "mode": "simulated",
    }
    meta.update({k: v for k, v in result.as_meta().items() if k not in meta})
    if extra_meta:
        meta.update(extra_meta)

    return {
        "meta": meta,
        "dem_b64": _b64(dem_t, "<f4"),
        "depth_b64": _b64(stacked, "<u2"),
    }


def decode_simulation(payload: dict) -> tuple:
    """
    Inverse of `encode_simulation` — ``(dem, depths)`` in metres.

    Used by the tests and by any Python consumer of a stored payload; the
    browser does the same three lines in JavaScript.
    """
    meta = payload["meta"]
    ny, nx, n = meta["ny"], meta["nx"], meta["n_frames"]
    dem = np.frombuffer(base64.b64decode(payload["dem_b64"]), dtype="<f4").reshape(ny, nx)
    depth = np.frombuffer(base64.b64decode(payload["depth_b64"]), dtype="<u2")
    return dem.astype(np.float64), depth.reshape(n, ny, nx) / DEPTH_SCALE


def payload_bytes(payload: dict) -> int:
    """Size of the two encoded arrays, for the size guard and for reporting."""
    return len(payload["dem_b64"]) + len(payload["depth_b64"])
