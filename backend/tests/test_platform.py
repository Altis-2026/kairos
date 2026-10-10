import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")

import ratelimit  # noqa: E402
import result_cache  # noqa: E402
from ai.parser import ParsedQuery  # noqa: E402
from api import districts  # noqa: E402

AOI = [-99.40, 30.02, -99.28, 30.10]


def fake_result(analysis_type="flood_extent", value=42.0):
    return {
        "analysis_type": analysis_type,
        "display_name": "Flood Extent Mapping",
        "bbox": AOI,
        "start_date": "2025-07-03",
        "end_date": "2025-07-12",
        "tile_url": "https://example.test/{z}/{x}/{y}",
        "data_date": "2025-07-06",
        "confidence": 0.8,
        "headline_stat": {"label": "Flooded area", "value": value, "unit": "km²"},
        "context_layers": [],
        "mode": "observed",
        "stats": {},
    }


@pytest.fixture
def client():
    import main

    return fastapi_testclient.TestClient(main.app)


def test_health_reports_service_state(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["ai"] in {"configured", "not configured"}


def test_token_bucket_refuses_after_capacity(monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "compute", (3, 3600))
    assert [ratelimit._take("compute", "1.2.3.4") for _ in range(4)] == [True, True, True, False]
    assert ratelimit._take("compute", "5.6.7.8")


def test_daily_ceiling_stops_ai_calls(monkeypatch):
    monkeypatch.setattr(ratelimit, "DAILY_AI_CEILING", 2)
    assert ratelimit._spend_daily()
    assert ratelimit._spend_daily()
    assert not ratelimit._spend_daily()


def test_rate_limited_route_answers_429(client, monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "ai", (1, 3600))
    monkeypatch.setattr(
        "api.query.parse_natural_language",
        lambda *a, **k: ParsedQuery(understood=False, clarification="Where?"),
    )
    assert client.post("/query", json={"query": "flood"}).status_code == 200
    second = client.post("/query", json={"query": "flood"})
    assert second.status_code == 429
    assert "free tier" in second.json()["detail"]


def test_result_cache_expires(monkeypatch):
    result_cache.put("k", {"a": 1})
    assert result_cache.get("k") == {"a": 1}
    monkeypatch.setattr(result_cache, "TTL_SECONDS", -1)
    assert result_cache.get("k") is None


def test_run_analysis_serves_repeats_from_cache(monkeypatch):
    from api import analyze
    from gee.registry import ANALYSIS_REGISTRY

    calls = []

    def fake_detector(bbox, start_date, end_date):
        calls.append(bbox)
        return {"tile_url": "u", "data_date": "2025-07-06", "flood_area_km2": 3.0}

    monkeypatch.setitem(ANALYSIS_REGISTRY["flood_extent"], "function", fake_detector)
    monkeypatch.setattr(analyze, "_context_layers", lambda *a: [])
    first = analyze.run_analysis("flood_extent", AOI, "2025-07-03", "2025-07-12")
    second = analyze.run_analysis("flood_extent", AOI, "2025-07-03", "2025-07-12")
    assert first == second
    assert len(calls) == 1


def test_polygon_runs_on_its_envelope(monkeypatch):
    from api import analyze
    from gee import common
    from gee.registry import ANALYSIS_REGISTRY

    seen = {}

    def fake_detector(bbox, start_date, end_date):
        seen["bbox"] = bbox
        seen["polygon"] = common.active_polygon.get()
        return {"tile_url": "u", "data_date": "2025-07-06"}

    polygon = [[-99.4, 30.0], [-99.2, 30.0], [-99.3, 30.2]]
    monkeypatch.setitem(ANALYSIS_REGISTRY["flood_extent"], "function", fake_detector)
    monkeypatch.setattr(analyze, "_context_layers", lambda *a: [])
    out = analyze.run_analysis("flood_extent", AOI, "2025-07-03", "2025-07-12", polygon=polygon)
    assert seen["bbox"] == [-99.4, 30.0, -99.2, 30.2]
    assert seen["polygon"] == polygon
    assert out["polygon"] == polygon
    assert common.active_polygon.get() is None


def test_analyze_rejects_a_bad_polygon(client):
    body = {
        "analysis_type": "flood_extent",
        "bbox": AOI,
        "start_date": "2025-07-03",
        "end_date": "2025-07-12",
        "polygon": [[0, 0], [1, 1]],
    }
    assert client.post("/analyze", json=body).status_code == 422


def test_query_runs_extra_analyses_and_reports_them(client, monkeypatch):
    parsed = ParsedQuery(
        understood=True,
        analysis_type="flood_extent",
        bbox=AOI,
        start_date="2025-07-03",
        end_date="2025-07-12",
        extra_analyses=[{"analysis_type": "building_damage"}],
    )
    monkeypatch.setattr("api.query.parse_natural_language", lambda *a, **k: parsed)
    monkeypatch.setattr("api.query.run_analysis", lambda analysis_type, **k: fake_result(analysis_type))
    monkeypatch.setattr("api.query.narrate_result", lambda *a, **k: "Narrated.")
    body = client.post("/query", json={"query": "flood and damage"}).json()
    assert body["understood"] is True
    assert len(body["results"]) == 2
    assert body["explanation"].startswith("Narrated.")
    assert "Also added" in body["explanation"]


def test_query_falls_back_when_narration_fails(client, monkeypatch):
    parsed = ParsedQuery(
        understood=True,
        analysis_type="flood_extent",
        bbox=AOI,
        start_date="2025-07-03",
        end_date="2025-07-12",
    )
    monkeypatch.setattr("api.query.parse_natural_language", lambda *a, **k: parsed)
    monkeypatch.setattr("api.query.run_analysis", lambda **k: fake_result())

    def broken(*a, **k):
        raise TimeoutError

    monkeypatch.setattr("api.query.narrate_result", broken)
    body = client.post("/query", json={"query": "flood"}).json()
    assert "42.0 km²" in body["explanation"]


def test_query_reports_a_model_timeout_as_502(client, monkeypatch):
    def slow(*a, **k):
        raise TimeoutError

    monkeypatch.setattr("api.query.parse_natural_language", slow)
    res = client.post("/query", json={"query": "flood"})
    assert res.status_code == 502


def test_no_data_becomes_an_explanation_not_an_error(client, monkeypatch):
    parsed = ParsedQuery(
        understood=True,
        analysis_type="flood_extent",
        bbox=AOI,
        start_date="2025-07-03",
        end_date="2025-07-12",
    )
    monkeypatch.setattr("api.query.parse_natural_language", lambda *a, **k: parsed)

    def no_data(**k):
        raise ValueError("No Sentinel-1 scenes for this area and window.")

    monkeypatch.setattr("api.query.run_analysis", no_data)
    body = client.post("/query", json={"query": "flood"}).json()
    assert body["result"] is None
    assert "No Sentinel-1" in body["explanation"]


def test_manual_sweep_needs_the_operator_token(client, monkeypatch):
    monkeypatch.delenv("SWEEP_TOKEN", raising=False)
    assert client.post("/feed/sweep").status_code == 403
    monkeypatch.setenv("SWEEP_TOKEN", "secret")
    assert client.post("/feed/sweep", headers={"X-Sweep-Token": "wrong"}).status_code == 403
    monkeypatch.setattr("watch.sweeper.trigger_sweep_async", lambda: {"started": True})
    assert client.post("/feed/sweep", headers={"X-Sweep-Token": "secret"}).json() == {"started": True}


def test_briefing_escapes_user_text(client):
    body = {
        "area_name": "<script>alert(1)</script>",
        "prepared_for": "<img src=x onerror=alert(2)>",
        "findings": [
            {
                "analysis_type": "flood_extent",
                "display_name": "Flood <b>Extent</b>",
                "headline_label": "Flooded area",
                "headline_value": 12.5,
                "headline_unit": "km²",
                "data_date": "2025-07-06",
                "start_date": "2025-07-03",
                "end_date": "2025-07-12",
                "confidence": 0.8,
            }
        ],
    }
    page = client.post("/export/briefing", json=body).json()["html"]
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "<img src=x" not in page
    assert "Prem Kamasani and Amogh Vinaykumar" in page


def test_featured_lists_stories_and_rejects_unknown_ids(client):
    stories = client.get("/featured").json()["stories"]
    assert {s["id"] for s in stories} >= {"hill-country-2025", "pakistan-2022"}
    for s in stories:
        assert len(s["bbox"]) == 4 and s["start_date"] < s["end_date"]
    assert client.post("/featured/nope").status_code == 404


def test_district_shaping_keeps_the_largest_ring():
    small = [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]
    big = [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]
    feature = {
        "properties": {"STATE": "48", "BASENAME": "26"},
        "geometry": {"type": "MultiPolygon", "coordinates": [[small], [big]]},
    }
    shaped = districts._shape_district(feature)
    assert shaped["label"] == "TX-26"
    assert shaped["name"] == "Texas District 26"
    assert shaped["bbox"] == [1, 1, 2, 2]


def test_district_lookup_rejects_unknown_states(client):
    assert client.get("/districts/lookup", params={"state": "ZZ", "number": "1"}).status_code == 400


def test_janus_is_open_without_an_access_code(client, tmp_path, monkeypatch):
    from janus import store

    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "janus.db"))
    store.init_db()
    body = client.get("/janus/entitlements", params={"owner": "judge"}).json()
    assert body["locked"] is False
    assert "mentor_chat" in body["features"]


def test_district_lookup_rejects_injected_numbers(client):
    res = client.get("/districts/lookup", params={"state": "TX", "number": "1' OR '1'='1"})
    assert res.status_code == 400


def test_current_congress_rolls_over_on_january_third():
    from datetime import date

    assert districts.current_congress(date(2026, 10, 10)) == 119
    assert districts.current_congress(date(2027, 1, 2)) == 119
    assert districts.current_congress(date(2027, 1, 3)) == 120
