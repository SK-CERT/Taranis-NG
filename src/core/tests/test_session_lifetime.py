"""A sign-in lasts at most security_settings.session_max_hours.

A token lasted four hours and the GUI refreshed it before it ran out, so a session that stayed
open - on a wall display, or in a stolen browser profile - never ended. The token now records its
sign-in time; a refresh carries it over, the token never outlives the session, and a refresh too
close to the end is refused with SESSION_EXPIRED.
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from auth import base_authenticator
from auth.base_authenticator import BaseAuthenticator
from flask import Flask
from managers import auth_manager
from marshmallow import ValidationError
from model import security_settings
from model.security_settings import SecuritySettings

NOW = 1_800_000_000
HOUR = 3600
MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "b3e8d1f5a2c7_session_max_hours.py"


@pytest.fixture
def issued(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """The tokens generate_jwt asks for: their claims and lifetime."""
    tokens: list[dict] = []

    def create_access_token(*, identity: str, additional_claims: dict, expires_delta: timedelta | None) -> str:
        tokens.append({"identity": identity, **additional_claims, "expires_delta": expires_delta})
        return "token"

    monkeypatch.setattr(base_authenticator, "create_access_token", create_access_token)
    monkeypatch.setattr(base_authenticator.time, "time", lambda: NOW)
    monkeypatch.setattr(base_authenticator.log_manager, "store_user_activity", lambda *_args: None)
    monkeypatch.setattr(SecuritySettings, "get_auth_generation", classmethod(lambda _cls: 1))
    monkeypatch.setattr(SecuritySettings, "get_session_max_hours", classmethod(lambda _cls: 24))
    return tokens


@pytest.fixture
def alice() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        username="alice",
        name="Alice",
        password="hash",
        status="active",
        touch_login=lambda: None,
        get_current_organization_name=lambda: "",
        get_permissions=list,
    )


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 4 * HOUR
    with app.app_context():
        yield app


@pytest.mark.usefixtures("app")
def test_a_sign_in_records_its_time(issued: list[dict], alice: SimpleNamespace) -> None:
    assert BaseAuthenticator.generate_jwt(alice)[1] == HTTPStatus.OK

    assert issued[0]["auth_time"] == NOW
    assert issued[0]["expires_delta"] == timedelta(hours=4)


@pytest.mark.usefixtures("app")
def test_a_refresh_keeps_the_sign_in_time_and_never_outlives_the_session(issued: list[dict], alice: SimpleNamespace) -> None:
    signed_in = NOW - 22 * HOUR

    assert auth_manager.refresh(alice, signed_in)[1] == HTTPStatus.OK

    assert issued[0]["auth_time"] == signed_in
    assert issued[0]["expires_delta"] == timedelta(hours=2)


@pytest.mark.usefixtures("app")
@pytest.mark.parametrize("signed_in", [NOW - 24 * HOUR + 599, NOW - 30 * HOUR])
def test_a_refresh_at_the_end_of_the_session_is_refused(issued: list[dict], alice: SimpleNamespace, signed_in: int) -> None:
    body, status = auth_manager.refresh(alice, signed_in)

    assert status == HTTPStatus.UNAUTHORIZED
    assert body["code"] == "SESSION_EXPIRED"
    assert issued == []


@pytest.mark.parametrize("auth_time", [None, "1800000000", True, 1.5])
def test_a_token_without_a_sign_in_time_is_not_refreshed(issued: list[dict], alice: SimpleNamespace, auth_time: object) -> None:
    assert auth_manager.refresh(alice, auth_time)[1] == HTTPStatus.UNAUTHORIZED
    assert issued == []


@pytest.mark.usefixtures("app")
def test_zero_hours_means_no_limit(issued: list[dict], alice: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SecuritySettings, "get_session_max_hours", classmethod(lambda _cls: 0))

    assert auth_manager.refresh(alice, NOW - 1000 * HOUR)[1] == HTTPStatus.OK
    assert issued[0]["expires_delta"] is None


# --- the setting --------------------------------------------------------------------------------


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    record = SimpleNamespace(session_max_hours=24, passkey_enabled=False, get_origins=list)
    monkeypatch.setattr(SecuritySettings, "get", classmethod(lambda _cls: record))
    monkeypatch.setattr(SecuritySettings, "_update_api_key_policy", staticmethod(lambda _record, _new: None))
    monkeypatch.setattr(security_settings.db, "session", SimpleNamespace(commit=lambda: None))
    return record


@pytest.mark.parametrize("hours", [0, 1, 12, 8760])
def test_a_maximum_length_is_stored(stored: SimpleNamespace, hours: int) -> None:
    SecuritySettings.update({"session_max_hours": hours}, "admin")

    assert stored.session_max_hours == hours


@pytest.mark.parametrize("hours", [-1, 8761, "many"])
def test_an_impossible_maximum_length_is_refused(stored: SimpleNamespace, hours: object) -> None:
    with pytest.raises((ValueError, ValidationError), match=r"maximum session length|valid integer"):
        SecuritySettings.update({"session_max_hours": hours}, "admin")

    assert stored.session_max_hours == 24


def test_a_settings_update_without_it_keeps_the_stored_one(stored: SimpleNamespace) -> None:
    stored.session_max_hours = 8

    SecuritySettings.update({"require_mfa": False}, "admin")

    assert stored.session_max_hours == 8


def test_the_migration_adds_the_column_with_the_default() -> None:
    spec = importlib.util.spec_from_file_location("session_max_hours_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert (module.revision, module.down_revision) == ("b3e8d1f5a2c7", "7a4c1e9b2d36")
    assert 'server_default="24"' in MIGRATION.read_text()
