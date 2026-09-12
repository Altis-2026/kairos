"""
Rothermel surface fire spread rate, and the standard fuel models it runs on.

This is the point-behaviour half of the wildfire simulator: given a fuel bed,
its moisture, the midflame wind and the slope, how fast does a surface fire
front advance? Propagating that rate across a landscape is `fire_spread`.

The model
---------
Rothermel (1972), *A mathematical model for predicting fire spread in wildland
fuels*, INT-115, with the multi-size-class weighting and the dynamic live fuel
moisture of extinction from Albini (1976) as implemented in BEHAVE. Fuel
parameters are the thirteen fuel models of Anderson (1982), INT-122.

Everything inside is in Rothermel's original English units — loads in lb/ft²,
depths in ft, surface-area-to-volume in ft⁻¹, heat in BTU/lb — because every
coefficient in the published equations is tied to them, and converting the
constants instead of the inputs is how sign-off errors get introduced. The
conversion to SI happens once, at the boundary, in `spread_rate`.

What this is and is not
-----------------------
This predicts the spread of a *surface* fire in a *uniform, continuous* fuel
bed under *steady* wind. It has no crown fire, no spotting, no fire-atmosphere
coupling, and no fuel moisture dynamics — moisture is an input the user sets,
not something the model evolves. Real fire behaviour analysts run this model
knowing all of that; it is a screening tool, and treating its output as a
forecast of where a specific fire will go would be a serious misuse. That
caveat travels with every result the simulator produces.

The two-stage split
-------------------
`prepare` does everything that depends only on the fuel and its moisture, and
`spread_rate` applies wind and slope to the result. That is not just tidiness:
the landscape solver evaluates spread at every cell with a different slope and
wind, and the fuel-only half — which is the expensive half — is identical for
all of them.
"""

from dataclasses import dataclass

import numpy as np

#: Oven-dry particle density, lb/ft³ (Rothermel's value for woody fuels).
RHO_P = 32.0
#: Total mineral content, fraction.
ST = 0.0555
#: Effective (silica-free) mineral content, fraction.
SE = 0.010

#: 1 ton/acre in lb/ft². Fuel loads are published per acre; the equations
#: want per square foot.
TONS_ACRE_TO_LB_FT2 = 1.0 / 21.78
#: 1 ft/min in m/min.
FT_MIN_TO_M_MIN = 0.3048
#: 1 m/s in ft/min.
MS_TO_FT_MIN = 196.850394


@dataclass(frozen=True)
class FuelModel:
    """
    One standard fuel model.

    Loads are tons/acre and `sav_*` are ft⁻¹, exactly as published, so the
    table below can be checked against Anderson (1982) line by line without
    unit arithmetic. `depth_ft` is the fuel bed depth and `mx_dead` its dead
    fuel moisture of extinction.
    """

    id: str
    name: str
    group: str
    load_1h: float           # tons/acre
    load_10h: float
    load_100h: float
    load_live_herb: float
    load_live_woody: float
    depth_ft: float
    sav_1h: float            # ft^-1
    sav_live_herb: float
    sav_live_woody: float
    mx_dead: float           # fraction
    heat_btu_lb: float = 8000.0
    description: str = ""

    @property
    def has_live(self) -> bool:
        return (self.load_live_herb + self.load_live_woody) > 0.0


#: Surface-area-to-volume ratios for the coarser dead classes are fixed by
#: definition of the size class, not by the fuel model.
SAV_10H = 109.0
SAV_100H = 30.0


