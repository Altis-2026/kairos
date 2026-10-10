import numpy as np

SECONDS_PER_HOUR = 3600.0

_trapezoid = getattr(np, "trapezoid", None) or np.trapz


def validate_hydrograph(hydrograph) -> tuple:
    pairs = list(hydrograph)
    if not pairs:
        raise ValueError(
            "Hydrograph is empty. Provide at least one (t_seconds, m3_per_s) "
            "pair, or pass an all-False inflow mask for an unforced run."
        )
    arr = np.asarray(pairs, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(
            "Hydrograph must be a sequence of (t_seconds, m3_per_s) pairs; "
            f"got an array of shape {arr.shape}."
        )
    times, values = arr[:, 0], arr[:, 1]
    if not np.isfinite(arr).all():
        raise ValueError("Hydrograph contains NaN or infinite values.")
    if np.any(np.diff(times) <= 0):
        raise ValueError("Hydrograph times must be strictly increasing.")
    if np.any(values < 0):
        raise ValueError(
            "Hydrograph discharge must be non-negative. Water leaves the "
            "domain through open boundaries, not through negative inflow."
        )
    return times, values


def sample_hydrograph(times: np.ndarray, values: np.ndarray, t: float) -> float:
    return float(np.interp(t, times, values))


def integrate_hydrograph(times: np.ndarray, values: np.ndarray, t0: float, t1: float) -> float:
    if t1 <= t0:
        return 0.0
    interior = times[(times > t0) & (times < t1)]
    knots = np.concatenate(([t0], interior, [t1]))
    q = np.interp(knots, times, values)
    return float(_trapezoid(q, knots))


def rainfall_rate(mm_per_hour: float) -> float:
    if mm_per_hour < 0:
        raise ValueError("Rainfall intensity must be non-negative.")
    return mm_per_hour / 1000.0 / SECONDS_PER_HOUR


def validate_inflow_mask(inflow_mask, shape) -> np.ndarray:
    if inflow_mask is None:
        return np.zeros(shape, dtype=bool)
    mask = np.asarray(inflow_mask, dtype=bool)
    if mask.shape != shape:
        raise ValueError(f"inflow_mask shape {mask.shape} does not match DEM shape {shape}.")
    return mask


def lowest_cells_mask(dem: np.ndarray, row: int, col: int, n_cells: int = 9, radius: int = 3) -> np.ndarray:
    ny, nx = dem.shape
    if not (0 <= row < ny and 0 <= col < nx):
        raise ValueError(f"Inflow point ({row}, {col}) lies outside the {ny}x{nx} domain.")
    if n_cells < 1:
        raise ValueError("n_cells must be at least 1.")

    r0, r1 = max(0, row - radius), min(ny, row + radius + 1)
    c0, c1 = max(0, col - radius), min(nx, col + radius + 1)
    window = dem[r0:r1, c0:c1]

    k = min(n_cells, window.size)
    flat_idx = np.argsort(window, axis=None, kind="stable")[:k]
    rr, cc = np.unravel_index(flat_idx, window.shape)

    mask = np.zeros(dem.shape, dtype=bool)
    mask[rr + r0, cc + c0] = True
    return mask
