"""
Tests for the wildfire simulation orchestration layer.

The DEM provider is injectable, so the whole pipeline — parameter resolution,
ignition placement, solve, encode, result envelope — runs offline against
synthetic terrain with no Earth Engine credentials.
"""

import numpy as np
import pytest

from solver import fire_presets
from solver.fire_sim import (
    DISCLOSURE,
    MAX_CELLS,
    decode_fire,
    ignition_mask_for,
    resolve_params,
    simulate_fire,
)

BBOX = [-118.82, 34.06, -118.66, 34.14]


class FakeTile:
    def __init__(self, dem, dx):
        self.dem = dem
        self.dx = dx

    def as_dict(self):
        return {"scale_m": self.dx, "grid": list(self.dem.shape)}


def ridged(n=161, dx=30.0):
    y, x = np.mgrid[0:n, 0:n]
    dem = 260 * np.sin(x / 34.0) * np.cos(y / 47.0) + 1.1 * x + 0.7 * y
    return lambda bbox, scale: FakeTile(dem.astype(float), dx)


def run(params=None, provider=None, bbox=None):
    return simulate_fire(
        bbox or BBOX, "2026-08-01", "2026-08-02",
        params if params is not None else {"scene": "malibu_chaparral"},
        dem_provider=provider or ridged(),
    )


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------

def test_scene_supplies_defaults_and_user_values_win():
    scene = fire_presets.get_scene("front_range_grass")
    p = resolve_params({"scene": "front_range_grass"})
    assert p["fuel_model"] == scene.fuel_model
    assert p["wind_ms"] == scene.wind_ms

    override = resolve_params({"scene": "front_range_grass", "wind_ms": 2.0})
    assert override["wind_ms"] == 2.0
    assert override["fuel_model"] == scene.fuel_model, "scene's other tuning kept"


def test_unknown_parameters_are_rejected_by_name():
    with pytest.raises(ValueError, match="wind_speed"):
        resolve_params({"wind_speed": 5})


def test_unknown_fuel_model_lists_the_valid_ones():
    with pytest.raises(ValueError, match="gr1"):
        resolve_params({"fuel_model": "grass"})


def test_moisture_given_as_a_percentage_is_caught():
    """
    6 and 0.06 are both plausible-looking inputs and mean wildly different
    things. A moisture above 500% is not a fuel state, it is a unit mistake,
    and silently modelling it would produce a fire that will not start with
    no indication why.
    """
    with pytest.raises(ValueError, match="fraction, not a percentage"):
        resolve_params({"moisture_1h": 6.0})


def test_weather_wind_passed_as_midflame_is_caught():
    """
    Midflame wind is a third to a half of the 10 m wind. Passing the weather
    value straight in overstates spread several-fold, so an implausible
    midflame value is refused with the reason rather than modelled.
    """
    with pytest.raises(ValueError, match="MIDFLAME"):
        resolve_params({"wind_ms": 30.0})


def test_bearing_wraps_and_duration_is_capped():
    assert resolve_params({"wind_from_bearing": 405.0})["wind_from_bearing"] == 45.0
    assert resolve_params({"wind_from_bearing": -90.0})["wind_from_bearing"] == 270.0
    with pytest.raises(ValueError, match="capped at 72"):
        resolve_params({"duration_hours": 100})


@pytest.mark.parametrize("bad", [0, -5, "fast"])
def test_nonsense_durations_are_rejected(bad):
    with pytest.raises(ValueError):
        resolve_params({"duration_hours": bad})


def test_neighbour_count_is_restricted():
    with pytest.raises(ValueError, match="neighbours"):
        resolve_params({"neighbours": 12})


# --------------------------------------------------------------------------
# Ignition placement
# --------------------------------------------------------------------------

def test_ignition_is_a_single_cell():
    """
    A fire starts at a point. Spreading the ignition over a patch would hide
    the shape the elliptical model exists to produce.
    """
    dem = np.zeros((21, 21))
    mask, note = ignition_mask_for(dem)
    assert mask.sum() == 1
    assert "centre" in note


def test_ignition_point_maps_through_the_bbox():
    """North is row 0, so a northern latitude must land in a low row index."""
    dem = np.zeros((101, 101))
    north, _ = ignition_mask_for(dem, ignition_point=(-118.74, 34.135), bbox=BBOX)
    south, _ = ignition_mask_for(dem, ignition_point=(-118.74, 34.065), bbox=BBOX)
    assert np.nonzero(north)[0][0] < np.nonzero(south)[0][0]

    west, _ = ignition_mask_for(dem, ignition_point=(-118.81, 34.10), bbox=BBOX)
    east, _ = ignition_mask_for(dem, ignition_point=(-118.67, 34.10), bbox=BBOX)
    assert np.nonzero(west)[1][0] < np.nonzero(east)[1][0]


def test_ignition_outside_the_aoi_is_rejected():
    with pytest.raises(ValueError, match="outside the AOI"):
        ignition_mask_for(np.zeros((11, 11)), ignition_point=(0.0, 0.0), bbox=BBOX)


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------

def test_a_scene_runs_and_reports_a_burn():
    res = run()
    stats = res
    assert res["mode"] == "simulated"
    assert stats["burned_area_ha"] > 0
    assert stats["fuel_model"] == "sh4"
    assert stats["head_ros_m_min_max"] > 0
    assert stats["flame_length_m_max"] > 0


