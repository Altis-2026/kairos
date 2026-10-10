from dataclasses import dataclass

import numpy as np

RHO_P = 32.0
ST = 0.0555
SE = 0.010

TONS_ACRE_TO_LB_FT2 = 1.0 / 21.78
FT_MIN_TO_M_MIN = 0.3048
MS_TO_FT_MIN = 196.850394


@dataclass(frozen=True)
class FuelModel:
    id: str
    name: str
    group: str
    load_1h: float
    load_10h: float
    load_100h: float
    load_live_herb: float
    load_live_woody: float
    depth_ft: float
    sav_1h: float
    sav_live_herb: float
    sav_live_woody: float
    mx_dead: float
    heat_btu_lb: float = 8000.0
    description: str = ""

    @property
    def has_live(self) -> bool:
        return (self.load_live_herb + self.load_live_woody) > 0.0


SAV_10H = 109.0
SAV_100H = 30.0


FUEL_MODELS = {
    "gr1": FuelModel(
        "gr1",
        "Short grass",
        "Grass",
        0.74,
        0.00,
        0.00,
        0.00,
        0.00,
        1.0,
        3500,
        0,
        0,
        0.12,
        description="Cured or nearly-cured short grass, under a foot deep. "
        "Fast-moving, low-intensity surface fire.",
    ),
    "gr2": FuelModel(
        "gr2",
        "Timber grass and understory",
        "Grass",
        2.00,
        1.00,
        0.50,
        0.50,
        0.00,
        1.0,
        3000,
        1500,
        0,
        0.15,
        description="Open pine or scrub oak with a grass understory carrying the fire between the trees.",
    ),
    "gr3": FuelModel(
        "gr3",
        "Tall grass",
        "Grass",
        3.01,
        0.00,
        0.00,
        0.00,
        0.00,
        2.5,
        1500,
        0,
        0,
        0.25,
        description="Dense, coarse grass around head height. The fastest spreading of the thirteen.",
    ),
    "sh4": FuelModel(
        "sh4",
        "Chaparral",
        "Shrub",
        5.01,
        4.01,
        2.00,
        0.00,
        5.01,
        6.0,
        2000,
        0,
        1500,
        0.20,
        description="Mature chaparral, six feet deep, with a heavy dead "
        "component. Intense, difficult-to-control fire.",
    ),
    "sh5": FuelModel(
        "sh5",
        "Brush",
        "Shrub",
        1.00,
        0.50,
        0.00,
        0.00,
        2.00,
        2.0,
        2000,
        0,
        1500,
        0.20,
        description="Young green brush with little dead material. The live "
        "foliage slows the fire down markedly.",
    ),
    "sh6": FuelModel(
        "sh6",
        "Dormant brush, hardwood slash",
        "Shrub",
        1.50,
        2.50,
        2.00,
        0.00,
        0.00,
        2.5,
        1750,
        0,
        0,
        0.25,
        description="Dormant or cured brush. Carries fire more readily than the green brush of model sh5.",
    ),
    "sh7": FuelModel(
        "sh7",
        "Southern rough",
        "Shrub",
        1.13,
        1.87,
        1.50,
        0.00,
        0.37,
        2.5,
        1750,
        0,
        1500,
        0.40,
        description="Palmetto-gallberry rough under a pine overstory. Burns even at high moisture.",
    ),
    "tl8": FuelModel(
        "tl8",
        "Closed timber litter",
        "Timber litter",
        1.50,
        1.00,
        2.50,
        0.00,
        0.00,
        0.2,
        2000,
        0,
        0,
        0.30,
        description="Compact needle litter under a closed canopy. Slow, creeping surface fire.",
    ),
    "tl9": FuelModel(
        "tl9",
        "Hardwood litter",
        "Timber litter",
        2.92,
        0.41,
        0.15,
        0.00,
        0.00,
        0.2,
        2500,
        0,
        0,
        0.25,
        description="Long-needle pine or hardwood leaf litter. Loose enough to spread faster than model tl8.",
    ),
    "tu10": FuelModel(
        "tu10",
        "Timber litter and understory",
        "Timber-understory",
        3.01,
        2.00,
        5.01,
        0.00,
        2.00,
        1.0,
        2000,
        0,
        1500,
        0.25,
        description="Timber with a shrub understory and heavy down material. "
        "Torching and crowning likely in the real world, which "
        "this surface model does not represent.",
    ),
    "sb11": FuelModel(
        "sb11",
        "Light logging slash",
        "Slash",
        1.50,
        4.51,
        5.51,
        0.00,
        0.00,
        1.0,
        1500,
        0,
        0,
        0.15,
        description="Light partially-cured slash from a light thinning.",
    ),
    "sb12": FuelModel(
        "sb12",
        "Medium logging slash",
        "Slash",
        4.01,
        14.03,
        16.53,
        0.00,
        0.00,
        2.3,
        1500,
        0,
        0,
        0.20,
        description="Medium slash, heavy loading and continuous.",
    ),
    "sb13": FuelModel(
        "sb13",
        "Heavy logging slash",
        "Slash",
        7.01,
        23.04,
        28.05,
        0.00,
        0.00,
        3.0,
        1600,
        0,
        0,
        0.25,
        description="Heavy clearcut slash. Very high intensity, long residence time.",
    ),
}

