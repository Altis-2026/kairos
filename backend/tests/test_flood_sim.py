"""
The simulation pipeline end to end, against synthetic terrain.

`simulate_flood` takes an injectable DEM provider precisely so this can run
with no Earth Engine, no credentials and no network — the same discipline the
solver itself follows.
"""

import numpy as np
import pytest

from gee.raster_fetch import DemTile
from solver import flood_sim
from solver.payload import decode_simulation
from tests.conftest import synthetic_valley

AOI = [-99.40, 30.02, -99.28, 30.10]


@pytest.fixture(scope="module")
def result():
    """One full run, shared across the assertions that inspect it."""
    dem = synthetic_valley()

    def provider(bbox, scale_m):
        return DemTile(dem=dem.copy(), dx=float(scale_m), crs="EPSG:32614",
                       bbox=list(bbox))

    return flood_sim.simulate_flood(
        bbox=AOI,
        start_date="2026-08-29",
        end_date="2026-08-29",
        params={
            "peak_discharge_m3s": 180.0, "rise_minutes": 10.0,
            "peak_minutes": 10.0, "recession_minutes": 40.0,
            "duration_hours": 2.0, "n_frames": 12, "max_transport_dim": 64,
        },
        dem_provider=provider,
    )


class TestParameterResolution:
    def test_defaults_apply_when_nothing_is_given(self):
        p = flood_sim.resolve_params(None)
        assert p["peak_discharge_m3s"] == flood_sim.DEFAULTS["peak_discharge_m3s"]
        assert p["scene"] is None

    def test_a_scene_supplies_its_own_tuning(self):
        p = flood_sim.resolve_params({"scene": "bright_angel_canyon"})
        assert p["scene"].id == "bright_angel_canyon"
        assert p["peak_discharge_m3s"] == 220.0
        assert p["n_manning"] == 0.045

    def test_explicit_parameters_beat_the_scene(self):
        """Pick a showcase scene, then tune one knob without losing the rest."""
        p = flood_sim.resolve_params(
            {"scene": "bright_angel_canyon", "peak_discharge_m3s": 999.0}
        )
        assert p["peak_discharge_m3s"] == 999.0
        assert p["n_manning"] == 0.045      # still the scene's

    def test_a_typo_is_rejected_rather_than_ignored(self):
        """
        Silently dropping `peak_dischage_m3s` would run the default and look
        like the parameter simply had no effect.
        """
        with pytest.raises(ValueError, match="Unknown simulation parameter"):
            flood_sim.resolve_params({"peak_dischage_m3s": 500})

    @pytest.mark.parametrize(
        "params, message",
        [
            ({"peak_discharge_m3s": 0}, "must be positive"),
            ({"peak_discharge_m3s": float("nan")}, "must be a finite number"),
            ({"n_manning": -0.1}, "must be positive"),
            ({"rise_minutes": -5}, "non-negative"),
            ({"n_frames": 0}, "n_frames"),
            ({"n_frames": 5000}, "n_frames"),
            ({"duration_hours": 500}, "capped at 72"),
        ],
    )
    def test_out_of_range_values_are_rejected(self, params, message):
        with pytest.raises(ValueError, match=message):
            flood_sim.resolve_params(params)

    @pytest.mark.parametrize("bad", ["lots", None, {"a": 1}, [1, 2]])
    def test_a_non_numeric_value_is_a_user_error_not_a_crash(self, bad):
        """
        These arrive as JSON over a public endpoint. A string where a number
        belongs must name the field in a 400, not surface as a TypeError from
        somewhere inside the solver.
        """
        with pytest.raises(ValueError, match="peak_discharge_m3s must be"):
            flood_sim.resolve_params({"peak_discharge_m3s": bad})

    def test_resource_ceilings_clamp_rather_than_reject(self):
        """
        A caller asking for a longer solve or a bigger payload gets the
        maximum. These bound how long one request can hold a worker and how
        much data it can return, so they cannot be suggestions.
        """
        p = flood_sim.resolve_params(
            {"max_seconds": 99_999, "max_transport_dim": 8192, "inflow_cells": 10_000}
        )
        assert p["max_seconds"] == flood_sim.DEFAULT_MAX_SECONDS
        assert p["max_transport_dim"] == flood_sim.MAX_TRANSPORT_DIM
        assert p["inflow_cells"] == 400

    def test_frames_ship_at_native_resolution_by_default(self):
        """
        Decimation is off unless asked for. Area-averaging flattens peaks in a
        confined channel badly enough (8.8 m -> 4.8 m on a real scene) that the
        headline depth and the rendered animation stopped agreeing.
        """
        assert flood_sim.resolve_params(None)["max_transport_dim"] is None

    def test_ceilings_can_still_be_lowered(self):
        p = flood_sim.resolve_params({"max_seconds": 30, "max_transport_dim": 64})
        assert p["max_seconds"] == 30
        assert p["max_transport_dim"] == 64


class TestHydrographShape:
    def test_rise_plateau_recession(self):
        knots = flood_sim.build_hydrograph(
            flood_sim.resolve_params(
                {"peak_discharge_m3s": 100.0, "rise_minutes": 10.0,
                 "peak_minutes": 20.0, "recession_minutes": 30.0}
            )
        )
        assert knots == [(0.0, 0.0), (600.0, 100.0), (1800.0, 100.0), (3600.0, 0.0)]

    def test_zero_length_segments_collapse_instead_of_breaking_the_solver(self):
        """
        An instantaneous rise is a legitimate request (a dam break). It must
        not produce two knots at the same time, which the solver rejects.
        """
        knots = flood_sim.build_hydrograph(
            flood_sim.resolve_params(
                {"rise_minutes": 0.0, "peak_minutes": 0.0, "recession_minutes": 60.0}
            )
        )
        times = [t for t, _ in knots]
        assert times == sorted(set(times))
        assert knots[0][1] == flood_sim.DEFAULTS["peak_discharge_m3s"]


