"""Wrong second-factor codes are counted even when the password was right.

A right password cleared the failure counter before the MFA step, and the TOTP step counts its
wrong codes on that same counter: whoever knew the password could alternate a sign-in and four
wrong codes for ever, and so try every code. The counter is now cleared only once a session
token is issued. Removing one's TOTP while signed in checked a code with no limit at all.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from api import user as user_api
from auth.base_authenticator import BaseAuthenticator
from flask import Flask
from managers import auth_manager, login_throttle, webauthn_manager
from model.security_settings import SecuritySettings

RIGHT_PASSWORD = "correct horse"
RIGHT_CODE = "123456"
WRONG_CODE = "000000"

app = Flask(__name__)


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int = 0) -> None:  # noqa: ARG002 - the TTL is test_login_throttle.py's
        self.store[key] = value

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(login_throttle, "redis_client", fake)
    return fake


@pytest.fixture
def alice(monkeypatch: pytest.MonkeyPatch, redis: _FakeRedis) -> SimpleNamespace:  # noqa: ARG001
    """An account with a password and TOTP; the code checks are recorded."""
    account = SimpleNamespace(
        username="alice",
        status="active",
        totp_secret="seed",
        webauthn_credentials=[],
        auth_identities=[],
        organizations=[],
        require_mfa=False,
        codes_checked=[],
    )

    def verify_code(_user: SimpleNamespace, code: str) -> bool:
        account.codes_checked.append(code)
        return code == RIGHT_CODE

    monkeypatch.setattr(auth_manager.AuthProvider, "get_enabled_by_kind", lambda _kinds: [SimpleNamespace(kind="local", require_mfa=False)])
    monkeypatch.setattr(
        auth_manager.PasswordAuthenticator,
        "verify",
        lambda credentials: account if credentials["password"] == RIGHT_PASSWORD else None,
    )
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, username: account if username == "alice" else None))
    monkeypatch.setattr(auth_manager.totp_manager, "verify_code", verify_code)
    monkeypatch.setattr(webauthn_manager, "passkey_second_factor_enabled", lambda: False)
    monkeypatch.setattr(SecuritySettings, "mfa_required", classmethod(lambda _cls: False))
    monkeypatch.setattr(
        BaseAuthenticator,
        "generate_jwt",
        staticmethod(lambda user: ({"access_token": f"jwt-for-{user.username}"}, HTTPStatus.OK)),
    )
    monkeypatch.setattr(auth_manager.time, "sleep", lambda _seconds: None)
    for name in ("store_auth_error_activity", "store_auth_warning_activity", "store_user_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return account


def _sign_in(username: str = "alice", password: str = RIGHT_PASSWORD) -> tuple[dict, HTTPStatus]:
    with app.test_request_context("/api/v1/auth/login", method="POST", json={"username": username}):
        return auth_manager.authenticate_with_provider(None, {"username": username, "password": password})


def _failures(username: str = "alice", namespace: str = login_throttle.LOGIN) -> int:
    return login_throttle._read(username, namespace)[0]


def test_wrong_codes_after_a_right_password_reach_the_lock(alice: SimpleNamespace) -> None:
    """Sign in, four wrong codes, sign in again, ...: the fifth wrong code locks the account."""
    refused = 0
    for _round in range(5):
        body, _status = _sign_in()
        if body.get("code") != "MFA_REQUIRED":
            refused += 1
            continue
        for _guess in range(login_throttle.FAIL_THRESHOLD - 1):
            auth_manager.complete_mfa_totp(body["mfa_token"], WRONG_CODE)

    assert len(alice.codes_checked) == login_throttle.FAIL_THRESHOLD
    assert login_throttle.is_locked("alice")
    assert refused == 3  # the sign-ins after the lock
    assert _sign_in()[0] == {"error": "Authentication failed"}


def test_a_right_password_alone_clears_nothing(alice: SimpleNamespace) -> None:  # noqa: ARG001
    for _ in range(3):
        login_throttle.register_failure("alice")

    body, _status = _sign_in()

    assert body["code"] == "MFA_REQUIRED"
    assert _failures() == 3


def test_a_completed_sign_in_clears_the_counter(alice: SimpleNamespace) -> None:  # noqa: ARG001
    for _ in range(3):
        login_throttle.register_failure("alice")
    body, _status = _sign_in()
    assert auth_manager.complete_mfa_totp(body["mfa_token"], WRONG_CODE)[0]["code"] == "TOTP_INVALID"
    assert _failures() == 4

    assert auth_manager.complete_mfa_totp(body["mfa_token"], RIGHT_CODE) == ({"access_token": "jwt-for-alice"}, HTTPStatus.OK)
    assert _failures() == 0


def test_a_sign_in_without_a_second_step_clears_the_counter_of_the_name_typed(alice: SimpleNamespace) -> None:
    alice.totp_secret = None
    for _ in range(3):
        login_throttle.register_failure(" Alice ")

    assert _sign_in(" Alice ") == ({"access_token": "jwt-for-alice"}, HTTPStatus.OK)
    assert _failures() == 0


def test_a_right_password_of_a_disabled_account_clears_nothing(alice: SimpleNamespace) -> None:
    alice.status = "disabled"
    login_throttle.register_failure("alice")

    assert _sign_in()[0]["code"] == "ACCOUNT_DISABLED"
    assert _failures() == 1


def test_wrong_passkeys_in_the_mfa_step_are_counted_and_a_right_one_clears(alice: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    alice.totp_secret = None
    alice.webauthn_credentials = [SimpleNamespace(id=1)]
    monkeypatch.setattr(webauthn_manager, "passkey_second_factor_enabled", lambda: True)
    asserted = {"owner": None}
    monkeypatch.setattr(webauthn_manager, "finish_authentication", lambda _challenge, _credential: asserted["owner"])
    body, _status = _sign_in()
    assert body["methods"] == ["passkey"]

    for _ in range(login_throttle.FAIL_THRESHOLD - 1):
        assert auth_manager.complete_mfa_passkey(body["mfa_token"], "challenge", {"id": "other"})[1] == HTTPStatus.UNAUTHORIZED
    assert _failures() == login_throttle.FAIL_THRESHOLD - 1

    asserted["owner"] = alice
    assert auth_manager.complete_mfa_passkey(body["mfa_token"], "challenge", {"id": "mine"}) == (
        {"access_token": "jwt-for-alice"},
        HTTPStatus.OK,
    )
    assert _failures() == 0


def test_a_locked_account_finishes_no_passkey_mfa_step(alice: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    alice.totp_secret = None
    alice.webauthn_credentials = [SimpleNamespace(id=1)]
    monkeypatch.setattr(webauthn_manager, "passkey_second_factor_enabled", lambda: True)
    monkeypatch.setattr(webauthn_manager, "finish_authentication", lambda _challenge, _credential: pytest.fail("no assertion may be checked"))
    body, _status = _sign_in()
    for _ in range(login_throttle.FAIL_THRESHOLD):
        login_throttle.register_failure("alice")

    response, status = auth_manager.complete_mfa_passkey(body["mfa_token"], "challenge", {"id": "mine"})

    assert (status, response["code"]) == (HTTPStatus.UNAUTHORIZED, "MFA_TOKEN_INVALID")


# --- removing one's TOTP while signed in --------------------------------------------------------


@pytest.fixture
def remove_totp(alice: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Call DELETE /users/my-totp as alice; returns the codes the removal checked."""
    checked: list[str] = []

    def disable(_user: SimpleNamespace, code: str) -> bool:
        checked.append(code)
        return code == RIGHT_CODE

    monkeypatch.setattr(user_api.auth_manager, "get_user_from_jwt", lambda: alice)
    monkeypatch.setattr(user_api.totp_manager, "disable", disable)
    monkeypatch.setattr(user_api.notification_manager, "notify_user", lambda *_args, **_kwargs: None)
    return checked


