"""
Tests for landscape fire spread.

The valuable checks here are the ones with a closed-form answer to compare
against. A fire on flat ground in still air is a circle growing at a known
rate; a fire under wind is an ellipse whose head and backing rates the
Richards formula gives exactly. Both are checked numerically rather than by
eye, because a spread pattern that is subtly wrong — biased toward the
lattice axes, or with the ignition in the middle of the burn instead of near
its back — looks entirely plausible in a screenshot.
"""

import numpy as np
import pytest

from solver.fire_behavior import (
    FUEL_MODELS,
    length_to_breadth,
    prepare,
    slope_factor,
)
from solver.fire_spread import (
    MIN_SPREAD_M_MIN,
    combine_wind_and_slope,
    effective_wind_ms,
    elliptical_rate,
    spread,
    terrain_slope,
)

DRY = {"dead_1h": 0.06, "dead_10h": 0.07, "dead_100h": 0.08, "live": 1.00}


@pytest.fixture
def grass():
    return prepare(FUEL_MODELS["gr1"], DRY)


def flat(n=121):
    dem = np.zeros((n, n))
    ig = np.zeros((n, n), dtype=bool)
    ig[n // 2, n // 2] = True
    return dem, ig


# --------------------------------------------------------------------------
# Closed-form comparisons
# --------------------------------------------------------------------------

def test_still_air_on_flat_ground_burns_a_circle(grass):
    """
    With no wind and no slope the burn is a disc of the analytic radius.

    Area is the check rather than the outline, because area is what a user
    reads off the result and it integrates every direction at once: a front
    that bulged along the grid axes would pass an axis-only radius check and
    fail this one.
    """
    dem, ig = flat()
    minutes = 200.0
    res = spread(grass, dem, 10.0, ig, wind_ms=0.0, duration_min=minutes)

    radius = grass.r0_m_min * minutes
    expected_ha = np.pi * radius * radius / 1e4
    assert res.area_burned_m2() / 1e4 == pytest.approx(expected_ha, rel=0.05)


def test_head_and_backing_rates_match_the_richards_ellipse(grass):
    """
    Arrival times downwind and upwind match the ellipse formula exactly.

    This is the strongest check in the file. The head rate and the backing
    rate come from opposite ends of the eccentricity term, so a sign error,
    a reciprocal, or an ignition placed at the ellipse centre instead of its
    focus all break one or the other.
    """
    dem, ig = flat()
    c = dem.shape[0] // 2
    res = spread(grass, dem, 10.0, ig, wind_ms=3.0,
                 wind_from_bearing=270.0, duration_min=60.0)

    lb = float(res.length_breadth[c, c])
    ecc = np.sqrt(lb * lb - 1.0) / lb
    head = float(res.ros_m_min[c, c])
    back = head * (1.0 - ecc) / (1.0 + ecc)

    for cells in (5, 10, 20):
        metres = cells * 10.0
        assert float(res.arrival_min[c, c + cells]) == pytest.approx(
            metres / head, rel=0.02)          # downwind
    for cells in (5, 10):
        metres = cells * 10.0
        assert float(res.arrival_min[c, c - cells]) == pytest.approx(
            metres / back, rel=0.02)          # upwind, creeping


def test_angular_error_shrinks_with_more_neighbours(grass):
    """
    The 16-neighbour set cuts the lattice's directional bias to a third.

    Travel time on a discrete graph can only overestimate — a path has to
    follow available bearings — so the error is one-sided, and its size is
    the honest statement of how much a spread outline can be trusted.
    """
    dem, ig = flat(161)
    n = dem.shape[0]
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    true_time = np.hypot(yy - c, xx - c) * 10.0 / grass.r0_m_min

    errors = {}
    for nb in (8, 16, 32):
        res = spread(grass, dem, 10.0, ig, duration_min=200.0, neighbours=nb)
        m = np.isfinite(res.arrival_min) & (true_time > 50.0 / grass.r0_m_min)
        rel = (res.arrival_min[m] - true_time[m]) / true_time[m]
        # Arrival times are stored as float32, so allow for its rounding and
        # nothing more; a real undershoot would be orders of magnitude larger.
        assert rel.min() > -1e-6, "travel time on a graph cannot undershoot"
        errors[nb] = rel.max()

    assert errors[8] > 0.07
    assert errors[16] < 0.03
    assert errors[32] < 0.015
    assert errors[32] < errors[16] < errors[8]


# --------------------------------------------------------------------------
# Direction
# --------------------------------------------------------------------------

def test_wind_direction_follows_the_weather_convention(grass):
    """
    A wind *from* the west drives the fire east.

    The most consequential thing a caller can get wrong here is the sign of
    the wind, and a reversed fire still looks like a fire.
    """
    dem, ig = flat()
    c = dem.shape[0] // 2
    res = spread(grass, dem, 10.0, ig, wind_ms=4.0,
                 wind_from_bearing=270.0, duration_min=45.0)
    east = res.arrival_min[c, c + 15]
    west = res.arrival_min[c, c - 15]
    assert east < west
    assert float(res.head_bearing[c, c]) == pytest.approx(90.0, abs=0.5)


def test_fire_runs_uphill_faster_than_downhill(grass):
    """Slope alone, no wind: the head points upslope."""
    n = 121
    dem = np.tile(np.linspace(0, 300, n), (n, 1))   # rises toward the east
    ig = np.zeros((n, n), dtype=bool)
    c = n // 2
    ig[c, c] = True
    res = spread(grass, dem, 10.0, ig, wind_ms=0.0, duration_min=120.0)

    assert float(res.head_bearing[c, c]) == pytest.approx(90.0, abs=0.5)
    assert res.arrival_min[c, c + 10] < res.arrival_min[c, c - 10]


def test_upslope_wind_and_slope_reinforce_but_opposed_ones_cancel(grass):
    """
    Wind and slope are combined as vectors, not as scalars.

    Rothermel's `1 + phi_w + phi_s` is only correct when both point the same
    way. A downslope wind against an upslope must be able to partially cancel
    — and a scalar sum makes it *accelerate* the fire instead, which is the
    specific failure this guards.
    """
    n = 61
    slope = np.full((n, n), 0.4)
    upslope = np.full((n, n), 90.0)      # uphill toward the east

    phi_s = float(np.asarray(slope_factor(grass, slope))[0, 0])
    with_wind, bearing_same = combine_wind_and_slope(
        grass, 3.0, 90.0, slope, upslope)          # wind also toward the east
    against, bearing_opp = combine_wind_and_slope(
        grass, 3.0, 270.0, slope, upslope)         # wind toward the west

    # Aligned, the two add; opposed, they subtract. The gap between the two
    # cases is therefore exactly twice the slope contribution — which is the
    # arithmetic a scalar sum cannot reproduce, since it would give the same
    # answer both times.
    assert with_wind[0, 0] - against[0, 0] == pytest.approx(2 * phi_s, rel=1e-6)
    assert against[0, 0] < with_wind[0, 0]
    assert bearing_same[0, 0] == pytest.approx(90.0, abs=0.5)
    # Wind is the stronger of the two here, so it wins the direction outright.
    assert bearing_opp[0, 0] == pytest.approx(270.0, abs=0.5)


def test_cross_slope_wind_pushes_the_head_diagonally(grass):
    """A north wind on an east-facing slope sends the fire southeast."""
    n = 41
    slope = np.full((n, n), 0.3)
    upslope = np.full((n, n), 90.0)              # uphill east
    _, bearing = combine_wind_and_slope(grass, 2.0, 180.0, slope, upslope)
    assert 90.0 < float(bearing[0, 0]) < 180.0


# --------------------------------------------------------------------------
# Terrain
# --------------------------------------------------------------------------

def test_terrain_slope_reads_a_known_plane():
    """A plane rising 1 in 10 toward the north reads back as exactly that."""
    n = 21
    dx = 10.0
    # Row 0 is north, so northward rise means elevation falls with row index.
    dem = np.tile(np.linspace(200, 0, n)[:, None], (1, n))
    slope, bearing = terrain_slope(dem, dx)

    assert slope[n // 2, n // 2] == pytest.approx(1.0, rel=1e-9)
    assert bearing[n // 2, n // 2] == pytest.approx(0.0, abs=1e-6)


def test_terrain_slope_bearing_points_east_when_ground_rises_east():
    n = 21
    dem = np.tile(np.linspace(0, 200, n), (n, 1))
    slope, bearing = terrain_slope(dem, 10.0)
    assert bearing[n // 2, n // 2] == pytest.approx(90.0, abs=1e-6)


def test_flat_ground_has_no_slope_direction():
    slope, _ = terrain_slope(np.zeros((10, 10)), 30.0)
    assert np.all(slope == 0.0)


# --------------------------------------------------------------------------
# Barriers and non-burnable fuel
# --------------------------------------------------------------------------

def test_a_barrier_stops_the_fire(grass):
    """A full-width fireline is not crossed."""
    n = 81
    dem = np.zeros((n, n))
    ig = np.zeros((n, n), dtype=bool)
    ig[n // 2, 5] = True
    barrier = np.zeros((n, n), dtype=bool)
    barrier[:, 40:43] = True                  # a three-cell break, wall to wall

    res = spread(grass, dem, 10.0, ig, wind_ms=5.0, wind_from_bearing=270.0,
                 duration_min=600.0, barrier=barrier)

    assert res.burned[:, :40].any()
    assert not res.burned[:, 40:].any()


def test_fire_flows_around_a_partial_barrier(grass):
    """A break that does not reach the edge is flanked, not stopped."""
    n = 81
    dem = np.zeros((n, n))
    ig = np.zeros((n, n), dtype=bool)
    ig[n // 2, 5] = True
    barrier = np.zeros((n, n), dtype=bool)
    barrier[10:70, 40:43] = True              # gaps at both ends

    res = spread(grass, dem, 10.0, ig, wind_ms=5.0, wind_from_bearing=270.0,
                 duration_min=600.0, barrier=barrier)

    assert res.burned[:, 50:].any(), "fire should get round the ends"
    assert not res.burned[barrier].any(), "the break itself never burns"


@pytest.mark.parametrize("neighbours", [8, 16, 32])
def test_a_one_cell_fireline_cannot_be_jumped(grass, neighbours):
    """
    Narrow barriers hold, whatever the neighbourhood.

    The longer hops that make the spread outline smooth also skip over ground,
    and a knight's move lands on a burnable cell having crossed a barrier
    without ever testing it. Measured before the fix: a one-cell fireline
    leaked with both the 16- and 32-offset sets, and a two-cell fireline
    leaked with 32. Nothing about the rendered burn would have looked wrong.
    """
    n = 61
    dem = np.zeros((n, n))
    ig = np.zeros((n, n), dtype=bool)
    ig[n // 2, 5] = True
    barrier = np.zeros((n, n), dtype=bool)
    barrier[:, 30] = True                    # one cell wide, wall to wall

    res = spread(grass, dem, 10.0, ig, wind_ms=6.0, wind_from_bearing=270.0,
                 duration_min=900.0, barrier=barrier, neighbours=neighbours)

    assert res.burned[:, :30].any(), "the fire should still run up to the line"
    assert not res.burned[:, 30:].any(), "the fireline was jumped"


def test_nonburnable_fuel_never_ignites():
    """A fuel bed at its moisture of extinction does not carry a fire."""
    fuel = FUEL_MODELS["gr1"]
    wet = prepare(fuel, {"dead_1h": 0.5, "dead_10h": 0.5,
                         "dead_100h": 0.5, "live": 1.0})
    dem, ig = flat(41)
    res = spread(wet, dem, 10.0, ig, wind_ms=5.0, duration_min=600.0)
    assert res.burned.sum() == 1        # the ignition cell and nothing else


# --------------------------------------------------------------------------
# Mechanics of the solve
# --------------------------------------------------------------------------

def test_duration_bounds_the_arrival_times(grass):
    dem, ig = flat(81)
    res = spread(grass, dem, 10.0, ig, wind_ms=2.0, duration_min=90.0)
    finite = res.arrival_min[np.isfinite(res.arrival_min)]
    assert finite.max() <= 90.0
    assert res.area_burned_m2(30.0) < res.area_burned_m2(90.0)


def test_a_longer_solve_only_adds_burned_area(grass):
    """
    Arrival times do not change when the fire is given more time.

    Dijkstra settles a cell once and for all, so extending the duration must
    extend the burn without disturbing what was already solved. If that fails,
    the frontier is being cut off early somewhere.
    """
    dem, ig = flat(81)
    short = spread(grass, dem, 10.0, ig, wind_ms=2.0, duration_min=60.0)
    long = spread(grass, dem, 10.0, ig, wind_ms=2.0, duration_min=180.0)

    m = np.isfinite(short.arrival_min)
    assert np.allclose(short.arrival_min[m], long.arrival_min[m])
    assert long.burned.sum() > short.burned.sum()


def test_multiple_ignitions_merge(grass):
    """Two starts produce one burn, each cell reached by whichever is nearer."""
    n = 81
    dem = np.zeros((n, n))
    ig = np.zeros((n, n), dtype=bool)
    ig[40, 20] = True
    ig[40, 60] = True
    res = spread(grass, dem, 10.0, ig, duration_min=300.0)

    assert res.arrival_min[40, 20] == 0.0
    assert res.arrival_min[40, 60] == 0.0
    # The midpoint is 200 m from each start, and is reached at the time a
    # single fire would take to cover that distance — neither front is
    # delayed or helped by the presence of the other.
    assert float(res.arrival_min[40, 40]) == pytest.approx(
        200.0 / grass.r0_m_min, rel=0.02)
    # ...and symmetrically, since the two starts are identical.
    assert float(res.arrival_min[40, 39]) == pytest.approx(
        float(res.arrival_min[40, 41]), rel=1e-5)


def test_intensity_and_flame_length_are_reported_only_where_it_burned(grass):
    dem, ig = flat(61)
    res = spread(grass, dem, 10.0, ig, wind_ms=3.0, duration_min=60.0)
    assert np.all(res.flame_length_m[~res.burned] == 0.0)
    assert np.all(res.intensity_kw_m[~res.burned] == 0.0)
    assert res.flame_length_m[res.burned].max() > 0.3
    # Byram's flame length for a grass fire of this intensity is metres, not
    # tens of metres; a unit slip here is otherwise invisible.
    assert res.flame_length_m[res.burned].max() < 20.0


def test_stronger_wind_burns_more_area_in_the_same_time(grass):
    dem, ig = flat(151)
    areas = [
        spread(grass, dem, 10.0, ig, wind_ms=u, wind_from_bearing=270.0,
               duration_min=60.0).area_burned_m2()
        for u in (0.0, 2.0, 5.0)
    ]
    assert areas == sorted(areas)


def test_effective_wind_turns_slope_into_the_wind_it_resembles(grass):
    """
    A steep slope in still air elongates the ellipse as a wind would.

    Without this, a fire running up a canyon wall would spread fast but stay
    circular, which is not what fires on steep ground do.
    """
    steep = np.full((5, 5), 0.6)
    flat_ground = np.zeros((5, 5))
    phi_steep, _ = combine_wind_and_slope(grass, 0.0, 0.0, steep,
                                          np.full((5, 5), 0.0))
    phi_flat, _ = combine_wind_and_slope(grass, 0.0, 0.0, flat_ground,
                                         np.zeros((5, 5)))
    lb_steep = length_to_breadth(effective_wind_ms(grass, phi_steep))
    lb_flat = length_to_breadth(effective_wind_ms(grass, phi_flat))
    assert lb_steep.max() > 1.5
    assert lb_flat.max() == pytest.approx(1.0)


def test_elliptical_rate_is_a_circle_without_wind():
    head = np.array([[5.0]])
    bearing = np.array([[0.0]])
    lb = np.array([[1.0]])
    rates = [float(elliptical_rate(head, bearing, lb, b)[0, 0])
             for b in (0, 45, 90, 180, 270)]
    assert all(r == pytest.approx(5.0) for r in rates)


def test_elliptical_rate_peaks_at_the_head():
    head = np.array([[10.0]])
    bearing = np.array([[45.0]])
    lb = np.array([[3.0]])
    at_head = float(elliptical_rate(head, bearing, lb, 45.0)[0, 0])
    assert at_head == pytest.approx(10.0)
    for b in (0.0, 90.0, 135.0, 225.0):
        assert float(elliptical_rate(head, bearing, lb, b)[0, 0]) < at_head


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs,message", [
    ({"dx": 0.0}, "dx"),
    ({"duration_min": 0.0}, "duration"),
    ({"neighbours": 5}, "neighbours"),
])
def test_bad_arguments_are_rejected(grass, kwargs, message):
    dem, ig = flat(11)
    call = {"dx": 10.0, "duration_min": 60.0, "neighbours": 16}
    call.update(kwargs)
    with pytest.raises(ValueError, match=message):
        spread(grass, dem, ignition=ig, **call)


def test_an_unlit_landscape_is_rejected(grass):
    dem = np.zeros((11, 11))
    with pytest.raises(ValueError, match="ignition"):
        spread(grass, dem, 10.0, np.zeros((11, 11), dtype=bool))


def test_mismatched_shapes_are_rejected(grass):
    with pytest.raises(ValueError, match="same shape"):
        spread(grass, np.zeros((11, 11)), 10.0, np.ones((9, 9), dtype=bool))
    with pytest.raises(ValueError, match="same shape"):
        spread(grass, np.zeros((11, 11)), 10.0, np.ones((11, 11), dtype=bool),
               barrier=np.zeros((5, 5), dtype=bool))