class TestInflowPlacement:
    def test_water_enters_on_the_upstream_edge(self, valley_dem):
        """The valley drains south, so the inflow belongs on the north edge."""
        assert flood_sim.upstream_edge(valley_dem, ("south",)) == "north"

    def test_inflow_lands_in_the_channel_not_on_a_bank(self, valley_dem):
        mask, note = flood_sim.inflow_mask_for(valley_dem, ("south",), 12)
        assert mask.sum() == 12
        assert "north" in note

        rows, cols = np.nonzero(mask)
        centre = (valley_dem.shape[1] - 1) / 2.0
        assert np.abs(cols - centre).max() < valley_dem.shape[1] * 0.25
        assert rows.max() < valley_dem.shape[0] * 0.2   # near the upstream edge

    def test_an_explicit_point_is_snapped_to_the_local_low(self, valley_dem, aoi):
        """A click on the valley wall should still put water in the channel."""
        lon = aoi[0] + 0.5 * (aoi[2] - aoi[0])
        lat = aoi[1] + 0.9 * (aoi[3] - aoi[1])
        mask, note = flood_sim.inflow_mask_for(
            valley_dem, ("south",), 9, inflow_point=[lon, lat], bbox=aoi
        )
        assert mask.sum() == 9
        assert "user-placed" in note and "snapped" in note

    def test_a_point_outside_the_aoi_is_rejected(self, valley_dem, aoi):
        with pytest.raises(ValueError, match="outside the AOI"):
            flood_sim.inflow_mask_for(
                valley_dem, ("south",), 9, inflow_point=[0.0, 0.0], bbox=aoi
            )


class TestFullPipeline:
    def test_produces_an_animation_that_rises_and_recedes(self, result):
        _, depths = decode_simulation(result["simulation"])
        peaks = [float(d.max()) for d in depths]
        assert max(peaks) > 0.05, "no flood wave was produced"
        assert peaks[-1] < max(peaks), "the flood never receded"
        assert np.argmax(peaks) not in (0, len(peaks) - 1)

    def test_terrain_travels_with_the_water(self, result):
        """The 3D viewer builds both meshes from this one payload."""
        dem, depths = decode_simulation(result["simulation"])
        assert dem.shape == depths.shape[1:]
        assert dem.max() > dem.min()

    def test_labelled_as_simulated_everywhere_it_could_be_read(self, result):
        assert result["mode"] == "simulated"
        assert result["simulation"]["meta"]["mode"] == "simulated"
        assert "SIMULATED" in result["disclosure"]
        assert "not a satellite observation" in result["disclosure"]

    def test_confidence_is_explicitly_not_forecast_skill(self, result):
        """
        The UI renders `confidence` as a badge. For a simulation it can only
        mean numerical integrity, and the result has to say so.
        """
        assert result["confidence"] == 0.95
        assert "NOT forecast skill" in result["confidence_meaning"]

    def test_reports_its_own_mass_closure(self, result):
        assert abs(result["mass_error"]) < 1e-12
        assert result["injected_volume_m3"] > 0
        assert result["solver_steps"] > 100
        assert result["truncated"] is False

    def test_dem_conditioning_is_disclosed(self, result):
        """Pit filling changes the terrain, so it can never be silent."""
        assert result["dem_pits_filled"] is True
        assert "changes the terrain" in result["dem_conditioning_note"]

    def test_headline_is_the_peak_depth(self, result):
        assert result["headline_stat"]["unit"] == "m"
        assert result["headline_stat"]["value"] == pytest.approx(
            result["peak_depth_m"], abs=0.01
        )

    def test_reports_extent_as_well_as_depth(self, result):
        assert result["total_inundated_km2"] > 0
        assert result["total_inundated_km2"] >= result["max_instantaneous_extent_km2"]

    def test_carries_the_hydrograph_it_actually_used(self, result):
        assert result["hydrograph"][0] == [0.0, 0.0]
        assert max(q for _, q in result["hydrograph"]) == 180.0

    def test_no_server_rendered_tile_is_claimed(self, result):
        assert result["tile_url"] == ""


def test_scale_parameter_reaches_the_solver(fake_dem_provider, aoi):
    result = flood_sim.simulate_flood(
        aoi, "2026-08-29", "2026-08-29",
        params={"scale_m": 60.0, "duration_hours": 0.5, "n_frames": 3},
        dem_provider=fake_dem_provider,
    )
    assert result["dem_scale_m"] == 60.0
    assert result["simulation"]["meta"]["solve_dx"] == 60.0


def test_a_scene_can_drive_the_whole_run(fake_dem_provider, aoi):
    result = flood_sim.simulate_flood(
        aoi, "2026-08-29", "2026-08-29",
        params={"scene": "rio_ruidoso_burn", "duration_hours": 0.5, "n_frames": 3},
        dem_provider=fake_dem_provider,
    )
    assert result["scene_id"] == "rio_ruidoso_burn"
    assert result["scene_name"].startswith("Rio Ruidoso")
    assert "not a gauge record" in result["hydrograph_note"]
