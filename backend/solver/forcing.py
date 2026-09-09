"""
Forcing terms for the hydraulic solver: inflow hydrographs, rainfall, losses.

Two kinds of water can enter the domain (paper §2.3):

  * **Pluvial** — rain falling on the grid. Because gravity is evaluated from
    the free-surface gradient, uniform rain channelises into topographic lows
    on its own, with no prescribed drainage network.
  * **Fluvial** — a river draining a catchment that lies *outside* the DEM
    contributes nothing to a rain-on-grid model, so its discharge is injected
    directly at the point where it enters the domain.

The hydrograph is piecewise linear in ``(t_seconds, m³/s)`` pairs and is
integrated **exactly** over each time step rather than sampled at the step's
start. With adaptive steps that land on hydrograph breakpoints only by
accident, sampling would quietly change the total injected volume as a
function of the Courant number — the same event would deliver different
amounts of water at different time-step settings.
"""

import numpy as np

SECONDS_PER_HOUR = 3600.0

# np.trapz was renamed to np.trapezoid in NumPy 2.0; support both.
_trapezoid = getattr(np, "trapezoid", None) or np.trapz


def validate_hydrograph(hydrograph) -> tuple:
    """
    Normalise and check a piecewise-linear hydrograph.

    Returns ``(times, values)`` as float arrays.
    """
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
    """
    Discharge (m³/s) at time `t`, linearly interpolated.

    Outside the hydrograph's span the first/last value is held constant, so a
    run may extend past the last breakpoint (that is how the recession limb
    gets any time to happen).
    """
    return float(np.interp(t, times, values))


def integrate_hydrograph(
    times: np.ndarray, values: np.ndarray, t0: float, t1: float
) -> float:
    """
    Exact volume (m³) delivered between `t0` and `t1`.

    The integrand is piecewise linear, so the trapezoid rule is exact provided
    every breakpoint inside the interval is used as a sub-interval endpoint.
    """
    if t1 <= t0:
        return 0.0
    interior = times[(times > t0) & (times < t1)]
    knots = np.concatenate(([t0], interior, [t1]))
    q = np.interp(knots, times, values)
    return float(_trapezoid(q, knots))


def rainfall_rate(mm_per_hour: float) -> float:
    """Convert a rainfall intensity in mm/hr to a source rate in m/s."""
    if mm_per_hour < 0:
        raise ValueError("Rainfall intensity must be non-negative.")
    return mm_per_hour / 1000.0 / SECONDS_PER_HOUR


def validate_inflow_mask(inflow_mask, shape) -> np.ndarray:
    """Coerce the inflow mask to a boolean array matching the DEM."""
    if inflow_mask is None:
        return np.zeros(shape, dtype=bool)
    mask = np.asarray(inflow_mask, dtype=bool)
    if mask.shape != shape:
        raise ValueError(
            f"inflow_mask shape {mask.shape} does not match DEM shape {shape}."
        )
    return mask


def lowest_cells_mask(
    dem: np.ndarray, row: int, col: int, n_cells: int = 9, radius: int = 3
) -> np.ndarray:
    """
    An inflow mask covering the `n_cells` lowest-lying cells near (row, col).

    A river's discharge is injected into channel cells, not onto whatever
    pixel the user happened to click: dropping hundreds of m³/s onto a single
    30 m cell would add metres of depth per step and force the CFL condition
    to collapse. Spreading the flux over the local topographic low both places
    the water in the channel and keeps the per-cell fill rate sane.
    """
    ny, nx = dem.shape
    if not (0 <= row < ny and 0 <= col < nx):
        raise ValueError(
            f"Inflow point ({row}, {col}) lies outside the {ny}x{nx} domain."
        )
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
