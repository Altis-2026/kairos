"""
Numerical validation of the local-inertial shallow-water solver.

These tests are the reason the solver can be trusted to animate anything. Four
of them guard failure modes that produce a *plausible-looking* result from
wrong physics — water invented from nothing, water leaking across a ridge,
a flood that never recedes, a grid that never settles. None of those announce
themselves; each one has to be asserted against explicitly.

Tolerances here are float64 rounding, not modelling slop. Measured closure
error across these cases is 1e-16 to 1e-15 relative over hundreds to thousands
of steps, so the 1e-12 thresholds below carry three orders of magnitude of
headroom. If one of them ever fails it is a bug in the scheme, not a tolerance
that needs loosening.
"""

import numpy as np
import pytest

from solver import solve
from solver.forcing import lowest_cells_mask
from solver.hydraulic_route import run_event

# Relative volume-closure tolerance. See module note.
MASS_TOL = 1e-12


def _volume(depth: np.ndarray, dx: float) -> float:
    return float(depth.sum()) * dx * dx


# --------------------------------------------------------------------------
# 1. Mass conservation
# --------------------------------------------------------------------------
def test_closed_basin_conserves_volume_exactly(bowl):
    """
    A closed basin with no inflow and no outlet must hold exactly the water it
    started with, however violently that water sloshes.

    This is the assertion that would have caught clipping negative depths to
    zero: that bug is invisible in every visual check and shows up here as a
    growing volume.
    """
    dem = bowl(40)
    dx = 20.0
    start = np.zeros_like(dem)
    start[15:25, 15:25] = 2.0

    result = solve(
        dem, dx, initial_depth=start, open_edges=(), duration_s=3600.0,
        n_frames=6, dt_max=5.0,
    )

    assert result.steps > 500, "run was too short to be a meaningful test"
    v0, v1 = _volume(start, dx), _volume(result.depths[-1], dx)
    assert abs(v1 - v0) / v0 < MASS_TOL
    assert abs(result.ledger.mass_error) < MASS_TOL
    assert result.ledger.discharged == 0.0, "a closed domain discharged water"


# --------------------------------------------------------------------------
# 2. Ridge non-crossing
# --------------------------------------------------------------------------
def test_water_never_crosses_a_ridge_it_cannot_top(two_basins):
    """
    Two basins, one ridge, water only on the left and never deep enough to top
    it: the right basin must stay bone dry — exactly zero, not "almost zero".

    This is the failure mode a flat-plane depth approximation gets wrong, and
    it is the single most important regression test in the file. Keep it
    forever.
    """
    dem = two_basins(n=41, ridge_height=5.0)
    dx = 10.0
    mid = 41 // 2
    start = np.zeros_like(dem)
    start[5:36, 5:15] = 3.0          # well below the 5 m ridge crest

    result = solve(
        dem, dx, initial_depth=start, open_edges=(), duration_s=1800.0,
        n_frames=6, dt_max=2.0,
    )

    far_side = [d[:, mid + 2:] for d in result.depths]
    assert max(float(d.max()) for d in far_side) == 0.0

    # And the water really did move on the near side, so the dry far side is
    # a physical result rather than a solver that simply did nothing.
    assert float(result.depths[-1][:, :mid - 1].max()) < 3.0
    assert abs(result.ledger.mass_error) < MASS_TOL


# --------------------------------------------------------------------------
# 3. Settling
# --------------------------------------------------------------------------
def test_arbitrary_distribution_settles_to_a_flat_surface(bowl):
    """
    Water dumped as a block in a bowl must relax toward a level surface: the
    spread of water-surface elevation across wet cells has to collapse.
    """
    dem = bowl(40)
    dx = 20.0
    start = np.zeros_like(dem)
    start[12:20, 18:30] = 2.5

    result = solve(
        dem, dx, initial_depth=start, open_edges=(), duration_s=7200.0,
        n_frames=4, dt_max=5.0,
    )

    def surface_spread(depth):
        wet = depth > 1e-3
        return float(np.std((dem + depth)[wet])) if wet.any() else 0.0

    assert surface_spread(result.depths[-1]) < 0.05 * surface_spread(start)
    assert surface_spread(result.depths[-1]) < 0.05   # metres, near-level


