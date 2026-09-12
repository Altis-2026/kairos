"""Showcase scenes: every one must be runnable and honestly labelled."""

import pytest

from gee.raster_fetch import plan_grid
from solver.forcing import validate_hydrograph
from solver.presets import SCENES, get_scene, scenes_as_json


@pytest.mark.parametrize("scene_id", list(SCENES))
class TestEveryScene:
    def test_hydrograph_is_valid(self, scene_id):
        times, values = validate_hydrograph(SCENES[scene_id].hydrograph())
        assert values.max() == SCENES[scene_id].peak_discharge_m3s

    def test_run_outlasts_the_hydrograph_so_it_can_recede(self, scene_id):
        """
        If the run ends when the inflow does, the animation stops at the peak
        and the flood never visibly drains — the whole point of the feature.
        """
        scene = SCENES[scene_id]
        assert scene.duration_s() > scene.hydrograph()[-1][0]

    def test_bbox_is_well_formed_and_small_enough_to_solve(self, scene_id):
        scene = SCENES[scene_id]
        min_lon, min_lat, max_lon, max_lat = scene.bbox
        assert min_lon < max_lon and min_lat < max_lat
        assert -180 <= min_lon and max_lon <= 180
        assert -90 <= min_lat and max_lat <= 90

        plan = plan_grid(list(scene.bbox), scene.scale_m)
        assert plan.cells <= 150_000, (
            f"{scene_id} is {plan.cells:,} cells — too slow for a demo scene; "
            f"raise its scale_m"
        )
        assert not plan.downscaled

    def test_roughness_is_physically_plausible(self, scene_id):
        assert 0.01 <= SCENES[scene_id].n_manning <= 0.2

    def test_carries_its_disclosure(self, scene_id):
        """
        A synthetic hydrograph over real terrain looks exactly as convincing
        as a real one. The difference has to be stated on every scene.
        """
        scene = SCENES[scene_id]
        assert scene.disclosure
        assert "not a gauge record" in scene.disclosure
        assert scene.as_dict()["mode"] == "simulated"


def test_catalogue_is_serializable_and_complete():
    catalogue = scenes_as_json()
    assert len(catalogue) == len(SCENES)
    for entry in catalogue:
        assert entry["id"] in SCENES
        assert entry["summary"] and entry["region"] and entry["name"]


def test_unknown_scene_lists_what_exists():
    with pytest.raises(ValueError, match="Available"):
        get_scene("atlantis")
