import numpy as np
import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")

import provenance  # noqa: E402
from gee.raster_fetch import DemTile  # noqa: E402
from gee.registry import ANALYSIS_REGISTRY, registry_as_json  # noqa: E402
from solver import fire_sim, flood_sim  # noqa: E402
from tests.conftest import synthetic_valley  # noqa: E402

AOI = [-99.40, 30.02, -99.28, 30.10]

FAST = {"duration_hours": 0.4, "n_frames": 4, "max_transport_dim": 48}


@pytest.fixture
def client(monkeypatch):
    dem = synthetic_valley(ny=60, nx=48)

    def stub_fetch(bbox, scale_m):
        return DemTile(dem=dem.copy(), dx=float(scale_m), crs="EPSG:32614", bbox=list(bbox))

    monkeypatch.setattr(flood_sim, "_fetch_dem", stub_fetch)

    def stub_fire_fetch(bbox, scale_m):
        ridged = (
            np.add.outer(np.linspace(0, 240, 90), np.linspace(0, 160, 90))
            + 90 * np.sin(np.linspace(0, 9, 90))[None, :]
        )
        return DemTile(dem=ridged, dx=float(scale_m), crs="EPSG:32611", bbox=list(bbox))

    monkeypatch.setattr(fire_sim, "_fetch_dem", stub_fire_fetch)

    import main

    return fastapi_testclient.TestClient(main.app)


FIRE_FAST = {"duration_hours": 1.0, "neighbours": 8}
FIRE_AOI = [-118.82, 34.06, -118.66, 34.14]


class TestRegistryExposure:
    def test_the_simulation_appears_automatically(self):
        entry = next(t for t in registry_as_json() if t["id"] == "flood_simulation")
        assert entry["mode"] == "simulated"
        assert entry["accepts_params"] is True
        assert "peak_discharge_m3s" in entry["params_schema"]
        assert entry["category"] == "Simulation (forward model)"

    def test_the_description_leads_with_what_it_is_not(self):
        entry = ANALYSIS_REGISTRY["flood_simulation"]
        assert entry["description"].startswith("SIMULATED")
        assert "Flood Extent Mapping" in entry["description"]

    def test_every_other_analysis_is_still_observed_and_parameterless(self):
        entries = registry_as_json()
        simulated = [t for t in entries if t.get("mode") == "simulated"]
        others = [t for t in entries if t.get("mode") != "simulated"]
        assert len(simulated) >= 2, "flood and wildfire forward models"
        assert len(others) == 24
        assert all(t["mode"] == "observed" for t in others)
        assert all(t["accepts_params"] is False for t in others)
        assert all(t["params_schema"] is None for t in others)

    def test_registry_endpoint_serves_the_new_fields(self, client):
        payload = client.get("/registry").json()
        entry = next(t for t in payload if t["id"] == "flood_simulation")
        assert entry["mode"] == "simulated"


class TestScenesEndpoint:
    def test_lists_scenes_with_their_disclosure(self, client):
        body = client.get("/simulate/scenes").json()
        assert len(body["scenes"]) >= 5
        assert "not a gauge record" in body["note"]
        assert all(s["mode"] == "simulated" for s in body["scenes"])