# --------------------------------------------------------------------------
# 4. Recession
# --------------------------------------------------------------------------
def test_flood_recedes_through_an_open_boundary(tilted_channel):
    """
    With an open downstream edge and a hydrograph that ramps back to zero, the
    flood must actually recede — not plateau.

    Without an open boundary this test fails by construction: a domain walled
    on all four sides has nowhere to put the water.
    """
    dem = tilted_channel()
    dx = 30.0
    mask = lowest_cells_mask(dem, row=2, col=15, n_cells=9, radius=2)
    hydrograph = [(0.0, 0.0), (600.0, 120.0), (1800.0, 120.0), (3600.0, 0.0)]

    result = solve(
        dem, dx, inflow_mask=mask, hydrograph=hydrograph, duration_s=9000.0,
        n_frames=24, open_edges=("south",), dt_max=5.0,
    )

    peaks = [float(d.max()) for d in result.depths]
    crest = max(peaks)
    assert crest > 0.1, "no meaningful flood wave was produced"
    assert peaks[-1] < 0.2 * crest, "water plateaued instead of receding"
    assert np.argmax(peaks) < len(peaks) - 1, "peak never passed"
    assert result.ledger.discharged > 0.0

    # Injected volume must match the hydrograph's exact integral:
    # 0.5*600*120 + 1200*120 + 0.5*1800*120 = 288000 m3.
    assert result.ledger.injected == pytest.approx(288000.0, rel=1e-12)
    assert abs(result.ledger.mass_error) < MASS_TOL


# --------------------------------------------------------------------------
# 5. Stability
# --------------------------------------------------------------------------
def test_steep_noisy_terrain_stays_finite_and_non_negative(noisy_slope):
    """
    Steep, noisy topography at the default Courant number must not produce
    NaNs, infinities, or negative depths in any frame.
    """
    dem = noisy_slope(n=48, drop=60.0, noise=1.5)

    result = solve(
        dem, 20.0, rain_mm_per_hour=80.0, duration_s=5400.0, n_frames=12,
        open_edges=("south",), dt_max=5.0, courant=0.4,
    )

    stack = np.array(result.depths)
    assert np.isfinite(stack).all(), "solver produced NaN or infinity"
    assert stack.min() >= 0.0, "solver produced a negative depth"
    assert stack.max() > 0.0, "nothing happened — the test proves nothing"
    assert abs(result.ledger.mass_error) < MASS_TOL
    assert not result.truncated


# --------------------------------------------------------------------------
# 6. The limiter must actually fire
# --------------------------------------------------------------------------
def test_flux_limiter_engages_and_still_conserves_mass():
    """
    Exercise the flux limiter on purpose.

    Tests 1-5 pass whether or not the limiter is ever reached, so on their own
    they are no evidence that it works — a mass-conservation test that never
    touches the code path protecting mass conservation proves nothing. This
    case (steep terrain, a thin water film, a deliberately aggressive step)
    drives cells to propose draining more than they hold, and asserts three
    things at once: the limiter engaged, depth stayed non-negative, and not one
    drop of water was created or destroyed while it did.
    """
    rng = np.random.default_rng(1)
    n = 40
    dem = np.linspace(80.0, 0.0, n)[:, None] * np.ones((1, n))
    dem = dem + rng.normal(0.0, 1.0, size=(n, n))
    dx = 5.0
    start = np.full((n, n), 0.02)

    result = solve(
        dem, dx, initial_depth=start, open_edges=(), duration_s=300.0,
        n_frames=4, dt_max=10.0, courant=1.0,
    )

    assert result.limited_steps > 0, (
        "the limiter never engaged, so this test is not exercising it — "
        "make the step more aggressive or the terrain steeper"
    )
    assert result.min_alpha < 1.0

    stack = np.array(result.depths)
    assert stack.min() >= 0.0
    v0, v1 = _volume(start, dx), _volume(result.depths[-1], dx)
    assert abs(v1 - v0) / v0 < MASS_TOL
    assert abs(result.ledger.mass_error) < MASS_TOL


# --------------------------------------------------------------------------
# 7. Open-boundary mass balance
# --------------------------------------------------------------------------
def test_open_boundary_outflow_balances_the_ledger(tilted_channel):
    """
    stored == initial + injected - discharged, exactly.

    The limiter scales boundary outflow along with the interior fluxes; if it
    ever forgets to, or if the ledger records the proposed outflow rather than
    the applied one, the identity breaks here and nowhere else.
    """
    dem = tilted_channel()
    dx = 30.0
    start = np.zeros_like(dem)
    start[5:20, 10:20] = 1.5
    mask = lowest_cells_mask(dem, row=2, col=15, n_cells=6, radius=2)
    hydrograph = [(0.0, 40.0), (1200.0, 0.0)]

    result = solve(
        dem, dx, initial_depth=start, inflow_mask=mask, hydrograph=hydrograph,
        duration_s=4800.0, n_frames=8, open_edges=("south", "east"), dt_max=5.0,
    )

    ledger = result.ledger
    expected = ledger.initial + ledger.injected - ledger.discharged
    assert ledger.discharged > 0.0, "nothing left through the open edges"
    assert abs(ledger.stored - expected) / ledger.initial < MASS_TOL
    assert _volume(result.depths[-1], dx) == pytest.approx(ledger.stored, rel=1e-12)


