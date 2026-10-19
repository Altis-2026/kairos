"""
An OpenRouter key that is present but rejected, told apart from a flaky
model call.

Reported from production: asking Kairos a plain-language question returned
the OpenAI SDK's raw exception text verbatim — "Query parsing failed: Error
code: 401 - {'error': {'message': 'User not found.', 'code': 401}}" — a
message that names no cause a person reading it could act on. Before this,
`ai/client.py` called the OpenRouter SDK directly from nine places, and
`api/query.py` had exactly two outcomes for anything that call could raise:
`RuntimeError` (the one case it knew was a configuration problem — no key
set at all) got a plain 503; everything else, including an invalid or
revoked key, fell into a generic handler that said "the language model did
not answer in time ... try again in a moment" — advice that is actively
wrong for an error no retry can fix.

These tests exercise `_complete`, the one place every call in that module
now goes through, with the exact exception shape OpenRouter sends for a
dead key (`openai.AuthenticationError`, body `{"error": {"message": "User
not found.", "code": 401}}`) — not a hand-written stand-in for it.
"""
import httpx
import openai
import pytest

from ai.client import _complete, _openrouter_message


def _sdk_error(cls, status: int, message: str):
    """
    Build the real SDK exception OpenRouter's response produces, the same
    way the `openai` client itself constructs one internally — status,
    body shape and `.body` attribute all as a live call would see them, so
    the test is pinned to the SDK's actual behaviour rather than a guess
    about its shape.
    """
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    body = {"error": {"message": message, "code": status}}
    response = httpx.Response(status, request=request, json=body)
    return cls(f"Error code: {status} - {body}", response=response, body=body)


class _FakeCompletions:
    def __init__(self, raises=None, result=None):
        self._raises = raises
        self._result = result
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self._raises:
            raise self._raises
        return self._result


class _FakeClient:
    def __init__(self, raises=None, result=None):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(raises, result)})()


def test_an_invalid_key_becomes_a_plain_runtime_error():
    """
    The exact failure reported in production: a key OpenRouter no longer
    recognises. This must come out as the same exception class a missing
    key produces, not the SDK's own exception leaking through.
    """
    err = _sdk_error(openai.AuthenticationError, 401, "User not found.")
    client = _FakeClient(raises=err)

    with pytest.raises(RuntimeError) as exc_info:
        _complete(client, model="m", messages=[])

    message = str(exc_info.value)
    assert "OPENROUTER_API_KEY" in message
    assert "User not found." in message
    assert "openrouter.ai/keys" in message
    # The misleading advice this replaced must not reappear for this case.
    assert "did not answer in time" not in message
    assert "try again" not in message.lower()


def test_a_revoked_or_wrong_account_key_is_also_caught():
    """PermissionDeniedError (403) is the SDK's other auth-shaped failure —
    e.g. a key valid for a different OpenRouter account or project."""
    err = _sdk_error(openai.PermissionDeniedError, 403, "Insufficient permissions.")
    client = _FakeClient(raises=err)

    with pytest.raises(RuntimeError) as exc_info:
        _complete(client, model="m", messages=[])

    assert "Insufficient permissions." in str(exc_info.value)


def test_a_non_auth_failure_passes_through_unchanged():
    """
    A rate limit, a timeout, a 500 from OpenRouter — none of those are a
    credential problem, and must not be relabelled as one. Only
    authentication/authorization failures get the RuntimeError treatment;
    everything else is the caller's problem to handle as it already does.
    """
    err = _sdk_error(openai.RateLimitError, 429, "Rate limit exceeded.")
    client = _FakeClient(raises=err)

    with pytest.raises(openai.RateLimitError):
        _complete(client, model="m", messages=[])


def test_a_successful_call_is_unaffected():
    """The common case: `_complete` is a transparent pass-through when
    nothing goes wrong."""
    client = _FakeClient(result="ok")
    assert _complete(client, model="m", messages=[]) == "ok"
    assert client.chat.completions.calls == 1


