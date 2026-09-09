"""
Local-inertial shallow-water solver (Bates et al. 2010; de Almeida et al. 2012).

This is the forward model behind Kairos's *simulated* flood views. It is a
small, pure-NumPy, single-process solver — good enough to produce a physically
believable rise-and-recession animation over real terrain, and deliberately
much less than a research hydraulic code. It has no infiltration model beyond
a constant rate, no urban drainage coupling, and no differentiable
calibration. It is **not** a forecast, and nothing it produces should ever be
presented as an observation: Kairos's SAR analyses measure floods that
happened, this predicts what water would do given terrain and an assumed
inflow.

Numerics
--------
State is staggered: depth ``h`` at cell centres, unit-width discharge ``qx`` /
``qy`` on the faces between cells. Each step is two sweeps.

1. **Flux sweep.** Each face discharge is updated from the momentum equation
   with gravity explicit from the free-surface gradient ∇(z + h) and Manning
   friction semi-implicit — the friction term sits in the denominator, which
   is what keeps the response stable at large time steps. Face flow depth is
   reconstructed as ``max(wse_a, wse_b) - max(z_a, z_b)``, so a face whose
   both sides are dry, or whose water surface sits below the higher bed,
   carries exactly zero flow. That reconstruction is the reason water does not
   leak across a ridge.
2. **Depth sweep.** Each cell's depth changes by the net divergence of its own
   face fluxes. Because the same face value is subtracted from one cell and
   added to its neighbour, water leaving a cell is exactly the water entering
   the next one — the scheme is mass-conservative by construction.

Stability comes from an adaptive CFL step ``dt = C·dx/sqrt(g·h_max)`` capped
at ``dt_max``, plus a per-face critical-flow (Froude ≤ 1) cap.

Three things are load-bearing and easy to get wrong
---------------------------------------------------
**1. The flux limiter.** "Mass-conservative by construction" holds only if no
cell is ever asked to drain more water than it holds. An explicit step on real
terrain will occasionally propose exactly that. Clipping the resulting
negative depth to zero — the obvious fix — *creates water from nothing*, every
time it happens, invisibly unless total volume is checked. Instead, when any
cell would go negative, one global scale factor ``alpha`` is applied to the
entire flux field (face discharges, boundary outflow, and the resulting depth
change alike) so that the worst cell lands exactly at empty. Non-negativity is
then exact and no mass is created or destroyed; the price is a locally more
conservative step. The factor must be *global*: scaling per-cell would break
the shared-face identity that mass conservation rests on.

**2. The open boundary.** A domain walled on all four sides has nowhere to
drain, so water pools forever and the flood never recedes. At least one
transmissive edge is needed for a rise-and-recession animation. Open edges
discharge as a critical-flow free overfall toward an imaginary dry cell just
outside the domain (``q_out = h·sqrt(g·h)``), and that outflow is subject to
the same limiter — a boundary cell cannot drain more than it holds either.

**3. A metric grid.** ``dx`` is a single cell size in metres applied in both
directions. A DEM on a lat/lon grid has x-spacing that shrinks with latitude,
which routes water at a wrong angle everywhere outside the equator, silently.
Reproject to UTM (or equivalent) before calling in. See ``grid.py``.

References
----------
Bates, Horritt & Fewtrell (2010), J. Hydrol. 387(1-2).
de Almeida, Bates, Freer & Souvignet (2012), Water Resour. Res. 48(5).
Li (2026), "Inunda: a GPU-native, differentiable solver for high-resolution
flood inundation modeling", §2.1-2.3.
"""

from dataclasses import dataclass, field

import numpy as np

from solver import forcing, grid
from solver.diagnostics import VolumeLedger

#: Standard gravity (m/s²).
G = 9.80665

#: A face carrying less flow depth than this is treated as dry and passes no
#: water. This zeroes *fluxes* only — never depths. Zeroing a small depth
#: would destroy mass silently, which is the bug this module exists to avoid.
DEPTH_TOL = 1e-4

#: Depth floor used only inside the CFL expression, so a dry domain yields a
#: finite first time step instead of dividing by zero.
CFL_DEPTH_FLOOR = 1e-3

#: Applied to the limiter's scale factor so the constraining cell lands just
#: above empty rather than at a rounding-error-negative depth. Small enough to
#: be hydraulically irrelevant, large enough to dominate float64 rounding.
LIMITER_SAFETY = 1.0 - 1e-9

DEFAULT_MAX_STEPS = 500_000

