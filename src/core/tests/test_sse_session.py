"""An SSE session keeps the token's claims, not the token.

``/sse-init`` used to store the raw bearer JWT in Redis for a day, under ``jwt:<jti>``. Redis
has no password and every container on the compose network reaches it, so one compromised
collector or public-web container could list the keys and use every open GUI session - an
administrator's included. A stream, once open, also outlived the logout that should end it.
"""

from __future__ import annotations

import json
import time
import types
from http import HTTPStatus

import pytest
from api import sse
from flask import Flask
from managers import auth_manager
from model.security_settings import SecuritySettings
from model.token_blacklist import TokenBlacklist

APP = Flask(__name__)
JTI = "6f1c2a7e-3b4d-4e5f-8a9b-0c1d2e3f4a5b"
SID = "0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a"
TOKEN = "header.payload.signature"


class FakeRedis:
    """Keeps values and their TTLs in dicts."""

    def __init__(self) -> None:
        """Start empty."""
        self.values: dict[str, str] = {}
        self.ttl: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int) -> None:
        """Store a value with its TTL."""
        self.values[key], self.ttl[key] = value, ex

    def get(self, key: str) -> str | None:
        """Read a value."""
        return self.values.get(key)

    def exists(self, key: str) -> int:
        """Count the key, as Redis does."""
        return int(key in self.values)


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    fake = FakeRedis()
    monkeypatch.setattr(sse, "redis_client", fake)
    return fake


@pytest.fixture
def account(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    state = types.SimpleNamespace(active=True, logged_out=set(), generation=1, credential="cred-1")
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", classmethod(lambda _cls: state.generation))
    monkeypatch.setattr(
        TokenBlacklist,
        "is_blacklisted",
        classmethod(lambda _cls, jti, session_id=None: jti in state.logged_out or f"sid:{session_id}" in state.logged_out),
    )
    monkeypatch.setattr(auth_manager, "_credential_is_current", lambda claims: claims.get("cred") == state.credential)
    monkeypatch.setattr(auth_manager, "_find_active_user", lambda sub: types.SimpleNamespace(username=sub) if state.active else None)
    for name in ("store_auth_warning_activity", "store_auth_error_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return state


def _init(redis: FakeRedis, monkeypatch: pytest.MonkeyPatch, expires_in: int = 3600, **changes: object) -> object:
    claims = {
        "sub": "admin",
        "jti": JTI,
        "exp": int(time.time()) + expires_in,
        "auth_generation": 1,
        "sid": SID,
        "cred": "cred-1",
        "user_claims": {"permissions": ["X"]},
        **changes,
    }
    monkeypatch.setattr(sse, "get_jwt", lambda: claims)
    with APP.test_request_context("/api/v1/sse-init", method="POST", headers={"Authorization": f"Bearer {TOKEN}"}):
        response = sse.SseInitResource.post.__wrapped__(sse.SseInitResource())
    assert response.status_code == HTTPStatus.OK
    return redis.values[f"sse:{JTI}"]


def _open(cookie: str = JTI) -> tuple:
    with APP.test_request_context("/sse", headers={"Cookie": f"jwt_id={cookie}"}):
        result = sse.SseResource().get()
    return result if isinstance(result, tuple) else (result, result.status_code)


def test_the_session_stores_claims_and_never_the_token(redis: FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    stored = _init(redis, monkeypatch, expires_in=3600)

    assert TOKEN not in stored
    assert json.loads(stored) == {
        "sub": "admin",
        "jti": JTI,
        "exp": json.loads(stored)["exp"],
        "auth_generation": 1,
        "sid": SID,
        "cred": "cred-1",
    }
    assert not any(key.startswith("jwt:") for key in redis.values)
    # It lapses with the token, not a day later.
    assert 3590 <= redis.ttl[f"sse:{JTI}"] <= 3600


@pytest.mark.usefixtures("account")
def test_an_active_user_with_a_valid_session_gets_the_stream(redis: FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    _init(redis, monkeypatch)

    response, status = _open()

    assert status == HTTPStatus.OK
    assert response.mimetype == "text/event-stream"


@pytest.mark.parametrize("change", ["logged_out", "signed_out", "password", "disabled", "generation", "expired", "unknown"])
def test_a_session_that_no_longer_holds_is_refused(
    redis: FakeRedis,
    account: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    _init(redis, monkeypatch, expires_in=-5 if change == "expired" else 3600)
    if change == "logged_out":
        account.logged_out.add(JTI)
    elif change == "signed_out":  # logged out with another token of the same sign-in (a refreshed one)
        account.logged_out.add(f"sid:{SID}")
    elif change == "password":  # the password changed since the session was opened
        account.credential = "cred-2"
    elif change == "disabled":
        account.active = False
    elif change == "generation":
        account.generation = 2

    _body, status = _open("00000000-0000-0000-0000-000000000000" if change == "unknown" else JTI)

    assert status == HTTPStatus.FORBIDDEN


@pytest.mark.usefixtures("account")
@pytest.mark.parametrize("missing", ["sid", "cred"])
def test_a_session_opened_without_its_sign_in_s_claims_is_refused(redis: FakeRedis, monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    _init(redis, monkeypatch, **{missing: None})

    assert _open()[1] == HTTPStatus.FORBIDDEN


@pytest.mark.usefixtures("account")
def test_a_cookie_that_is_not_a_jti_is_not_looked_up(redis: FakeRedis) -> None:
    redis.values["sse:*"] = json.dumps({"sub": "admin"})

    assert _open("*")[1] == HTTPStatus.FORBIDDEN


def test_an_open_stream_ends_with_its_session(redis: FakeRedis) -> None:
    redis.values["sse:x"] = "{}"
    assert sse.session_open("sse:x") is True
    assert sse.session_open(None) is True  # a node's stream has no session

    del redis.values["sse:x"]  # logout

    assert sse.session_open("sse:x") is False