# --------------------------------------------------------------------------
# 8. Frame timing
# --------------------------------------------------------------------------
def test_frames_land_exactly_on_the_requested_times(tilted_channel):
    """
    Adaptive steps must be clipped so output lands on the requested times.

    Frames that drift off the schedule make the UI scrubber quietly lie about
    when each state occurred.
    """
    dem = tilted_channel()
    hydrograph = [(0.0, 0.0), (300.0, 60.0), (1200.0, 0.0)]
    mask = lowest_cells_mask(dem, row=2, col=15, n_cells=9, radius=2)

    result = solve(
        dem, 30.0, inflow_mask=mask, hydrograph=hydrograph, duration_s=2400.0,
        n_frames=17, open_edges=("south",),
    )

    assert len(result.times) == 17
    assert np.array_equal(np.array(result.times), np.linspace(0.0, 2400.0, 17))
    assert all(d.shape == dem.shape for d in result.depths)


# --------------------------------------------------------------------------
# API surface and guard rails
# --------------------------------------------------------------------------
def test_run_event_returns_frames_and_step_count(tilted_channel):
    """The documented convenience signature: (frames, step_count)."""
    dem = tilted_channel()
    mask = lowest_cells_mask(dem, row=2, col=15, n_cells=9, radius=2)
    frames, steps = run_event(
        dem, 30.0, mask, [(0.0, 0.0), (600.0, 80.0), (1800.0, 0.0)], n_frames=8,
    )

    assert steps > 0
    assert len(frames) == 8
    t, depth = frames[3]
    assert isinstance(t, float) and depth.shape == dem.shape


def test_auto_open_edge_picks_the_lowest_lying_boundary(tilted_channel):
    dem = tilted_channel()
    result = solve(dem, 30.0, initial_depth=np.zeros_like(dem),
                   open_edges="auto", duration_s=10.0, n_frames=1)
    assert result.open_edges == ("south",)


def test_rainfall_and_infiltration_are_both_tracked(noisy_slope):
    dem = noisy_slope(n=32)
    result = solve(
        dem, 20.0, rain_mm_per_hour=80.0, infiltration_mm_per_hour=20.0,
        duration_s=3600.0, n_frames=4, open_edges=("south",),
    )
    assert result.ledger.rained > 0.0
    assert result.ledger.infiltrated > 0.0
    assert abs(result.ledger.mass_error) < MASS_TOL


def test_a_run_that_cannot_finish_is_reported_not_hidden(tilted_channel):
    """Exceeding the step budget truncates and says so — it never fabricates."""
    dem = tilted_channel()
    mask = lowest_cells_mask(dem, row=2, col=15, n_cells=9, radius=2)
    result = solve(
        dem, 30.0, inflow_mask=mask, hydrograph=[(0.0, 100.0), (7200.0, 100.0)],
        duration_s=7200.0, n_frames=12, open_edges=("south",), max_steps=50,
    )
    assert result.truncated
    assert "Step budget" in result.truncation_reason
    assert len(result.depths) < 12


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"courant": 1.5}, "courant"),
        ({"n_frames": 0}, "n_frames"),
        ({"dt_max": 0.0}, "dt_max"),
        ({"open_edges": ("up",)}, "Unknown open edge"),
        ({"n_manning": 0.0}, "Manning"),
    ],
)
def test_invalid_parameters_fail_loudly(bowl, kwargs, message):
    dem = bowl(10)
    with pytest.raises(ValueError, match=message):
        solve(dem, 10.0, duration_s=60.0, **kwargs)


def test_lat_lon_sized_grid_is_not_silently_accepted(bowl):
    """dx must be a real positive metric cell size."""
    with pytest.raises(ValueError, match="dx must be"):
        solve(bowl(10), 0.0, duration_s=60.0)


def test_non_finite_dem_is_rejected(bowl):
    dem = bowl(10)
    dem[3, 3] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        solve(dem, 10.0, duration_s=60.0)


def test_hydrograph_without_anywhere_to_enter_is_rejected(bowl):
    dem = bowl(10)
    with pytest.raises(ValueError, match="nowhere to enter"):
        solve(dem, 10.0, hydrograph=[(0.0, 50.0), (600.0, 50.0)])
