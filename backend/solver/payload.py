import base64

import numpy as np

DEPTH_SCALE = 100.0
_DEPTH_MAX_CM = 65535

DEFAULT_MAX_TRANSPORT_DIM = None

MAX_TRANSPORT_DIM = 1024


def transport_factor(shape: tuple, max_dim=DEFAULT_MAX_TRANSPORT_DIM) -> int:
    ceiling = MAX_TRANSPORT_DIM if max_dim is None else min(int(max_dim), MAX_TRANSPORT_DIM)
    if ceiling < 8:
        raise ValueError(f"max_dim must be at least 8; got {max_dim}.")
    longest = max(shape)
    factor = 1
    while longest // factor > ceiling:
        factor += 1
    return factor


def block_mean(arr: np.ndarray, factor: int) -> np.ndarray:
    if factor <= 1:
        return arr
    ny, nx = arr.shape
    ny_t, nx_t = (ny // factor) * factor, (nx // factor) * factor
    if ny_t < factor or nx_t < factor:
        return arr
    trimmed = arr[:ny_t, :nx_t]
    return trimmed.reshape(ny_t // factor, factor, nx_t // factor, factor).mean(axis=(1, 3))


def _b64(arr: np.ndarray, dtype: str) -> str:
    return base64.b64encode(np.ascontiguousarray(arr, dtype=dtype).tobytes()).decode()


def quantize_depth(depth: np.ndarray) -> np.ndarray:
    cm = np.rint(np.asarray(depth) * DEPTH_SCALE)
    return np.clip(cm, 0, _DEPTH_MAX_CM).astype("<u2")


def encode_simulation(
    result,
    max_transport_dim=DEFAULT_MAX_TRANSPORT_DIM,
    extra_meta: dict | None = None,
) -> dict:
    if not result.depths:
        raise ValueError(
            f"The solve produced no frames. Nothing to encode. {result.truncation_reason or 'Unknown cause.'}"
        )

    factor = transport_factor(result.dem.shape, max_transport_dim)
    dem_t = block_mean(result.dem, factor)
    frames = [block_mean(d, factor) for d in result.depths]
    ny, nx = dem_t.shape

    stacked = np.stack([quantize_depth(f) for f in frames])
    peak_cm = int(stacked.max()) if stacked.size else 0
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
    meta = payload["meta"]
    ny, nx, n = meta["ny"], meta["nx"], meta["n_frames"]
    dem = np.frombuffer(base64.b64decode(payload["dem_b64"]), dtype="<f4").reshape(ny, nx)
    depth = np.frombuffer(base64.b64decode(payload["depth_b64"]), dtype="<u2")
    return dem.astype(np.float64), depth.reshape(n, ny, nx) / DEPTH_SCALE


def payload_bytes(payload: dict) -> int:
    return len(payload["dem_b64"]) + len(payload["depth_b64"])