#: Smallest time step worth taking. Below this the run is going nowhere and is
#: reported as truncated rather than spinning.
MIN_DT = 1e-9


@dataclass
class SolveResult:
    """Everything one solve produced, including how honest it was."""

    times: list                      # frame times, seconds from event start
    depths: list                     # list of (ny, nx) float64 depth arrays
    dem: np.ndarray
    dx: float
    open_edges: tuple
    steps: int
    ledger: VolumeLedger
    truncated: bool = False
    truncation_reason: str | None = None
    limited_steps: int = 0           # steps where the flux limiter engaged
    min_alpha: float = 1.0           # most aggressive limiting applied
    dt_min: float = 0.0
    dt_max_used: float = 0.0
    dt_mean: float = 0.0
    pits_filled: bool = False

    @property
    def frames(self) -> list:
        """``[(t_seconds, depth_array), ...]`` — the animation payload."""
        return list(zip(self.times, self.depths))

    @property
    def max_depth(self) -> float:
        return float(max((d.max() for d in self.depths), default=0.0))

    def as_meta(self) -> dict:
        """Serializable summary. No arrays — those are packed separately."""
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
    """
    Manning n² on x- and y-faces.

    Accepts a scalar or a full field (the hook for land-cover- and burn-scar-
    derived roughness later); a field is averaged onto each face.
    """
    if np.isscalar(n_manning):
        if n_manning <= 0:
            raise ValueError(f"Manning n must be positive; got {n_manning}.")
        n2 = float(n_manning) ** 2
        return n2, n2

    n = np.asarray(n_manning, dtype=np.float64)
    if n.shape != shape:
        raise ValueError(
            f"n_manning field shape {n.shape} does not match DEM shape {shape}."
        )
    if not np.isfinite(n).all() or np.any(n <= 0):
        raise ValueError("n_manning field must be finite and strictly positive.")
    n2x = (0.5 * (n[:, :-1] + n[:, 1:])) ** 2
    n2y = (0.5 * (n[:-1, :] + n[1:, :])) ** 2
    return n2x, n2y


