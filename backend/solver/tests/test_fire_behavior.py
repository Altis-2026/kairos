import numpy as np
import pytest

from solver.fire_behavior import (
    DEFAULT_MOISTURE,
    FUEL_MODELS,
    length_to_breadth,
    prepare,
    slope_factor,
    spread_rate,
    wind_factor,
)

WIND_5MPH_MS = 5.0 * 0.44704
CH_H_TO_M_MIN = 20.1168 / 60.0

DRY_DEAD = {"dead_1h": 0.08, "dead_10h": 0.08, "dead_100h": 0.08, "live": 1.00}


def ch_per_hour(bed, wind_ms=WIND_5MPH_MS, slope=0.0) -> float:
    return float(spread_rate(bed, wind_ms, slope)) / CH_H_TO_M_MIN


PUBLISHED_BED = {
    "gr1": (3500, 0.00106),
    "gr2": (2784, 0.00574),
    "sh4": (1739, 0.00383),
    "sh5": (1683, 0.00251),
    "tl8": (1889, 0.03587),
    "tu10": (1765, 0.01725),
}


@pytest.mark.parametrize("key,expected", PUBLISHED_BED.items())
def test_bed_properties_match_published_table(key, expected):
    sigma_pub, beta_pub = expected
    bed = prepare(FUEL_MODELS[key], DRY_DEAD)
    fuel = bed.fuel
    total_load = (
        fuel.load_1h + fuel.load_10h + fuel.load_100h + fuel.load_live_herb + fuel.load_live_woody
    ) / 21.78
    beta = total_load / fuel.depth_ft / 32.0

    assert bed.sigma_char == pytest.approx(sigma_pub, rel=0.005)
    assert beta == pytest.approx(beta_pub, rel=0.005)


PUBLISHED_ROS_DEAD_ONLY = {
    "gr1": 78.0,
    "gr3": 104.0,
    "sh6": 32.0,
    "tl8": 1.6,
    "tl9": 7.5,
    "sb11": 6.0,
    "sb12": 13.0,
    "sb13": 13.5,
}


@pytest.mark.parametrize("key,published", PUBLISHED_ROS_DEAD_ONLY.items())
def test_spread_rate_matches_published_table(key, published):
    bed = prepare(FUEL_MODELS[key], DRY_DEAD)
    assert ch_per_hour(bed) == pytest.approx(published, rel=0.15)


@pytest.mark.parametrize(
    "key,published",
    [
        ("sh4", 75.0),
        ("sh5", 18.0),
        ("sh7", 20.0),
        ("tu10", 7.9),
    ],
)
def test_live_fuel_models_bracket_published(key, published):
    fuel = FUEL_MODELS[key]
    cured = prepare(fuel, {**DRY_DEAD, "live": 0.30})
    green = prepare(fuel, {**DRY_DEAD, "live": 1.50})

    assert ch_per_hour(green) < published < ch_per_hour(cured) * 1.2
    assert ch_per_hour(cured) > ch_per_hour(green)


def test_grass_outruns_closed_timber_litter():
    grass = prepare(FUEL_MODELS["gr1"], DRY_DEAD)
    litter = prepare(FUEL_MODELS["tl8"], DRY_DEAD)
    assert spread_rate(grass, WIND_5MPH_MS) > 10 * spread_rate(litter, WIND_5MPH_MS)


def test_spread_rate_increases_with_wind_and_slope():
    bed = prepare(FUEL_MODELS["gr2"], DRY_DEAD)
    winds = np.array([0.0, 1.0, 2.0, 4.0])
    rates = spread_rate(bed, winds, 0.0)
    assert np.all(np.diff(rates) > 0)

    slopes = np.array([0.0, 0.1, 0.3, 0.6])
    on_slope = spread_rate(bed, 0.0, slopes)
    assert np.all(np.diff(on_slope) > 0)


def test_no_wind_no_slope_rate_is_the_baseline():
    for fuel in FUEL_MODELS.values():
        bed = prepare(fuel, DRY_DEAD)
        assert float(spread_rate(bed, 0.0, 0.0)) == pytest.approx(bed.r0_m_min)


def test_slope_is_direction_agnostic():
    bed = prepare(FUEL_MODELS["gr1"], DRY_DEAD)
    assert slope_factor(bed, 0.3) == pytest.approx(slope_factor(bed, -0.3))


