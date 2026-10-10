import time
from dataclasses import dataclass

import numpy as np

from solver import forcing, grid
from solver.diagnostics import VolumeLedger

G = 9.80665

DEPTH_TOL = 1e-4

CFL_DEPTH_FLOOR = 1e-3

LIMITER_SAFETY = 1.0 - 1e-9

DEFAULT_MAX_STEPS = 500_000

MIN_DT = 1e-9


@dataclass
class SolveResult:
    times: list
    depths: list
    dem: np.ndarray
    dx: float
    open_edges: tuple
    steps: int
    ledger: VolumeLedger
    truncated: bool = False
    truncation_reason: str | None = None
    limited_steps: int = 0
    min_alpha: float = 1.0
    dt_min: float = 0.0
    dt_max_used: float = 0.0
    dt_mean: float = 0.0
    pits_filled: bool = False

    @property
    def frames(self) -> list:
        return list(zip(self.times, self.depths))

    @property
    def max_depth(self) -> float:
        return float(max((d.max() for d in self.depths), default=0.0))

    def as_meta(self) -> dict:
        ny, nx = self.dem.shape
        return {
            "ny": ny,
            "nx": nx,
            "dx": self.dx,
            "times": [float(t) for t in self.times],
            "dem_min": float(self.dem.min()),
            "dem_max": float(self.dem.max()),
            "depth_max": self.max_depth,
            "steps": self.steps,
            "open_edges": list(self.open_edges),
            "truncated": self.truncated,
            "truncation_reason": self.truncation_reason,
            "limiter_activations": self.limited_steps,
            "limiter_min_alpha": self.min_alpha,
            "dt_min_s": self.dt_min,
            "dt_max_s": self.dt_max_used,
            "dt_mean_s": self.dt_mean,
            "pits_filled": self.pits_filled,
            "mode": "simulated",
            "volume": self.ledger.as_dict(),
        }


def _face_manning_sq(n_manning, shape: tuple) -> tuple:
    if np.isscalar(n_manning):
        if n_manning <= 0:
            raise ValueError(f"Manning n must be positive; got {n_manning}.")
        n2 = float(n_manning) ** 2
        return n2, n2

    n = np.asarray(n_manning, dtype=np.float64)
    if n.shape != shape:
        raise ValueError(f"n_manning field shape {n.shape} does not match DEM shape {shape}.")
    if not np.isfinite(n).all() or np.any(n <= 0):
        raise ValueError("n_manning field must be finite and strictly positive.")
    n2x = (0.5 * (n[:, :-1] + n[:, 1:])) ** 2
    n2y = (0.5 * (n[:-1, :] + n[1:, :])) ** 2
    return n2x, n2y


def _critical_outflow(h_edge: np.ndarray) -> np.ndarray:
    wet = h_edge > DEPTH_TOL
    hh = np.where(wet, h_edge, 0.0)
    return np.where(wet, hh * np.sqrt(G * hh), 0.0)