class TestSimulateEndpoint:
    def test_runs_inline_and_returns_a_full_result(self, client):
        response = client.post(
            "/simulate",
            json={"bbox": AOI, "start_date": "2026-08-29", "run_async": False, "params": FAST},
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["analysis_type"] == "flood_simulation"
        assert body["mode"] == "simulated"
        assert body["tile_url"] == ""
        assert body["simulation"]["meta"]["n_frames"] == 4
        assert "SIMULATED" in body["stats"]["disclosure"]
        assert "mode" not in body["stats"]

    def test_a_scene_supplies_its_own_aoi(self, client):
        response = client.post(
            "/simulate",
            json={"scene": "bright_angel_canyon", "run_async": False, "params": FAST},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["stats"]["scene_id"] == "bright_angel_canyon"
        assert body["bbox"] == pytest.approx([-112.135, 36.060, -112.050, 36.130])

    def test_an_unknown_scene_is_a_client_error_that_names_the_options(self, client):
        response = client.post("/simulate", json={"scene": "atlantis"})
        assert response.status_code == 400
        assert "Available" in response.json()["detail"]

    def test_neither_bbox_nor_scene_is_rejected(self, client):
        assert client.post("/simulate", json={"run_async": False}).status_code == 422

    def test_a_bad_parameter_is_reported_not_ignored(self, client):
        response = client.post(
            "/simulate",
            json={"bbox": AOI, "run_async": False, "params": {"peak_dischage_m3s": 500}},
        )
        assert response.status_code == 400
        assert "Unknown simulation parameter" in response.json()["detail"]

    def test_the_date_defaults_to_today_rather_than_failing(self, client):
        response = client.post("/simulate", json={"bbox": AOI, "run_async": False, "params": FAST})
        assert response.status_code == 200
        assert body_date_is_iso(response.json()["start_date"])


def body_date_is_iso(value: str) -> bool:
    from datetime import date

    date.fromisoformat(value)
    return True


class TestParamsChannel:
    def test_analyze_accepts_params_for_a_simulation(self, client):
        response = client.post(
            "/analyze",
            json={
                "analysis_type": "flood_simulation",
                "bbox": AOI,
                "start_date": "2026-08-29",
                "end_date": "2026-08-30",
                "params": FAST,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["mode"] == "simulated"

    def test_params_sent_to_analyze_are_not_silently_dropped(self, client):
        from models.requests import AnalyzeRequest

        assert "params" in AnalyzeRequest.model_fields

    def test_analyses_that_take_no_params_say_so(self, client):
        from api.analyze import run_analysis

        with pytest.raises(ValueError, match="does not take extra parameters"):
            run_analysis("flood_extent", AOI, "2026-01-01", "2026-01-31", params={"peak_discharge_m3s": 100})


class TestProvenance:
    @pytest.fixture
    def signed(self, client):
        return client.post(
            "/simulate",
            json={"bbox": AOI, "start_date": "2026-08-29", "run_async": False, "params": FAST},
        ).json()

    def test_a_fresh_result_verifies(self, signed):
        assert provenance.verify(signed)["valid"] is True

    def test_relabelling_a_simulation_as_observed_breaks_the_signature(self, signed):
        tampered = dict(signed, mode="observed")
        verdict = provenance.verify(tampered)
        assert verdict["valid"] is False

    def test_changing_a_number_still_breaks_the_signature(self, signed):
        tampered = dict(signed)
        tampered["headline_stat"] = dict(tampered["headline_stat"], value=99.9)
        assert provenance.verify(tampered)["valid"] is False

    def test_restyling_does_not_break_it(self, signed):
        restyled = dict(signed, tile_url="https://example.invalid/{z}/{x}/{y}")
        assert provenance.verify(restyled)["valid"] is True

    def test_results_issued_before_mode_existed_still_verify(self):
        legacy = provenance.stamp(
            {
                "analysis_type": "flood_extent",
                "bbox": AOI,
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "data_date": "2026-01-30",
                "confidence": 0.86,
                "headline_stat": {"label": "Flood extent", "value": 342, "unit": "km2"},
                "stats": {},
            }
        )
        assert "mode" not in legacy
        assert provenance.verify(legacy)["valid"] is True


class TestAiLabelling:
    def test_slim_result_carries_the_mode_and_a_warning(self):
        from janus.tools import _slim_result

        slim = _slim_result(
            {
                "analysis_type": "flood_simulation",
                "mode": "simulated",
                "headline_stat": {"label": "Peak simulated depth", "value": 3.2, "unit": "m"},
                "stats": {"peak_depth_m": 3.2},
            }
        )
        assert slim["mode"] == "simulated"
        assert "not observations" in slim["WARNING"]

    def test_observed_results_carry_no_warning(self):
        from janus.tools import _slim_result

        slim = _slim_result(
            {
                "analysis_type": "flood_extent",
                "mode": "observed",
                "headline_stat": {"label": "Flood extent", "value": 342, "unit": "km2"},
                "stats": {},
            }
        )
        assert slim["mode"] == "observed"
        assert "WARNING" not in slim

    def test_the_query_parser_prompt_separates_the_two(self):
        prompt = open("ai/system_prompt.md").read()
        assert "flood_simulation" in prompt
        assert "fire_simulation" in prompt
        assert "Observed versus simulated" in prompt
        assert '"mode": "simulated"' in prompt


def test_worker_exposes_a_simulation_job():
    from jobs import worker

    assert callable(worker.job_run_simulation)


def test_main_registers_the_simulation_routes():
    import main

    paths = set(main.app.openapi()["paths"])
    assert {"/simulate", "/simulate/scenes", "/status/{job_id}", "/registry"} <= paths


def test_gzip_is_enabled_for_the_large_payloads():
    from fastapi.middleware.gzip import GZipMiddleware

    import main

    assert any(m.cls is GZipMiddleware for m in main.app.user_middleware)


class TestWildfireEndpoint:
    def test_a_fire_scene_runs_and_returns_a_burn(self, client):
        body = client.post(
            "/simulate",
            json={
                "kind": "fire",
                "scene": "malibu_chaparral",
                "run_async": False,
                "params": FIRE_FAST,
            },
        ).json()

        assert body["mode"] == "simulated"
        stats = body["stats"]
        assert stats["burned_area_ha"] > 0
        assert stats["fuel_model"] == "sh4"
        assert "arrival_b64" in body["simulation"]
        assert "flame_b64" in body["simulation"]

    def test_kind_selects_the_physics(self, client):
        fire = client.post(
            "/simulate",
            json={
                "kind": "fire",
                "bbox": FIRE_AOI,
                "run_async": False,
                "params": FIRE_FAST,
            },
        ).json()
        flood = client.post(
            "/simulate",
            json={
                "bbox": AOI,
                "run_async": False,
                "params": FAST,
            },
        ).json()

        assert "flame_length_m_max" in fire["stats"]
        assert "flame_length_m_max" not in flood["stats"]
        assert "peak_depth_m" in flood["stats"]
        assert "peak_depth_m" not in fire["stats"]

    def test_kind_defaults_to_flood_for_older_callers(self, client):
        body = client.post(
            "/simulate",
            json={
                "bbox": AOI,
                "run_async": False,
                "params": FAST,
            },
        ).json()
        assert "peak_depth_m" in body["stats"]

    def test_an_unknown_kind_is_rejected(self, client):
        assert (
            client.post(
                "/simulate",
                json={
                    "kind": "earthquake",
                    "bbox": AOI,
                    "run_async": False,
                },
            ).status_code
            == 422
        )

    def test_a_fire_scene_id_is_not_accepted_as_a_flood_scene(self, client):
        response = client.post(
            "/simulate",
            json={
                "scene": "malibu_chaparral",
                "run_async": False,
            },
        )
        assert response.status_code == 400
        assert "Unknown" in response.json()["detail"]

    def test_scenes_endpoint_serves_both_catalogues(self, client):
        both = client.get("/simulate/scenes").json()
        kinds = {s["kind"] for s in both["scenes"]}
        assert kinds == {"flood", "fire"}
        assert all(s["mode"] == "simulated" for s in both["scenes"])

        only_fire = client.get("/simulate/scenes?kind=fire").json()
        assert {s["kind"] for s in only_fire["scenes"]} == {"fire"}
        assert "not a reconstruction" in only_fire["note"]

        assert client.get("/simulate/scenes?kind=volcano").status_code == 400

    def test_the_fire_result_is_labelled_simulated_everywhere(self, client):
        body = client.post(
            "/simulate",
            json={
                "kind": "fire",
                "scene": "front_range_grass",
                "run_async": False,
                "params": FIRE_FAST,
            },
        ).json()

        assert body["mode"] == "simulated"
        assert body["simulation"]["meta"]["mode"] == "simulated"
        assert "not a forecast" in body["stats"]["disclosure"]
        assert "no spotting" in body["stats"]["limitations"]

    def test_bad_fire_parameters_return_400_not_500(self, client):
        for params in (
            {"moisture_1h": 6.0},
            {"wind_ms": 40.0},
            {"fuel_model": "grass"},
            {"neighbours": 12},
        ):
            response = client.post(
                "/simulate",
                json={
                    "kind": "fire",
                    "bbox": FIRE_AOI,
                    "run_async": False,
                    "params": {**FIRE_FAST, **params},
                },
            )
            assert response.status_code == 400, params
