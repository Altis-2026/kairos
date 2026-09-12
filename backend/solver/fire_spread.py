"""
Propagate a surface fire across a landscape as a minimum-arrival-time problem.

`fire_behavior` answers "how fast, here, in the head direction?". This answers
"when does the front reach each cell?", which needs three more things: the
direction the head actually points once wind and slope are combined, how much
slower the fire spreads in every other direction, and a way to accumulate
travel time across a grid.

Method
------
Finney's (2002) minimum travel time, the same formulation FARSITE and
FlamMap use. Each cell carries an elliptical spread template — Richards
(1990) — and the arrival time at a cell is the shortest travel time along any
path of cell-to-cell hops from the ignition. That is a shortest-path problem
on a weighted graph, so Dijkstra solves it exactly, in one pass, with no
timestep and therefore no stability condition to violate.

Why not a cellular automaton
----------------------------
The obvious alternative — step time forward and let burning cells ignite their
neighbours — is easier to write and quietly wrong in a way that is hard to
see: spread rate becomes tied to the timestep, and the fire front develops a
square or octagonal bias from the lattice that looks like fire behaviour and
is not. Minimum travel time has no timestep to couple to, and its error is a
pure angular discretisation that shrinks predictably as neighbours are added
(see `NEIGHBOURHOODS`) and is measured in the tests.

Conventions
-----------
Row 0 is north, matching the flood solver's grid. Bearings are degrees
clockwise from north. Wind is given the way weather reports give it — the
direction it blows *from* — and converted once, at the boundary, because a
reversed wind is the single most consequential thing a caller can get wrong
here and the convention should be the one they already hold.
"""

import heapq
from dataclasses import dataclass

import numpy as np

from solver.fire_behavior import (
    FuelBed,
    MS_TO_FT_MIN,
    length_to_breadth,
    slope_factor,
    wind_factor,
)

#: Neighbour offsets. The 8-neighbour set can only represent spread along
#: eight bearings, so a circular fire comes out visibly octagonal and travel
#: along an off-axis bearing is overestimated by up to 8%. Adding longer hops
#: adds bearings and cuts that error; the cost is roughly linear in the number
#: of offsets. Measured against an analytic circle by
#: `test_angular_error_shrinks_with_more_neighbours`:
#:
#:     offsets    worst-case    mean      301x301 solve
#:          8         8.2%      5.4%           0.3 s
#:         16         2.8%      1.4%           0.6 s
#:         32         1.3%      0.5%           1.1 s
#:
#: 32 is the default: at a second or so for a typical scene the accuracy is
#: worth paying for, and the interior arrival field stops showing the chevron
#: faceting that the coarser sets leave behind. 8 exists so the test has a
#: case where the error is unmistakable.
NEIGHBOURHOODS = {
    8: [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)],
    16: [
        (-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1),
        (-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1),
    ],
    32: [
        (-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1),
        (-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1),
        (-3, -1), (-3, 1), (-1, -3), (-1, 3), (1, -3), (1, 3), (3, -1), (3, 1),
        (-3, -2), (-3, 2), (-2, -3), (-2, 3), (2, -3), (2, 3), (3, -2), (3, 2),
    ],
}

def _intermediate_cells(dr: int, dc: int) -> tuple:
    """
    Cells a hop from (0,0) to (dr,dc) passes through, endpoints excluded.

    Hops longer than one cell skip over ground. Without this, a fire could
    cross a one-cell-wide fireline or river diagonally by a knight's move —
    the destination is burnable, so nothing in the obvious check objects, and
    the result is a fire that jumps a barrier that should have held it. That
    is invisible in a rendered outline and would quietly invalidate every
    containment scenario the simulator is useful for.
    """
    steps = 4 * max(abs(dr), abs(dc))
    cells = []
    for i in range(1, steps):
        t = i / steps
        cell = (int(round(dr * t)), int(round(dc * t)))
        if cell not in cells and cell != (0, 0) and cell != (dr, dc):
            cells.append(cell)
    return tuple(cells)


