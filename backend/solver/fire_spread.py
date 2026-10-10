import heapq
from dataclasses import dataclass

import numpy as np

from solver.fire_behavior import (
    MS_TO_FT_MIN,
    FuelBed,
    length_to_breadth,
    slope_factor,
    wind_factor,
)

NEIGHBOURHOODS = {
    8: [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)],
    16: [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
        (-2, -1),
        (-2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
        (2, -1),
        (2, 1),
    ],
    32: [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
        (-2, -1),
        (-2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
        (2, -1),
        (2, 1),
        (-3, -1),
        (-3, 1),
        (-1, -3),
        (-1, 3),
        (1, -3),
        (1, 3),
        (3, -1),
        (3, 1),
        (-3, -2),
        (-3, 2),
        (-2, -3),
        (-2, 3),
        (2, -3),
        (2, 3),
        (3, -2),
        (3, 2),
    ],
}


def _intermediate_cells(dr: int, dc: int) -> tuple:
    steps = 4 * max(abs(dr), abs(dc))
    cells = []
    for i in range(1, steps):
        t = i / steps
        cell = (int(round(dr * t)), int(round(dc * t)))
        if cell not in cells and cell != (0, 0) and cell != (dr, dc):
            cells.append(cell)
    return tuple(cells)


MIN_SPREAD_M_MIN = 1e-3

_FLAME_A = 0.45
_FLAME_B = 0.46
BTU_FT_S_TO_KW_M = 3.46414
_FT_TO_M = 0.3048


@dataclass
class FireResult:
    arrival_min: np.ndarray
    ros_m_min: np.ndarray
    intensity_kw_m: np.ndarray
    flame_length_m: np.ndarray
    slope_tan: np.ndarray
    upslope_bearing: np.ndarray
    head_bearing: np.ndarray
    length_breadth: np.ndarray
    burnable: np.ndarray
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
    if dem.ndim != 2:
        raise ValueError("dem must be 2-D")
    d_row, d_col = np.gradient(dem.astype(np.float64), dx)
    g_north = -d_row
    g_east = d_col

    slope = np.hypot(g_north, g_east)
    bearing = np.degrees(np.arctan2(g_east, g_north)) % 360.0
    return slope.astype(np.float64), bearing.astype(np.float64)


def effective_wind_ms(bed: FuelBed, phi_combined: np.ndarray) -> np.ndarray:
    if not bed.burnable or bed.wind_b == 0:
        return np.zeros_like(phi_combined)
    base = bed.wind_c * bed.beta_ratio**-bed.wind_e
    with np.errstate(divide="ignore", invalid="ignore"):
        u_ft_min = np.where(phi_combined > 0, (np.maximum(phi_combined, 0) / base) ** (1.0 / bed.wind_b), 0.0)
    u_ft_min = np.clip(np.nan_to_num(u_ft_min), 0.0, bed.max_wind_ft_min)
    return u_ft_min / MS_TO_FT_MIN


def combine_wind_and_slope(
    bed: FuelBed,
    wind_ms: float,
    wind_to_bearing: float,
    slope_tan: np.ndarray,
    upslope_bearing: np.ndarray,
) -> tuple:
    phi_w = np.asarray(wind_factor(bed, wind_ms), dtype=np.float64)
    phi_s = np.asarray(slope_factor(bed, slope_tan), dtype=np.float64)
    phi_w = np.broadcast_to(phi_w, slope_tan.shape)

    wind_rad = np.radians(wind_to_bearing)
    slope_rad = np.radians(upslope_bearing)

    north = phi_w * np.cos(wind_rad) + phi_s * np.cos(slope_rad)
    east = phi_w * np.sin(wind_rad) + phi_s * np.sin(slope_rad)

    phi = np.hypot(north, east)
    bearing = np.degrees(np.arctan2(east, north)) % 360.0
    bearing = np.where(phi > 1e-12, bearing, 0.0)
    return phi, bearing


def elliptical_rate(
    head_rate: np.ndarray,
    head_bearing: np.ndarray,
    length_breadth: np.ndarray,
    bearing: float,
) -> np.ndarray:
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

    wind_to = (float(wind_from_bearing) + 180.0) % 360.0
    phi, head_bearing = combine_wind_and_slope(bed, float(wind_ms), wind_to, slope_tan, upslope)

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
            continue
        if t > duration_min:
            break
        for k, (dr, dc) in enumerate(offsets):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if not burnable[nr, nc]:
                continue
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