# The thirteen original fuel models. Values from Anderson (1982), Table 1.
FUEL_MODELS = {
    "gr1": FuelModel(
        "gr1", "Short grass", "Grass",
        0.74, 0.00, 0.00, 0.00, 0.00, 1.0, 3500, 0, 0, 0.12,
        description="Cured or nearly-cured short grass, under a foot deep. "
                    "Fast-moving, low-intensity surface fire.",
    ),
    "gr2": FuelModel(
        "gr2", "Timber grass and understory", "Grass",
        2.00, 1.00, 0.50, 0.50, 0.00, 1.0, 3000, 1500, 0, 0.15,
        description="Open pine or scrub oak with a grass understory carrying "
                    "the fire between the trees.",
    ),
    "gr3": FuelModel(
        "gr3", "Tall grass", "Grass",
        3.01, 0.00, 0.00, 0.00, 0.00, 2.5, 1500, 0, 0, 0.25,
        description="Dense, coarse grass around head height. The fastest "
                    "spreading of the thirteen.",
    ),
    "sh4": FuelModel(
        "sh4", "Chaparral", "Shrub",
        5.01, 4.01, 2.00, 0.00, 5.01, 6.0, 2000, 0, 1500, 0.20,
        description="Mature chaparral, six feet deep, with a heavy dead "
                    "component. Intense, difficult-to-control fire.",
    ),
    "sh5": FuelModel(
        "sh5", "Brush", "Shrub",
        1.00, 0.50, 0.00, 0.00, 2.00, 2.0, 2000, 0, 1500, 0.20,
        description="Young green brush with little dead material. The live "
                    "foliage slows the fire down markedly.",
    ),
    "sh6": FuelModel(
        "sh6", "Dormant brush, hardwood slash", "Shrub",
        1.50, 2.50, 2.00, 0.00, 0.00, 2.5, 1750, 0, 0, 0.25,
        description="Dormant or cured brush. Carries fire more readily than "
                    "the green brush of model sh5.",
    ),
    "sh7": FuelModel(
        "sh7", "Southern rough", "Shrub",
        1.13, 1.87, 1.50, 0.00, 0.37, 2.5, 1750, 0, 1500, 0.40,
        description="Palmetto-gallberry rough under a pine overstory. Burns "
                    "even at high moisture.",
    ),
    "tl8": FuelModel(
        "tl8", "Closed timber litter", "Timber litter",
        1.50, 1.00, 2.50, 0.00, 0.00, 0.2, 2000, 0, 0, 0.30,
        description="Compact needle litter under a closed canopy. Slow, "
                    "creeping surface fire.",
    ),
    "tl9": FuelModel(
        "tl9", "Hardwood litter", "Timber litter",
        2.92, 0.41, 0.15, 0.00, 0.00, 0.2, 2500, 0, 0, 0.25,
        description="Long-needle pine or hardwood leaf litter. Loose enough "
                    "to spread faster than model tl8.",
    ),
    "tu10": FuelModel(
        "tu10", "Timber litter and understory", "Timber-understory",
        3.01, 2.00, 5.01, 0.00, 2.00, 1.0, 2000, 0, 1500, 0.25,
        description="Timber with a shrub understory and heavy down material. "
                    "Torching and crowning likely in the real world — which "
                    "this surface model does not represent.",
    ),
    "sb11": FuelModel(
        "sb11", "Light logging slash", "Slash",
        1.50, 4.51, 5.51, 0.00, 0.00, 1.0, 1500, 0, 0, 0.15,
        description="Light partially-cured slash from a light thinning.",
    ),
    "sb12": FuelModel(
        "sb12", "Medium logging slash", "Slash",
        4.01, 14.03, 16.53, 0.00, 0.00, 2.3, 1500, 0, 0, 0.20,
        description="Medium slash, heavy loading and continuous.",
    ),
    "sb13": FuelModel(
        "sb13", "Heavy logging slash", "Slash",
        7.01, 23.04, 28.05, 0.00, 0.00, 3.0, 1600, 0, 0, 0.25,
        description="Heavy clearcut slash. Very high intensity, long "
                    "residence time.",
    ),
}

#: Default dead fuel moistures by size class, fraction. These are the dry,
#: fire-season values a screening run should default to; they are an
#: assumption the user can and should override.
DEFAULT_MOISTURE = {
    "dead_1h": 0.06,
    "dead_10h": 0.07,
    "dead_100h": 0.08,
    "live": 1.00,
}


@dataclass(frozen=True)
class FuelBed:
    """
    A fuel model with its moisture resolved into Rothermel's intermediates.

    Every field is wind- and slope-independent, so a landscape solve computes
    this once and reuses it at every cell. `r0_m_min` is the no-wind, no-slope
    spread rate — the number to compare against published fuel model tables.
    """

    fuel: FuelModel
    reaction_intensity: float    # BTU/ft²/min
    propagating_flux: float      # dimensionless
    heat_sink: float             # BTU/ft³
    sigma_char: float            # ft^-1
    beta_ratio: float            # beta / beta_op
    wind_c: float
    wind_b: float
    wind_e: float
    slope_coeff: float           # phi_s = slope_coeff * tan(slope)^2
    max_wind_ft_min: float       # effective wind speed limit
    r0_m_min: float

    @property
    def burnable(self) -> bool:
        return self.heat_sink > 0.0 and self.reaction_intensity > 0.0