#: Spread slower than this is treated as no spread at all. Below roughly a
#: millimetre a minute a fire is not propagating, and leaving the values in
#: produces arrival times of tens of thousands of hours that are noise
#: dressed as data.
MIN_SPREAD_M_MIN = 1e-3

#: Byram's flame length constant and exponent, for intensity in BTU/ft/s and
#: flame length in feet.
_FLAME_A = 0.45
_FLAME_B = 0.46
#: 1 BTU/ft/s in kW/m.
BTU_FT_S_TO_KW_M = 3.46414
_FT_TO_M = 0.3048


@dataclass
class FireResult:
    """
    A solved fire.

    `arrival_min` is the headline product: minutes from ignition until the
    front reaches each cell, `inf` where the fire never arrives. Everything
    else describes the fire *at* that arrival — the rate, intensity and flame
    length of the front as it passes — which is what a fire behaviour analyst
    reads off a map, not the peak anywhere or the average over time.
    """

    arrival_min: np.ndarray        # float32, inf where unburned
    ros_m_min: np.ndarray          # head-fire rate of spread at each cell
    intensity_kw_m: np.ndarray     # Byram's fireline intensity
    flame_length_m: np.ndarray
    slope_tan: np.ndarray
    upslope_bearing: np.ndarray    # degrees clockwise from north
    head_bearing: np.ndarray       # degrees, combined wind and slope
    length_breadth: np.ndarray     # ellipse elongation at each cell
    burnable: np.ndarray           # bool
    duration_min: float
    dx: float

    @property
    def burned(self) -> np.ndarray:
        return np.isfinite(self.arrival_min)

    def burned_at(self, minutes: float) -> np.ndarray:
        return self.arrival_min <= minutes

    def area_burned_m2(self, minutes: float = None) -> float:
        mask = self.burned if minutes is None else self.burned_at(minutes)
        return float(mask.sum()) * self.dx * self.dx


def terrain_slope(dem: np.ndarray, dx: float) -> tuple:
    """
    Slope (rise over run) and the bearing of steepest ascent, per cell.

    Uses a centred difference, which is the right choice over a one-sided
    difference here: fire spread depends on the slope a fire crosses, and a
    one-sided gradient reports the slope of one side of the cell rather than
    the slope through it, biasing the whole field half a cell downhill.
    """
    if dem.ndim != 2:
        raise ValueError("dem must be 2-D")
    # np.gradient's axis 0 runs down rows, i.e. southward, so the northward
    # gradient is its negation.
    d_row, d_col = np.gradient(dem.astype(np.float64), dx)
    g_north = -d_row
    g_east = d_col

    slope = np.hypot(g_north, g_east)
    bearing = np.degrees(np.arctan2(g_east, g_north)) % 360.0
    return slope.astype(np.float64), bearing.astype(np.float64)


def effective_wind_ms(bed: FuelBed, phi_combined: np.ndarray) -> np.ndarray:
    """
    The wind speed that alone would produce this combined wind-and-slope
    factor.

    On a steep slope in light wind the fire behaves like a wind-driven fire
    even though the wind is mild, and the ellipse should elongate to match.
    Inverting Rothermel's wind coefficient is how that is expressed: slope is
    converted into the wind it is equivalent to, and the ellipse geometry then
    depends on one quantity rather than two.
    """
    if not bed.burnable or bed.wind_b == 0:
        return np.zeros_like(phi_combined)
    base = bed.wind_c * bed.beta_ratio ** -bed.wind_e
    with np.errstate(divide="ignore", invalid="ignore"):
        u_ft_min = np.where(
            phi_combined > 0, (np.maximum(phi_combined, 0) / base) ** (1.0 / bed.wind_b), 0.0
        )
    u_ft_min = np.clip(np.nan_to_num(u_ft_min), 0.0, bed.max_wind_ft_min)
    return u_ft_min / MS_TO_FT_MIN