def _critical_outflow(h_edge: np.ndarray) -> np.ndarray:
    """Free-overfall unit discharge (m²/s) leaving an open boundary."""
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
    max_inflow_rise_m: float = 0.25,
) -> SolveResult:
    """
    Run a flood event and return frames plus full diagnostics.

    Args:
        dem: (ny, nx) bed elevation in metres. Row 0 is north, column 0 west.
        dx: uniform cell size in **metres** (see module note on projection).
        inflow_mask: boolean array marking cells the hydrograph is injected
            into. The discharge is split evenly across them.
        hydrograph: piecewise-linear ``[(t_seconds, m3_per_s), ...]``.
        initial_depth: optional starting water depth field (m).
        n_manning: Manning roughness, scalar or per-cell field.
        dt_max: hard cap on the adaptive time step (s).
        n_frames: number of evenly spaced output frames over the run.
        courant: CFL number. 0.4 is the value Inunda reports as necessary to
            stay stable through the recession limb on incised channels.
        open_edges: edges water may leave through — any of 'north', 'south',
            'east', 'west'; ``'auto'`` picks the lowest-lying edge; ``()``
            makes the domain fully closed.
        duration_s: total simulated time. Defaults to the hydrograph's last
            breakpoint — pass a longer value to watch the flood recede.
        rain_mm_per_hour: uniform rainfall source.
        infiltration_mm_per_hour: uniform loss sink, water-limited.
        fill_dem_pits: condition the DEM with priority-flood filling first.
            Off by default: it changes the terrain, so it is opt-in and
            reported back in the result.
        max_steps: guard against a run that will not finish.
        max_inflow_rise_m: clamp dt so injected water cannot raise an inflow
            cell by more than this in one step.

    Returns:
        SolveResult with frames, step count, and the volume ledger.
    """
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

    # Materialise once: `hydrograph` may be any iterable, and checking it for
    # emptiness would otherwise consume a generator before validation ran.
    pairs = list(hydrograph)
    if pairs:
        h_times, h_values = forcing.validate_hydrograph(pairs)
        if n_inflow == 0 and np.any(h_values > 0):
            raise ValueError(
                "A hydrograph with non-zero discharge was given but the inflow "
                "mask selects no cells — the water has nowhere to enter."
            )
    else:
        h_times = h_values = None

    if duration_s is None:
        if h_times is None:
            raise ValueError(
                "duration_s must be given when there is no hydrograph to take "
                "the run length from."
            )
        duration_s = float(h_times[-1])
    if duration_s <= 0:
        raise ValueError(f"duration_s must be positive; got {duration_s}.")

    if initial_depth is None:
        h = np.zeros((ny, nx), dtype=np.float64)
    else:
        h = np.array(initial_depth, dtype=np.float64, copy=True)
        if h.shape != z.shape:
            raise ValueError(
                f"initial_depth shape {h.shape} does not match DEM shape {z.shape}."
            )
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

    frame_times = (
        np.linspace(0.0, duration_s, n_frames)
        if n_frames > 1
        else np.array([duration_s])
    )

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

    while next_frame < len(frame_times):
        if steps >= max_steps:
            truncated = True
            reason = (
                f"Step budget exhausted after {max_steps} steps at t={t:.1f}s of "
                f"{duration_s:.1f}s. Coarsen the grid, raise dt_max, or shorten "
                f"the event."
            )
            break

        target = float(frame_times[next_frame])

        # ---- adaptive time step -------------------------------------------
        h_max = float(h.max())
        dt = min(
            dt_max,
            courant * dx / np.sqrt(G * max(h_max, CFL_DEPTH_FLOOR)),
        )
        # Injected water must not out-run the CFL limit on its own: cap dt so
        # one step cannot raise an inflow cell by more than max_inflow_rise_m.
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

        # ---- flux sweep: x faces ------------------------------------------
        wse = z + h
        bed_x = np.maximum(z[:, :-1], z[:, 1:])
        hf = np.maximum(wse[:, :-1], wse[:, 1:]) - bed_x
        wet = hf > DEPTH_TOL
        hf_s = np.where(wet, hf, 1.0)
        q_star = qx - G * hf_s * dt * (wse[:, 1:] - wse[:, :-1]) / dx
        q_new = q_star / (1.0 + G * dt * n2x * np.abs(qx) / hf_s ** (7.0 / 3.0))
        cap = hf_s * np.sqrt(G * hf_s)           # Froude <= 1
        qx = np.where(wet, np.clip(q_new, -cap, cap), 0.0)

        # ---- flux sweep: y faces ------------------------------------------
        bed_y = np.maximum(z[:-1, :], z[1:, :])
        hf = np.maximum(wse[:-1, :], wse[1:, :]) - bed_y
        wet = hf > DEPTH_TOL
        hf_s = np.where(wet, hf, 1.0)
        q_star = qy - G * hf_s * dt * (wse[1:, :] - wse[:-1, :]) / dx
        q_new = q_star / (1.0 + G * dt * n2y * np.abs(qy) / hf_s ** (7.0 / 3.0))
        cap = hf_s * np.sqrt(G * hf_s)
        qy = np.where(wet, np.clip(q_new, -cap, cap), 0.0)

        # ---- assemble face fluxes including open boundaries ---------------
        # Fx[:, j] is the flux crossing the face on the WEST side of column j;
        # positive means flow toward +x (east). Same idea for Fy toward +y
        # (south, since row index increases southward).
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

        # ---- depth sweep ---------------------------------------------------
        dh = -dt * ((fx[:, 1:] - fx[:, :-1]) + (fy[1:, :] - fy[:-1, :])) / dx

        # ---- flux limiter (see module docstring, point 1) ------------------
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

        # Boundary discharge, measured after any limiting so the ledger
        # records what actually left rather than what was proposed.
        out_flux = (
            float(np.sum(-fx[:, 0]))
            + float(np.sum(fx[:, -1]))
            + float(np.sum(-fy[0, :]))
            + float(np.sum(fy[-1, :]))
        )
        ledger.discharged += out_flux * dx * dt

        # ---- sources: inflow and rainfall ---------------------------------
        # Sources only add water, so they cannot drive a cell negative and are
        # deliberately outside the limiter.
        if h_values is not None and n_inflow:
            volume = forcing.integrate_hydrograph(h_times, h_values, t, t + dt)
            if volume > 0.0:
                h[mask] += volume / (n_inflow * cell_area)
                ledger.injected += volume
        if rain_rate > 0.0:
            h += rain_rate * dt
            ledger.rained += rain_rate * dt * h.size * cell_area

        # ---- sink: infiltration, water-limited ----------------------------
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
    """
    Run a flood event and return ``(frames, step_count)``.

    ``hydrograph`` is piecewise-linear ``(t_seconds, inflow_m3_per_s)``;
    ``frames`` is ``[(t, depth_array), ...]``, evenly spaced in time for
    animation. This is the convenience form — use `solve` when the volume
    ledger and limiter statistics matter, which for anything user-facing they
    do.
    """
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