def _damping(moisture: float, mx: float) -> float:
    """Rothermel's moisture damping coefficient, clamped to [0, 1]."""
    if mx <= 0.0:
        return 0.0
    r = moisture / mx
    if r >= 1.0:
        # At or past the moisture of extinction the fuel does not carry fire.
        # The cubic below evaluates to zero at r = 1 in exact arithmetic but
        # leaves a ~1e-16 residue in floating point, which propagates into a
        # nonzero spread rate. Returning exactly zero here means "will not
        # burn" is representable, rather than merely very small.
        return 0.0
    eta = 1.0 - 2.59 * r + 5.11 * r * r - 3.52 * r * r * r
    return float(min(max(eta, 0.0), 1.0))


def prepare(fuel: FuelModel, moisture: dict = None) -> FuelBed:
    """
    Resolve a fuel model and its moisture into wind/slope-independent terms.

    `moisture` maps `dead_1h`, `dead_10h`, `dead_100h` and `live` to fractions
    (0.06 is 6%). Missing keys fall back to `DEFAULT_MOISTURE`.

    The size-class weighting follows Rothermel: within each category classes
    are weighted by surface area, and the two categories are then weighted by
    their share of the total surface area. Weighting by *load* instead — an
    easy and tempting simplification — would let a small mass of fine fuel be
    swamped by coarse material that in reality barely participates in the
    spreading front.
    """
    m = dict(DEFAULT_MOISTURE)
    m.update(moisture or {})

    # (load lb/ft², sav ft^-1, moisture fraction) per size class.
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

    # Net (mineral-free) load and mean moisture, per category.
    wn_dead = sum(f * c[0] for f, c in zip(f_dead, dead)) * (1.0 - ST)
    wn_live = sum(f * c[0] for f, c in zip(f_live, live)) * (1.0 - ST)
    mf_dead = sum(f * c[2] for f, c in zip(f_dead, dead))
    mf_live = sum(f * c[2] for f, c in zip(f_live, live))

    # Live fuel moisture of extinction is not a constant: it falls as the
    # dead fuel dries out, which is what lets a fire run through green brush
    # on a bad day and not on an ordinary one (Albini 1976).
    mx_live = fuel.mx_dead
    if live and dead:
        heat_dead = sum(w * np.exp(-138.0 / s) for w, s, _ in dead)
        heat_live = sum(w * np.exp(-500.0 / s) for w, s, _ in live)
        if heat_live > 0.0:
            ratio = heat_dead / heat_live
            fine_dead_mf = (
                sum(w * mo * np.exp(-138.0 / s) for w, s, mo in dead) / heat_dead
                if heat_dead > 0.0 else 0.0
            )
            mx_live = max(
                fuel.mx_dead,
                2.9 * ratio * (1.0 - fine_dead_mf / fuel.mx_dead) - 0.226,
            )

    rho_b = load_total / fuel.depth_ft            # bulk density, lb/ft³
    beta = rho_b / RHO_P                          # packing ratio
    beta_op = 3.348 * sigma_char ** -0.8189       # optimum packing ratio
    beta_ratio = beta / beta_op

    a_exp = 133.0 * sigma_char ** -0.7913
    gamma_max = sigma_char ** 1.5 / (495.0 + 0.0594 * sigma_char ** 1.5)
    gamma = gamma_max * beta_ratio ** a_exp * np.exp(a_exp * (1.0 - beta_ratio))

    eta_s = min(0.174 * SE ** -0.19, 1.0)
    ir = float(gamma * fuel.heat_btu_lb * eta_s * (
        cat_dead * wn_dead * _damping(mf_dead, fuel.mx_dead)
        + cat_live * wn_live * _damping(mf_live, mx_live)
    ))

    xi = float(
        np.exp((0.792 + 0.681 * np.sqrt(sigma_char)) * (beta + 0.1))
        / (192.0 + 0.2595 * sigma_char)
    )

    # Heat sink: the energy needed to bring the fuel ahead of the front to
    # ignition. Each size class heats at its own rate, hence the same
    # surface-area weighting again rather than a single characteristic value.
    def sink(classes, fs):
        return sum(
            f * np.exp(-138.0 / c[1]) * (250.0 + 1116.0 * c[2])
            for f, c in zip(fs, classes)
        )

    heat_sink = float(rho_b * (cat_dead * sink(dead, f_dead)
                               + cat_live * sink(live, f_live)))

    wind_c = float(7.47 * np.exp(-0.133 * sigma_char ** 0.55))
    wind_b = float(0.02526 * sigma_char ** 0.54)
    wind_e = float(0.715 * np.exp(-3.59e-4 * sigma_char))
    slope_coeff = float(5.275 * beta ** -0.3)

    # Rothermel's effective wind speed limit. Past it the equations
    # extrapolate into a regime they were never fitted in and spread rate
    # grows without bound, so wind is capped rather than trusted.
    max_wind = 0.9 * ir

    r0 = (ir * xi / heat_sink * FT_MIN_TO_M_MIN) if heat_sink > 0 else 0.0

    return FuelBed(
        fuel=fuel, reaction_intensity=ir, propagating_flux=xi,
        heat_sink=heat_sink, sigma_char=float(sigma_char),
        beta_ratio=float(beta_ratio), wind_c=wind_c, wind_b=wind_b,
        wind_e=wind_e, slope_coeff=slope_coeff, max_wind_ft_min=max_wind,
        r0_m_min=float(r0),
    )