def combine_wind_and_slope(
    bed: FuelBed,
    wind_ms: float,
    wind_to_bearing: float,
    slope_tan: np.ndarray,
    upslope_bearing: np.ndarray,
) -> tuple:
    """
    Vector-sum the wind and slope coefficients into one head direction.

    Rothermel gives two scalar multipliers, one for wind and one for slope,
    each acting along its own bearing. Adding them as scalars — which is what
    the bare `1 + phi_w + phi_s` in the point model does — is only correct
    when they point the same way. Treating them as vectors is what lets a
    cross-slope wind push a fire diagonally, and lets a strong upslope
    partially cancel a downslope wind, both of which are ordinary fire
    behaviour and neither of which a scalar sum can produce.

    Returns `(phi_combined, head_bearing_deg)`.
    """
    phi_w = np.asarray(wind_factor(bed, wind_ms), dtype=np.float64)
    phi_s = np.asarray(slope_factor(bed, slope_tan), dtype=np.float64)
    phi_w = np.broadcast_to(phi_w, slope_tan.shape)

    wind_rad = np.radians(wind_to_bearing)
    slope_rad = np.radians(upslope_bearing)

    north = phi_w * np.cos(wind_rad) + phi_s * np.cos(slope_rad)
    east = phi_w * np.sin(wind_rad) + phi_s * np.sin(slope_rad)

    phi = np.hypot(north, east)
    bearing = np.degrees(np.arctan2(east, north)) % 360.0
    # With no wind and flat ground the direction is undefined, not zero;
    # anything will do because the ellipse is a circle there.
    bearing = np.where(phi > 1e-12, bearing, 0.0)
    return phi, bearing


def elliptical_rate(
    head_rate: np.ndarray,
    head_bearing: np.ndarray,
    length_breadth: np.ndarray,
    bearing: float,
) -> np.ndarray:
    """
    Spread rate along `bearing`, from an ellipse with the ignition at a focus.

    Richards (1990). At the head this returns `head_rate`; directly behind it
    returns the backing rate, which is `head_rate * (1-e)/(1+e)` and is what
    makes a fire's back edge creep while its head runs.

    Putting the ignition at the focus rather than the centre is the detail
    that matters: it is what makes the fire's origin sit near the back of the
    burned area, as real wind-driven fires do, instead of in the middle.
    """
    lb = np.maximum(length_breadth, 1.0)
    ecc = np.sqrt(np.maximum(lb * lb - 1.0, 0.0)) / lb
    delta = np.radians(bearing - head_bearing)
    denom = 1.0 - ecc * np.cos(delta)
    with np.errstate(divide="ignore", invalid="ignore"):
        rate = head_rate * (1.0 - ecc) / denom
    return np.nan_to_num(rate, nan=0.0, posinf=0.0, neginf=0.0)