def test_fire_goes_out_at_the_moisture_of_extinction():
    fuel = FUEL_MODELS["gr1"]
    at_mx = {"dead_1h": fuel.mx_dead, "dead_10h": fuel.mx_dead, "dead_100h": fuel.mx_dead, "live": 1.0}
    assert float(spread_rate(prepare(fuel, at_mx), WIND_5MPH_MS)) == 0.0

    beyond = {k: v * 2 for k, v in at_mx.items()}
    assert float(spread_rate(prepare(fuel, beyond), WIND_5MPH_MS)) == 0.0


def test_spread_rate_falls_monotonically_with_dead_moisture():
    fuel = FUEL_MODELS["gr3"]
    rates = [
        float(
            spread_rate(
                prepare(fuel, {**DRY_DEAD, "dead_1h": mf, "dead_10h": mf, "dead_100h": mf}), WIND_5MPH_MS
            )
        )
        for mf in (0.03, 0.08, 0.15, 0.22)
    ]
    assert rates == sorted(rates, reverse=True)


def test_wind_is_capped_at_the_effective_wind_limit():
    bed = prepare(FUEL_MODELS["gr1"], DRY_DEAD)
    gale = wind_factor(bed, 40.0)
    hurricane = wind_factor(bed, 90.0)
    assert float(gale) == pytest.approx(float(hurricane))


def test_live_moisture_of_extinction_rises_with_wetter_dead_fuel():
    fuel = FUEL_MODELS["sh4"]

    def drying_response(model):
        dry = prepare(model, {"dead_1h": 0.04, "dead_10h": 0.04, "dead_100h": 0.04, "live": 1.0})
        damp = prepare(model, {"dead_1h": 0.15, "dead_10h": 0.15, "dead_100h": 0.15, "live": 1.0})
        return float(spread_rate(dry, WIND_5MPH_MS) / spread_rate(damp, WIND_5MPH_MS))

    dead_only = type(fuel)(**{**fuel.__dict__, "load_live_woody": 0.0})
    assert drying_response(fuel) > drying_response(dead_only)


def test_herbaceous_load_is_static_not_cured():
    fuel = FUEL_MODELS["gr2"]
    static = ch_per_hour(prepare(fuel, DRY_DEAD))
    cured = type(fuel)(
        **{**fuel.__dict__, "load_1h": fuel.load_1h + fuel.load_live_herb, "load_live_herb": 0.0}
    )
    transferred = ch_per_hour(prepare(cured, DRY_DEAD))

    assert static == pytest.approx(22.3, rel=0.1)
    assert transferred == pytest.approx(42.6, rel=0.1)
    assert static < 35.0 < transferred


def test_arrays_and_scalars_agree():
    bed = prepare(FUEL_MODELS["sh6"], DRY_DEAD)
    winds = np.array([0.5, 1.5, 3.0])
    slopes = np.array([0.0, 0.2, 0.45])
    vector = spread_rate(bed, winds, slopes)
    scalar = [float(spread_rate(bed, float(w), float(s))) for w, s in zip(winds, slopes)]
    assert np.allclose(vector, scalar)


def test_nonburnable_bed_never_spreads():
    fuel = FUEL_MODELS["gr1"]
    barren = type(fuel)(
        id="barren",
        name="Barren",
        group="None",
        load_1h=0.0,
        load_10h=0.0,
        load_100h=0.0,
        load_live_herb=0.0,
        load_live_woody=0.0,
        depth_ft=1.0,
        sav_1h=3500,
        sav_live_herb=0,
        sav_live_woody=0,
        mx_dead=0.12,
    )
    bed = prepare(barren)
    assert not bed.burnable
    assert float(spread_rate(bed, 10.0, 0.5)) == 0.0
    assert np.all(wind_factor(bed, np.array([1.0, 5.0])) == 0.0)


def test_length_to_breadth_is_one_in_still_air():
    assert length_to_breadth(0.0) == pytest.approx(1.0)
    assert length_to_breadth(5.0) > length_to_breadth(2.0) > 1.0


def test_default_moisture_is_a_dry_fire_season_assumption():
    assert DEFAULT_MOISTURE["dead_1h"] <= 0.08
    assert DEFAULT_MOISTURE["live"] >= 0.5


def test_every_fuel_model_is_self_consistent():
    for key, fuel in FUEL_MODELS.items():
        assert fuel.id == key
        assert fuel.depth_ft > 0
        assert fuel.sav_1h > 0
        assert 0 < fuel.mx_dead <= 0.5
        assert fuel.description
        bed = prepare(fuel, DRY_DEAD)
        assert bed.burnable, key
        assert bed.r0_m_min > 0, key
