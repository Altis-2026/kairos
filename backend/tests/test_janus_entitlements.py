"""
Janus entitlements: the contract every render of the panel depends on.

Every field asserted here is one the frontend's `Entitlements` TypeScript
type declares as required and reads without an optional-chain — most
pointedly `entitlements.skills.length`, reached unconditionally once a tier
is unlocked. There is no React error boundary anywhere in the app, so a
missing key here does not degrade the panel: it throws during render,
React unmounts the whole tree with nothing there to catch it, and every
control on the page — not just Janus — stops responding. That is the
literal failure mode a payload shaped wrong here produces, so the shape is
tested as its own contract rather than trusted to match the frontend by
inspection.

`skills` and `unread_insights` are owner-scoped state from `janus.store`,
not tier configuration, and both existed there — `record_skill`,
`get_skills`, `unread_insight_count` — before `entitlements()` was ever
wired to read them. The gap between "the data exists" and "the endpoint
returns it" is exactly the kind of thing that looks fine in every code
review and breaks on the one path nobody exercised: an owner who actually
redeems the code.
"""
import time

import pytest

from janus import entitlements as ent
from janus import store


#: Every key the frontend's Entitlements type declares. A response missing
#: any of these is not "incomplete" from the frontend's point of view — the
#: type says it is always present, so the panel reads it unconditionally.
REQUIRED_KEYS = {
    "tier", "tier_name", "blurb", "features", "project_cap",
    "locked", "catalog", "skills", "unread_insights",
}


@pytest.fixture(autouse=True)
def _isolated_owner(tmp_path, monkeypatch):
    """Point the store at a scratch database so tests never share state."""
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "janus_test.db"))
    store.init_db()


def fresh_owner(name: str) -> str:
    return f"test-owner-{name}-{time.time_ns()}"


def test_a_locked_owner_gets_every_required_key():
    owner = fresh_owner("locked")
    result = ent.entitlements(owner)
    assert REQUIRED_KEYS <= set(result)
    assert result["locked"] is True
    assert result["skills"] == []
    assert result["unread_insights"] == 0


def test_an_unlocked_owner_gets_every_required_key():
    """
    The path that actually crashed: `skills` and `unread_insights` were
    silently absent for exactly the owner state a successful code redemption
    produces — the entitlements were correct in every other field, so
    nothing about the response looked obviously broken.
    """
    owner = fresh_owner("unlocked")
    assert ent.redeem(owner, ent.access_code())
    result = ent.entitlements(owner)
    assert REQUIRED_KEYS <= set(result)
    assert result["locked"] is False
    assert isinstance(result["skills"], list)
    assert isinstance(result["unread_insights"], int)


def test_skills_reach_entitlements_after_being_recorded():
    """
    `record_skill` is real, working, and used by the mentor's own tool
    calls (see janus/tools.py) — the storage layer was never the gap. This
    is the wiring `entitlements()` was missing: the data existed and simply
    was not being read.
    """
    owner = fresh_owner("skilled")
    ent.redeem(owner, ent.access_code())
    store.record_skill(owner, "flood extent mapping", "practiced", "ran it twice")

    result = ent.entitlements(owner)
    assert len(result["skills"]) == 1
    skill = result["skills"][0]
    assert skill["skill"] == "flood extent mapping"
    assert skill["level"] == "practiced"
    assert skill["note"] == "ran it twice"
    assert "updated_at" in skill


def test_a_locked_owner_never_sees_another_owners_skills():
    """Skills are owner-scoped; a fresh, locked owner must never leak them."""
    other = fresh_owner("other")
    ent.redeem(other, ent.access_code())
    store.record_skill(other, "ship detection", "confident", None)

    locked = fresh_owner("locked-sibling")
    result = ent.entitlements(locked)
    assert result["skills"] == []


def test_catalog_never_offers_the_tier_the_owner_is_already_on():
    owner = fresh_owner("catalog")
    ent.redeem(owner, ent.access_code())
    ids = {c["id"] for c in ent.entitlements(owner)["catalog"]}
    assert "early_access" not in ids
    assert "locked" not in ids


def test_the_wrong_code_stays_locked_and_still_returns_every_key():
    owner = fresh_owner("wrong-code")
    assert ent.redeem(owner, "definitely-not-it") is False
    result = ent.entitlements(owner)
    assert REQUIRED_KEYS <= set(result)
    assert result["locked"] is True


def test_the_access_code_is_case_insensitive_and_trims_whitespace():
    owner = fresh_owner("case")
    assert ent.redeem(owner, f"  {ent.access_code().upper()}  ") is True
    assert ent.entitlements(owner)["locked"] is False