def spread(
    bed: FuelBed,
    dem: np.ndarray,
    dx: float,
    ignition: np.ndarray,
    wind_ms: float = 0.0,
    wind_from_bearing: float = 0.0,
    duration_min: float = 480.0,
    barrier: np.ndarray = None,
    neighbours: int = 32,
) -> FireResult:
    """
    Solve arrival time across the landscape.

    `ignition` is a boolean mask of cells alight at t=0. `barrier` marks cells
    fire cannot enter — water, rock, a road, a completed fireline. `wind_from_bearing`
    follows the weather convention: the direction the wind comes *from*.

    The solve is exact for the graph it is posed on. Its approximations are
    the fuel model being uniform, the wind being steady, and spread happening
    only along the `neighbours` discrete bearings — not numerical error, which
    is why there is no tolerance to tune.
    """
    dem = np.asarray(dem, dtype=np.float64)
    ignition = np.asarray(ignition, dtype=bool)
    if dem.shape != ignition.shape:
        raise ValueError("dem and ignition must have the same shape")
    if dx <= 0:
        raise ValueError("dx must be positive")
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")
    if neighbours not in NEIGHBOURHOODS:
        raise ValueError(f"neighbours must be one of {sorted(NEIGHBOURHOODS)}")
    if not ignition.any():
        raise ValueError("no ignition cells")

    rows, cols = dem.shape
    slope_tan, upslope = terrain_slope(dem, dx)

    # Wind blows *toward* the reciprocal of the direction it comes from.
    wind_to = (float(wind_from_bearing) + 180.0) % 360.0
    phi, head_bearing = combine_wind_and_slope(
        bed, float(wind_ms), wind_to, slope_tan, upslope
    )

    head_rate = bed.r0_m_min * (1.0 + phi)
    lb = np.asarray(length_to_breadth(effective_wind_ms(bed, phi)), dtype=np.float64)

    burnable = np.full(dem.shape, bed.burnable, dtype=bool)
    if barrier is not None:
        barrier = np.asarray(barrier, dtype=bool)
        if barrier.shape != dem.shape:
            raise ValueError("barrier must have the same shape as dem")
        burnable &= ~barrier
    head_rate = np.where(burnable, head_rate, 0.0)

    offsets = NEIGHBOURHOODS[neighbours]
    crossings = [_intermediate_cells(dr, dc) for dr, dc in offsets]
    # Precompute the per-direction travel cost for every cell at once. The
    # Dijkstra loop below then does array lookups instead of trigonometry,
    # which is the difference between a solve measured in seconds and one
    # measured in minutes.
    costs = np.empty((len(offsets), rows, cols), dtype=np.float64)
    for k, (dr, dc) in enumerate(offsets):
        bearing = np.degrees(np.arctan2(dc, -dr)) % 360.0
        rate = elliptical_rate(head_rate, head_bearing, lb, bearing)
        distance = dx * np.hypot(dr, dc)
        with np.errstate(divide="ignore"):
            costs[k] = np.where(rate > MIN_SPREAD_M_MIN, distance / rate, np.inf)

    arrival = np.full(dem.shape, np.inf, dtype=np.float64)
    heap = []
    for r, c in zip(*np.nonzero(ignition)):
        arrival[r, c] = 0.0
        heapq.heappush(heap, (0.0, int(r), int(c)))

    while heap:
        t, r, c = heapq.heappop(heap)
        if t > arrival[r, c]:
            continue          # stale entry, already improved
        if t > duration_min:
            break             # the heap is ordered, so everything left is later
        for k, (dr, dc) in enumerate(offsets):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if not burnable[nr, nc]:
                continue
            # A multi-cell hop may not pass through ground that will not burn.
            blocked = False
            for mr, mc in crossings[k]:
                if not burnable[r + mr, c + mc]:
                    blocked = True
                    break
            if blocked:
                continue
            step = costs[k, r, c]
            if step == np.inf:
                continue
            nt = t + step
            if nt < arrival[nr, nc] and nt <= duration_min:
                arrival[nr, nc] = nt
                heapq.heappush(heap, (nt, nr, nc))

    # Fire behaviour reported at the front, where the fire actually was.
    # Byram's intensity needs the residence time of the flaming front, which
    # Anderson gives as 384/sigma minutes.
    residence_min = 384.0 / bed.sigma_char if bed.sigma_char > 0 else 0.0
    intensity_btu = bed.reaction_intensity * (head_rate / _FT_TO_M) * residence_min / 60.0
    intensity_kw_m = intensity_btu * BTU_FT_S_TO_KW_M
    flame_ft = _FLAME_A * np.power(np.maximum(intensity_btu, 0.0), _FLAME_B)
    flame_m = flame_ft * _FT_TO_M

    unburned = ~np.isfinite(arrival)
    for field in (intensity_kw_m, flame_m):
        field[unburned] = 0.0

    return FireResult(
        arrival_min=arrival.astype(np.float32),
        ros_m_min=head_rate.astype(np.float32),
        intensity_kw_m=intensity_kw_m.astype(np.float32),
        flame_length_m=flame_m.astype(np.float32),
        slope_tan=slope_tan.astype(np.float32),
        upslope_bearing=upslope.astype(np.float32),
        head_bearing=head_bearing.astype(np.float32),
        length_breadth=lb.astype(np.float32),
        burnable=burnable,
        duration_min=float(duration_min),
        dx=float(dx),
    )