def test_every_result_is_labelled_simulated():
    """
    The label has to survive every layer, because a modelled fire over real
    named terrain is indistinguishable from a reconstruction at a glance.
    """
    res = run()
    assert res["mode"] == "simulated"
    assert res["simulation"]["meta"]["mode"] == "simulated"
    assert res["disclosure"] == DISCLOSURE
    assert "not a forecast" in DISCLOSURE
    assert "no spotting" in res["limitations"]


def test_the_payload_round_trips():
    res = run()
    arrival, flame = decode_fire(res["simulation"])
    burned = np.isfinite(arrival)

    assert burned.sum() == res["simulation"]["meta"]["burned_cells"]
    assert arrival[burned].min() == 0.0, "the ignition cell burns at t=0"
    assert arrival[burned].max() <= res["simulation"]["meta"]["duration_min"]
    assert float(flame.max()) == pytest.approx(
        res["flame_length_m_max"], abs=0.15)
    # Unburned ground carries no flame length.
    assert np.all(flame[~burned] == 0.0)


def test_arrival_time_transport_beats_shipping_frames():
    """
    One arrival grid replaces every frame of the animation.

    The flood simulator ships a grid per frame; a fire does not have to,
    because each frame is a threshold of the same array. The saving is what
    makes a native-resolution fire animation practical over the wire, so it
    is worth a test that it stays that way.
    """
    res = run()
    meta = res["simulation"]["meta"]
    one_grid = meta["ny"] * meta["nx"] * 2
    assert len(res["simulation"]["arrival_b64"]) < one_grid * 2
    # A comparable frame-based payload at 48 frames would be this much bigger.
    assert res["payload_bytes"] < one_grid * 48 / 4


def test_growth_curve_is_monotonic_and_ends_at_the_total():
    res = run()
    growth = res["perimeter_growth_ha"]
    areas = [a for _, a in growth]
    assert areas == sorted(areas), "burned area cannot shrink"
    assert areas[-1] == pytest.approx(res["burned_area_ha"], rel=1e-6)
    assert growth[0][0] == 0.0


def test_wind_direction_reaches_the_solver():
    """A scene's wind must actually steer the burn, not just be reported."""
    east = run({"fuel_model": "gr1", "wind_ms": 8.0,
                "wind_from_bearing": 270.0, "duration_hours": 3.0})
    west = run({"fuel_model": "gr1", "wind_ms": 8.0,
                "wind_from_bearing": 90.0, "duration_hours": 3.0})
    a_east, _ = decode_fire(east["simulation"])
    a_west, _ = decode_fire(west["simulation"])

    cols = np.arange(a_east.shape[1])
    centroid_east = (np.isfinite(a_east) * cols).sum() / np.isfinite(a_east).sum()
    centroid_west = (np.isfinite(a_west) * cols).sum() / np.isfinite(a_west).sum()
    assert centroid_east > centroid_west


def test_a_longer_fire_burns_more():
    short = run({"scene": "malibu_chaparral", "duration_hours": 2.0})
    long = run({"scene": "malibu_chaparral", "duration_hours": 8.0})
    assert long["burned_area_ha"] > short["burned_area_ha"]


def test_wet_fuel_is_refused_with_a_reason():
    """
    Fuel above its moisture of extinction produces no fire at all, and the
    user needs to know that is why, not see an empty map.
    """
    with pytest.raises(ValueError, match="moisture of extinction"):
        run({"fuel_model": "gr1", "moisture_1h": 0.30,
             "moisture_10h": 0.30, "moisture_100h": 0.30})


def test_a_fire_that_cannot_spread_is_refused_with_a_reason():
    with pytest.raises(ValueError, match="did not spread"):
        run({"fuel_model": "tl8", "wind_ms": 0.0, "duration_hours": 0.02})


def test_an_oversized_aoi_is_refused_before_solving():
    huge = np.zeros((900, 900))
    with pytest.raises(ValueError, match="cell limit"):
        run(provider=lambda b, s: FakeTile(huge, 30.0))
    assert MAX_CELLS < 900 * 900


def test_containment_note_tracks_flame_length():
    """
    Byram's flame length is what decides whether a fire can be fought
    directly, so the thresholds are reported rather than left to the reader.
    """
    calm = run({"fuel_model": "tl9", "wind_ms": 0.5, "duration_hours": 10.0})
    fierce = run({"scene": "malibu_chaparral"})
    assert calm["flame_length_m_p90"] < fierce["flame_length_m_p90"]
    assert "hand crews" in calm["containment_note"]
    assert "ineffective" in fierce["containment_note"]


def test_the_angular_error_is_stated_with_the_result():
    scene = fire_presets.get_scene("front_range_grass")
    for nb, expected in ((8, "8.2"), (16, "2.8"), (32, "1.3")):
        res = run({"scene": "front_range_grass", "neighbours": nb,
                   "duration_hours": 2.0}, bbox=list(scene.bbox))
        assert expected in res["angular_error_note"]


def test_every_scene_is_well_formed_and_runs():
    provider = ridged()
    for scene in fire_presets.scenes_as_json():
        assert scene["fuel_model"]
        assert scene["summary"]
        assert "not a reconstruction" in scene["disclosure"]
        lon, lat = scene["ignition_point"]
        min_lon, min_lat, max_lon, max_lat = scene["bbox"]
        assert min_lon <= lon <= max_lon and min_lat <= lat <= max_lat, scene["id"]

        res = simulate_fire(scene["bbox"], "2026-08-01", "2026-08-02",
                            {"scene": scene["id"], "duration_hours": 2.0},
                            dem_provider=provider)
        assert res["burned_area_ha"] > 0, scene["id"]