DEFAULT_MOISTURE = {
    "dead_1h": 0.06,
    "dead_10h": 0.07,
    "dead_100h": 0.08,
    "live": 1.00,
}


@dataclass(frozen=True)
class FuelBed:
    fuel: FuelModel
    reaction_intensity: float
    propagating_flux: float
    heat_sink: float
    sigma_char: float
    beta_ratio: float
    wind_c: float
    wind_b: float
    wind_e: float
    slope_coeff: float
    max_wind_ft_min: float
    r0_m_min: float

    @property
    def burnable(self) -> bool:
        return self.heat_sink > 0.0 and self.reaction_intensity > 0.0


def _damping(moisture: float, mx: float) -> float:
    if mx <= 0.0:
        return 0.0
    r = moisture / mx
    if r >= 1.0:
        return 0.0
    eta = 1.0 - 2.59 * r + 5.11 * r * r - 3.52 * r * r * r
    return float(min(max(eta, 0.0), 1.0))


def prepare(fuel: FuelModel, moisture: dict = None) -> FuelBed:
    m = dict(DEFAULT_MOISTURE)
    m.update(moisture or {})

    dead = [
        (fuel.load_1h * TONS_ACRE_TO_LB_FT2, fuel.sav_1h, m["dead_1h"]),
        (fuel.load_10h * TONS_ACRE_TO_LB_FT2, SAV_10H, m["dead_10h"]),
        (fuel.load_100h * TONS_ACRE_TO_LB_FT2, SAV_100H, m["dead_100h"]),
    ]
    live = [
        (fuel.load_live_herb * TONS_ACRE_TO_LB_FT2, fuel.sav_live_herb, m["live"]),
        (fuel.load_live_woody * TONS_ACRE_TO_LB_FT2, fuel.sav_live_woody, m["live"]),
    ]
    dead = [c for c in dead if c[0] > 0.0 and c[1] > 0.0]
    live = [c for c in live if c[0] > 0.0 and c[1] > 0.0]

    area_dead = sum(w * s / RHO_P for w, s, _ in dead)
    area_live = sum(w * s / RHO_P for w, s, _ in live)
    area_total = area_dead + area_live
    load_total = sum(w for w, _, _ in dead) + sum(w for w, _, _ in live)

    if area_total <= 0.0 or load_total <= 0.0 or fuel.depth_ft <= 0.0:
        return FuelBed(fuel, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0.0)

    def weights(classes, area):
        return [(w * s / RHO_P) / area for w, s, _ in classes] if area > 0 else []

    f_dead = weights(dead, area_dead)
    f_live = weights(live, area_live)
    cat_dead = area_dead / area_total
    cat_live = area_live / area_total

    sigma_dead = sum(f * c[1] for f, c in zip(f_dead, dead))
    sigma_live = sum(f * c[1] for f, c in zip(f_live, live))
    sigma_char = cat_dead * sigma_dead + cat_live * sigma_live

    wn_dead = sum(f * c[0] for f, c in zip(f_dead, dead)) * (1.0 - ST)
    wn_live = sum(f * c[0] for f, c in zip(f_live, live)) * (1.0 - ST)
    mf_dead = sum(f * c[2] for f, c in zip(f_dead, dead))
    mf_live = sum(f * c[2] for f, c in zip(f_live, live))

    mx_live = fuel.mx_dead
    if live and dead:
        heat_dead = sum(w * np.exp(-138.0 / s) for w, s, _ in dead)
        heat_live = sum(w * np.exp(-500.0 / s) for w, s, _ in live)
        if heat_live > 0.0:
            ratio = heat_dead / heat_live
            fine_dead_mf = (
                sum(w * mo * np.exp(-138.0 / s) for w, s, mo in dead) / heat_dead if heat_dead > 0.0 else 0.0
            )
            mx_live = max(
                fuel.mx_dead,
                2.9 * ratio * (1.0 - fine_dead_mf / fuel.mx_dead) - 0.226,
            )

    rho_b = load_total / fuel.depth_ft
    beta = rho_b / RHO_P
    beta_op = 3.348 * sigma_char**-0.8189
    beta_ratio = beta / beta_op

    a_exp = 133.0 * sigma_char**-0.7913
    gamma_max = sigma_char**1.5 / (495.0 + 0.0594 * sigma_char**1.5)
    gamma = gamma_max * beta_ratio**a_exp * np.exp(a_exp * (1.0 - beta_ratio))

    eta_s = min(0.174 * SE**-0.19, 1.0)
    ir = float(
        gamma
        * fuel.heat_btu_lb
        * eta_s
        * (
            cat_dead * wn_dead * _damping(mf_dead, fuel.mx_dead)
            + cat_live * wn_live * _damping(mf_live, mx_live)
        )
    )

    xi = float(np.exp((0.792 + 0.681 * np.sqrt(sigma_char)) * (beta + 0.1)) / (192.0 + 0.2595 * sigma_char))

    def sink(classes, fs):
        return sum(f * np.exp(-138.0 / c[1]) * (250.0 + 1116.0 * c[2]) for f, c in zip(fs, classes))

    heat_sink = float(rho_b * (cat_dead * sink(dead, f_dead) + cat_live * sink(live, f_live)))

    wind_c = float(7.47 * np.exp(-0.133 * sigma_char**0.55))
    wind_b = float(0.02526 * sigma_char**0.54)
    wind_e = float(0.715 * np.exp(-3.59e-4 * sigma_char))
    slope_coeff = float(5.275 * beta**-0.3)

    max_wind = 0.9 * ir

    r0 = (ir * xi / heat_sink * FT_MIN_TO_M_MIN) if heat_sink > 0 else 0.0

    return FuelBed(
        fuel=fuel,
        reaction_intensity=ir,
        propagating_flux=xi,
        heat_sink=heat_sink,
        sigma_char=float(sigma_char),
        beta_ratio=float(beta_ratio),
        wind_c=wind_c,
        wind_b=wind_b,
        wind_e=wind_e,
        slope_coeff=slope_coeff,
        max_wind_ft_min=max_wind,
        r0_m_min=float(r0),
    )