def solve(
    dem,
    dx: float,
    *,
    inflow_mask=None,
    hydrograph=(),
    initial_depth=None,
    n_manning=0.05,
    dt_max: float = 5.0,
    n_frames: int = 48,
    courant: float = 0.4,
    open_edges=("south",),
    duration_s: float | None = None,
    rain_mm_per_hour: float = 0.0,
    infiltration_mm_per_hour: float = 0.0,
    fill_dem_pits: bool = False,
    max_steps: int = DEFAULT_MAX_STEPS,
    max_seconds: float | None = None,
    max_inflow_rise_m: float = 0.25,
) -> SolveResult:
    z = np.array(dem, dtype=np.float64, copy=True)
    grid.check_uniform_grid(z, dx)

    pits_filled = False
    if fill_dem_pits:
        z = grid.fill_pits(z)
        pits_filled = True

    ny, nx = z.shape
    cell_area = dx * dx

    if n_frames < 1:
        raise ValueError(f"n_frames must be at least 1; got {n_frames}.")
    if not (0 < courant <= 1.0):
        raise ValueError(f"courant must lie in (0, 1]; got {courant}.")
    if dt_max <= 0:
        raise ValueError(f"dt_max must be positive; got {dt_max}.")

    edges = grid.resolve_open_edges(z, open_edges)
    open_n, open_s = "north" in edges, "south" in edges
    open_w, open_e = "west" in edges, "east" in edges

    mask = forcing.validate_inflow_mask(inflow_mask, z.shape)
    n_inflow = int(mask.sum())

    pairs = list(hydrograph)
    if pairs:
        h_times, h_values = forcing.validate_hydrograph(pairs)
        if n_inflow == 0 and np.any(h_values > 0):
            raise ValueError(
                "A hydrograph with non-zero discharge was given but the inflow "
                "mask selects no cells. The water has nowhere to enter."
            )
    else:
        h_times = h_values = None

    if duration_s is None:
        if h_times is None:
            raise ValueError(
                "duration_s must be given when there is no hydrograph to take the run length from."
            )
        duration_s = float(h_times[-1])
    if duration_s <= 0:
        raise ValueError(f"duration_s must be positive; got {duration_s}.")

    if initial_depth is None:
        h = np.zeros((ny, nx), dtype=np.float64)
    else:
        h = np.array(initial_depth, dtype=np.float64, copy=True)
        if h.shape != z.shape:
            raise ValueError(f"initial_depth shape {h.shape} does not match DEM shape {z.shape}.")
        if not np.isfinite(h).all() or np.any(h < 0):
            raise ValueError("initial_depth must be finite and non-negative.")

    n2x, n2y = _face_manning_sq(n_manning, z.shape)
    rain_rate = forcing.rainfall_rate(rain_mm_per_hour)
    infil_rate = forcing.rainfall_rate(infiltration_mm_per_hour)

    qx = np.zeros((ny, nx - 1), dtype=np.float64)
    qy = np.zeros((ny - 1, nx), dtype=np.float64)

    ledger = VolumeLedger()
    ledger.initial = float(h.sum()) * cell_area
    ledger.observe(ledger.initial)

    frame_times = np.linspace(0.0, duration_s, n_frames) if n_frames > 1 else np.array([duration_s])

    times: list = []
    depths: list = []
    next_frame = 0
    if frame_times[0] == 0.0:
        times.append(0.0)
        depths.append(h.copy())
        next_frame = 1

    t = 0.0
    steps = 0
    limited_steps = 0
    min_alpha = 1.0
    dt_sum = 0.0
    dt_lo = float("inf")
    dt_hi = 0.0
    truncated = False
    reason: str | None = None

    started = time.monotonic()

    while next_frame < len(frame_times):
        if max_seconds is not None and (time.monotonic() - started) > max_seconds:
            truncated = True
            reason = (
                f"Wall-clock budget of {max_seconds:.0f}s exhausted at "
                f"t={t:.1f}s of {duration_s:.1f}s after {steps} steps. Coarsen "
                f"the grid or shorten the event."
            )
            break
        if steps >= max_steps:
            truncated = True
            reason = (
                f"Step budget exhausted after {max_steps} steps at t={t:.1f}s of "
                f"{duration_s:.1f}s. Coarsen the grid, raise dt_max, or shorten "
                f"the event."
            )
            break

        target = float(frame_times[next_frame])

        h_max = float(h.max())
        dt = min(
            dt_max,
            courant * dx / np.sqrt(G * max(h_max, CFL_DEPTH_FLOOR)),
        )
        if h_values is not None and n_inflow:
            q_now = forcing.sample_hydrograph(h_times, h_values, t)
            if q_now > 0.0:
                rise_rate = q_now / (n_inflow * cell_area)
                dt = min(dt, max_inflow_rise_m / rise_rate)
        dt = min(dt, target - t)

        if dt <= MIN_DT:
            truncated = True
            reason = f"Time step collapsed to {dt:.3e}s at t={t:.1f}s."
            break

        wse = z + h
        bed_x = np.maximum(z[:, :-1], z[:, 1:])
        hf = np.maximum(wse[:, :-1], wse[:, 1:]) - bed_x
        wet = hf > DEPTH_TOL
        hf_s = np.where(wet, hf, 1.0)
        q_star = qx - G * hf_s * dt * (wse[:, 1:] - wse[:, :-1]) / dx
        q_new = q_star / (1.0 + G * dt * n2x * np.abs(qx) / hf_s ** (7.0 / 3.0))
        cap = hf_s * np.sqrt(G * hf_s)
        qx = np.where(wet, np.clip(q_new, -cap, cap), 0.0)

        bed_y = np.maximum(z[:-1, :], z[1:, :])
        hf = np.maximum(wse[:-1, :], wse[1:, :]) - bed_y
        wet = hf > DEPTH_TOL
        hf_s = np.where(wet, hf, 1.0)
        q_star = qy - G * hf_s * dt * (wse[1:, :] - wse[:-1, :]) / dx
        q_new = q_star / (1.0 + G * dt * n2y * np.abs(qy) / hf_s ** (7.0 / 3.0))
        cap = hf_s * np.sqrt(G * hf_s)
        qy = np.where(wet, np.clip(q_new, -cap, cap), 0.0)

        fx = np.zeros((ny, nx + 1), dtype=np.float64)
        fy = np.zeros((ny + 1, nx), dtype=np.float64)
        fx[:, 1:-1] = qx
        fy[1:-1, :] = qy
        if open_w:
            fx[:, 0] = -_critical_outflow(h[:, 0])
        if open_e:
            fx[:, -1] = _critical_outflow(h[:, -1])
        if open_n:
            fy[0, :] = -_critical_outflow(h[0, :])
        if open_s:
            fy[-1, :] = _critical_outflow(h[-1, :])

        dh = -dt * ((fx[:, 1:] - fx[:, :-1]) + (fy[1:, :] - fy[:-1, :])) / dx

        negative = (h + dh) < 0.0
        if negative.any():
            alpha = float(np.min(h[negative] / -dh[negative]))
            alpha = min(max(alpha, 0.0), 1.0) * LIMITER_SAFETY
            dh *= alpha
            qx *= alpha
            qy *= alpha
            fx *= alpha
            fy *= alpha
            limited_steps += 1
            min_alpha = min(min_alpha, alpha)

        h += dh

        out_flux = (
            float(np.sum(-fx[:, 0]))
            + float(np.sum(fx[:, -1]))
            + float(np.sum(-fy[0, :]))
            + float(np.sum(fy[-1, :]))
        )
        ledger.discharged += out_flux * dx * dt

        if h_values is not None and n_inflow:
            volume = forcing.integrate_hydrograph(h_times, h_values, t, t + dt)
            if volume > 0.0:
                h[mask] += volume / (n_inflow * cell_area)
                ledger.injected += volume
        if rain_rate > 0.0:
            h += rain_rate * dt
            ledger.rained += rain_rate * dt * h.size * cell_area

        if infil_rate > 0.0:
            loss = np.minimum(h, infil_rate * dt)
            h -= loss
            ledger.infiltrated += float(loss.sum()) * cell_area

        t += dt
        steps += 1
        dt_sum += dt
        dt_lo = min(dt_lo, dt)
        dt_hi = max(dt_hi, dt)
        ledger.observe(float(h.sum()) * cell_area)

        if t >= target - MIN_DT:
            t = target
            times.append(t)
            depths.append(h.copy())
            next_frame += 1

    return SolveResult(
        times=times,
        depths=depths,
        dem=z,
        dx=dx,
        open_edges=edges,
        steps=steps,
        ledger=ledger,
        truncated=truncated,
        truncation_reason=reason,
        limited_steps=limited_steps,
        min_alpha=min_alpha,
        dt_min=(0.0 if dt_lo == float("inf") else dt_lo),
        dt_max_used=dt_hi,
        dt_mean=(dt_sum / steps if steps else 0.0),
        pits_filled=pits_filled,
    )


def run_event(
    dem: np.ndarray,
    dx: float,
    inflow_mask: np.ndarray,
    hydrograph: list,
    n_manning=0.05,
    dt_max: float = 5.0,
    n_frames: int = 48,
    courant: float = 0.4,
    open_edges=("south",),
    **kwargs,
) -> tuple:
    result = solve(
        dem,
        dx,
        inflow_mask=inflow_mask,
        hydrograph=hydrograph,
        n_manning=n_manning,
        dt_max=dt_max,
        n_frames=n_frames,
        courant=courant,
        open_edges=open_edges,
        **kwargs,
    )
    return result.frames, result.steps
