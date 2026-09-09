"""
Pack a solved flood into one JSON-safe payload the browser can animate.

Two arrays travel: the terrain (float32 metres) and the depth frames (uint16
centimetres). Centimetres are plenty — the solver's own error bars are far
wider than a centimetre — and halve the payload against float32 while keeping
a 655 m ceiling no flood will reach.

Transport resolution is decoupled from solve resolution
-------------------------------------------------------
The solver runs at the DEM's native grid. Shipping that grid is a different
question: 400x400 x 48 frames is 15 MB before base64. So frames are decimated
to a viewer-appropriate grid on the way out, by area-averaging square blocks —
unbiased in volume, unlike taking the block maximum, which would inflate every
depth reading the user takes off the map.

The DEM is decimated by the same factor in the same way, so terrain and water
stay on a shared grid and the 3D viewer can build one mesh for both. The
returned `dx` is the transport cell size, not the solve cell size; both are
reported so nobody has to guess which one a measurement refers to.
"""

import base64

import numpy as np

#: Depth is stored as centimetres in a uint16.
DEPTH_SCALE = 100.0
_DEPTH_MAX_CM = 65535

#: Default longest-edge of the transport grid. 256 x 256 x 48 frames is about
#: 6 MB raw, which compresses to roughly a megabyte over the wire.
DEFAULT_MAX_TRANSPORT_DIM = 256


def transport_factor(shape: tuple, max_dim: int = DEFAULT_MAX_TRANSPORT_DIM) -> int:
    """Integer decimation factor that brings the longest edge under `max_dim`."""
    if max_dim < 8:
        raise ValueError(f"max_dim must be at least 8; got {max_dim}.")
    longest = max(shape)
    factor = 1
    while longest // factor > max_dim:
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
    max_transport_dim: int = DEFAULT_MAX_TRANSPORT_DIM,
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

    meta = {
        "ny": ny,
        "nx": nx,
        "dx": float(result.dx * factor),
        "times": [float(t) for t in result.times],
        "n_frames": len(frames),
        "dem_min": float(dem_t.min()),
        "dem_max": float(dem_t.max()),
        "depth_max": peak_cm / DEPTH_SCALE,
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