def wind_factor(bed: FuelBed, wind_ms):
    if not bed.burnable:
        return np.zeros_like(np.asarray(wind_ms, dtype=float))
    u = np.asarray(wind_ms, dtype=float) * MS_TO_FT_MIN
    u = np.clip(u, 0.0, bed.max_wind_ft_min)
    return bed.wind_c * u**bed.wind_b * bed.beta_ratio**-bed.wind_e


def slope_factor(bed: FuelBed, slope_tan):
    if not bed.burnable:
        return np.zeros_like(np.asarray(slope_tan, dtype=float))
    s = np.asarray(slope_tan, dtype=float)
    return bed.slope_coeff * s * s


def spread_rate(bed: FuelBed, wind_ms=0.0, slope_tan=0.0):
    if not bed.burnable:
        return np.zeros_like(np.asarray(wind_ms, dtype=float) + np.asarray(slope_tan, dtype=float))
    phi = 1.0 + wind_factor(bed, wind_ms) + slope_factor(bed, slope_tan)
    r_ft_min = bed.reaction_intensity * bed.propagating_flux * phi / bed.heat_sink
    return r_ft_min * FT_MIN_TO_M_MIN


def length_to_breadth(wind_ms) -> float:
    u_mi_h = np.asarray(wind_ms, dtype=float) * 2.236936
    return 1.0 + 0.25 * u_mi_h