def wind_factor(bed: FuelBed, wind_ms):
    """
    Rothermel's wind coefficient for a midflame wind speed in m/s.

    Note *midflame*: this is the wind at the flame, not the 10 m or 20 ft
    weather-station wind, which is roughly two to four times larger over open
    fuel and far larger under a canopy. Passing a forecast wind straight in
    here overpredicts spread badly, so the simulator applies a reduction
    factor before it gets this far.
    """
    if not bed.burnable:
        return np.zeros_like(np.asarray(wind_ms, dtype=float))
    u = np.asarray(wind_ms, dtype=float) * MS_TO_FT_MIN
    u = np.clip(u, 0.0, bed.max_wind_ft_min)
    return bed.wind_c * u ** bed.wind_b * bed.beta_ratio ** -bed.wind_e


def slope_factor(bed: FuelBed, slope_tan):
    """Rothermel's slope coefficient for a rise-over-run slope."""
    if not bed.burnable:
        return np.zeros_like(np.asarray(slope_tan, dtype=float))
    s = np.asarray(slope_tan, dtype=float)
    return bed.slope_coeff * s * s


def spread_rate(bed: FuelBed, wind_ms=0.0, slope_tan=0.0):
    """
    Head-fire spread rate in m/min. Accepts scalars or arrays.

    This is the maximum rate, in the direction the combined wind and slope
    vector points. Spread in every other direction is slower, and working out
    how much slower is the job of the elliptical geometry in `fire_spread` —
    keeping the two apart is what stops a directional assumption from being
    baked into the point model.
    """
    if not bed.burnable:
        return np.zeros_like(np.asarray(wind_ms, dtype=float)
                             + np.asarray(slope_tan, dtype=float))
    phi = 1.0 + wind_factor(bed, wind_ms) + slope_factor(bed, slope_tan)
    r_ft_min = bed.reaction_intensity * bed.propagating_flux * phi / bed.heat_sink
    return r_ft_min * FT_MIN_TO_M_MIN


def length_to_breadth(wind_ms) -> float:
    """
    Ellipse length-to-breadth ratio for a midflame wind speed, in m/s.

    Anderson (1983): a wind-driven fire's perimeter is well approximated by an
    ellipse whose elongation grows with wind. At zero wind the ratio is 1 — a
    circle — which is the behaviour a fire on flat ground in still air
    actually shows.
    """
    u_mi_h = np.asarray(wind_ms, dtype=float) * 2.236936
    return 1.0 + 0.25 * u_mi_h