def _delete_totp(code: str) -> tuple[dict, HTTPStatus]:
    with app.test_request_context("/api/v1/users/my-totp", method="DELETE", json={"code": code}):
        return user_api.UserTotp.delete.__wrapped__(user_api.UserTotp())


def test_removing_one_s_totp_is_refused_after_too_many_wrong_codes(remove_totp: list[str]) -> None:
    for _ in range(login_throttle.FAIL_THRESHOLD):
        assert _delete_totp(WRONG_CODE)[1] == HTTPStatus.BAD_REQUEST

    response, status = _delete_totp(RIGHT_CODE)

    assert status == HTTPStatus.TOO_MANY_REQUESTS
    assert "try again later" in response["error"]
    assert remove_totp == [WRONG_CODE] * login_throttle.FAIL_THRESHOLD  # the right one was not even checked
    # A typo spree in the profile dialog does not lock the person's sign-in.
    assert not login_throttle.is_locked("alice")


def test_a_right_code_removes_the_totp_and_clears_its_counter(remove_totp: list[str]) -> None:  # noqa: ARG001
    for _ in range(login_throttle.FAIL_THRESHOLD - 1):
        _delete_totp(WRONG_CODE)
    for _ in range(login_throttle.FAIL_THRESHOLD):
        login_throttle.register_failure("alice")  # a locked sign-in does not block a signed-in session

    assert _delete_totp(RIGHT_CODE) == ({"enabled": False}, HTTPStatus.OK)
    assert _failures(namespace=login_throttle.SIGNED_IN) == 0
