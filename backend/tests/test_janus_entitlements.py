import time

import pytest

from janus import entitlements as ent
from janus import store

REQUIRED_KEYS = {
    "tier",
    "tier_name",
    "blurb",
    "features",
    "project_cap",
    "locked",
    "catalog",
    "skills",
    "unread_insights",
}


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "janus_test.db"))
    store.init_db()


def fresh_owner(name: str) -> str:
    return f"test-owner-{name}-{time.time_ns()}"


def test_every_owner_gets_every_required_key():
    result = ent.entitlements(fresh_owner("new"))
    assert REQUIRED_KEYS <= set(result)
    assert result["locked"] is False
    assert result["skills"] == []
    assert result["unread_insights"] == 0


def test_every_feature_is_open_to_a_new_owner():
    owner = fresh_owner("open")
    for feature in ent.FEATURES:
        ent.require(owner, feature)
    assert set(ent.entitlements(owner)["features"]) == ent.FEATURES


def test_unknown_features_are_refused():
    with pytest.raises(ent.FeatureLocked):
        ent.require(fresh_owner("unknown"), "teleportation")


def test_recorded_skills_reach_entitlements():
    owner = fresh_owner("skilled")
    store.record_skill(owner, "flood extent mapping", "practiced", "ran it twice")
    skills = ent.entitlements(owner)["skills"]
    assert len(skills) == 1
    assert skills[0]["skill"] == "flood extent mapping"
    assert skills[0]["level"] == "practiced"
    assert skills[0]["note"] == "ran it twice"
    assert "updated_at" in skills[0]


def test_skills_never_leak_between_owners():
    other = fresh_owner("other")
    store.record_skill(other, "ship detection", "confident", None)
    assert ent.entitlements(fresh_owner("sibling"))["skills"] == []


def test_project_cap_is_a_positive_number():
    assert ent.project_cap(fresh_owner("cap")) > 0