def test_openrouter_message_extracts_the_clean_reason():
    err = _sdk_error(openai.AuthenticationError, 401, "User not found.")
    assert _openrouter_message(err) == "User not found."


def test_openrouter_message_falls_back_when_body_is_unexpected():
    """A differently-shaped error body must not crash the error path
    itself — it should degrade to the exception's own string form."""

    class Weird(Exception):
        body = {"not": "the expected shape"}

    e = Weird("fallback text")
    assert _openrouter_message(e) == "fallback text"

    class NoBody(Exception):
        pass

    e2 = NoBody("also fallback text")
    assert _openrouter_message(e2) == "also fallback text"


# --------------------------------------------------------------------------
# End to end through /query — the actual request shape that hit this in
# production, not just the unit underneath it.
# --------------------------------------------------------------------------

fastapi_testclient = pytest.importorskip("fastapi.testclient")


@pytest.fixture
def client_app(monkeypatch):
    import ai.client as ai_client

    err = _sdk_error(openai.AuthenticationError, 401, "User not found.")
    fake = _FakeClient(raises=err)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake)

    import main

    return fastapi_testclient.TestClient(main.app)


def test_query_endpoint_returns_503_not_a_leaked_sdk_error(client_app):
    """
    The literal production report: POST /query with a real question, a
    dead OpenRouter key behind it. Before this fix the detail string was
    the raw `openai` exception text; now it must be the plain,
    actionable one `_complete` produces, at a status code that tells a
    client this is a configuration problem rather than something retrying
    will fix.
    """
    res = client_app.post(
        "/query",
        json={"query": "Please tell me about the texas hill country floods"},
    )
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert "OPENROUTER_API_KEY" in detail
    assert "User not found." in detail
    assert "Error code: 401" not in detail
    assert "did not answer in time" not in detail


# --------------------------------------------------------------------------
# Janus's mentor chat has its own call site — janus/mentor.py called the SDK
# directly rather than through ai/client.py, so it needed the same fix
# applied separately. This confirms the wiring, not just the mechanism
# already covered above.
# --------------------------------------------------------------------------

from janus import mentor, store  # noqa: E402


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "janus_mentor_test.db"))
    store.init_db()


def test_mentor_turn_raises_a_plain_runtime_error_on_a_dead_key(
    isolated_store, monkeypatch
):
    project = store.create_project("owner-x", "Test project", "A question")
    err = _sdk_error(openai.AuthenticationError, 401, "User not found.")
    monkeypatch.setattr(mentor, "_get_client", lambda: _FakeClient(raises=err))

    with pytest.raises(RuntimeError) as exc_info:
        mentor.run_turn(project["id"], "hello", mode="mentor")

    message = str(exc_info.value)
    assert "OPENROUTER_API_KEY" in message
    assert "User not found." in message


def test_janus_chat_endpoint_returns_503_for_a_dead_key(isolated_store, monkeypatch):
    """The actual HTTP path /janus/projects/{id}/chat goes through, not just
    the function underneath it — the same class of check as the /query test
    above, for the second entry point this session found had the bug."""
    import os

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-not-real")
    owner = "owner-e2e"
    project = store.create_project(owner, "Test project", "A question")

    err = _sdk_error(openai.AuthenticationError, 401, "User not found.")
    monkeypatch.setattr(mentor, "_get_client", lambda: _FakeClient(raises=err))

    import main

    test_client = fastapi_testclient.TestClient(main.app)
    res = test_client.post(
        f"/janus/projects/{project['id']}/chat",
        json={"owner": owner, "message": "hello", "mode": "mentor"},
    )
    assert res.status_code == 503
    assert "OPENROUTER_API_KEY" in res.json()["detail"]
    assert os.getenv("OPENROUTER_API_KEY") == "sk-test-not-real"
