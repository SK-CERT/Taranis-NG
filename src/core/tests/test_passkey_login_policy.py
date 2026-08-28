"""A passkey sign-in is a first factor, not a way past the second one.

Passwordless passkey login used to go straight from the assertion to the JWT,
skipping the MFA gate every other login path runs. A user with TOTP enrolled -
or a site demanding a second factor of everyone - therefore signed in with the
passkey alone, and the installation quietly ran on a single factor.

The sign-in now runs the same gate, with two rules of its own: the passkey that
was just presented cannot also count as the second factor, so only TOTP can
satisfy the step; and the login-method level of the policy, which has no
provider to read for a passkey, is taken from the providers the account is
linked to. Where a passkey may be used at all is now two switches rather than
one - ``passkey_first_factor`` and ``passkey_second_factor``.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from auth.base_authenticator import BaseAuthenticator
from managers import auth_manager, webauthn_manager
from model.security_settings import SecuritySettings


@pytest.fixture
def login(monkeypatch) -> SimpleNamespace:  # noqa: ANN001
    """Isolate the login gates from the database, the JWT stack and the activity log."""
    switches = SimpleNamespace(first_factor=True, second_factor=True, site_requires_mfa=False)
    monkeypatch.setattr(webauthn_manager, "passkey_first_factor_enabled", lambda: switches.first_factor)
    monkeypatch.setattr(webauthn_manager, "passkey_second_factor_enabled", lambda: switches.second_factor)
    monkeypatch.setattr(SecuritySettings, "mfa_required", classmethod(lambda _cls: switches.site_requires_mfa))
    monkeypatch.setattr(
        BaseAuthenticator,
        "generate_jwt",
        staticmethod(lambda user: ({"access_token": f"jwt-for-{user.username}"}, HTTPStatus.OK)),
    )
    # The activity log writes to the database; these tests never reach one.
    monkeypatch.setattr(auth_manager.log_manager, "store_auth_error_activity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: None))
    return switches


def _user(**overrides) -> SimpleNamespace:  # noqa: ANN003
    """A user holding one passkey and nothing else."""
    defaults = {
        "username": "alice",
        "status": "active",
        "totp_secret": None,
        "webauthn_credentials": [SimpleNamespace(id=1)],
        "auth_identities": [],
        "organizations": [],
        "require_mfa": False,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _identity_at(*, require_mfa: bool, enabled: bool = True) -> SimpleNamespace:
    """A link to a provider with the given policy."""
    return SimpleNamespace(provider=SimpleNamespace(require_mfa=require_mfa, enabled=enabled))


def _assert_asserts(monkeypatch, user: SimpleNamespace) -> None:  # noqa: ANN001
    """Make the WebAuthn ceremony resolve to this user."""
    monkeypatch.setattr(webauthn_manager, "finish_authentication", lambda _challenge, _credential: user)


def _sign_in() -> tuple[dict, HTTPStatus]:
    return auth_manager.complete_passkey_login("challenge", {"id": "credential"})


def test_passkey_sign_in_alone_is_enough_when_nothing_demands_a_second_factor(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001, ARG001
    """The point of passwordless login survives: no policy, no enrolled TOTP, no extra step."""
    _assert_asserts(monkeypatch, _user())

    response, status = _sign_in()

    assert status == HTTPStatus.OK
    assert response == {"access_token": "jwt-for-alice"}


def test_passkey_sign_in_still_asks_for_the_totp_the_user_enrolled(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001, ARG001
    """A factor the user set up themselves is demanded here as on every other path."""
    _assert_asserts(monkeypatch, _user(totp_secret="seed"))

    response, status = _sign_in()

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "MFA_REQUIRED"
    assert response["methods"] == ["totp"]
    assert response["mfa_token"]


def test_a_passkey_cannot_be_both_factors_of_its_own_login(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001
    """Owning a passkey must not satisfy a step the same passkey just started."""
    login.site_requires_mfa = True
    login.second_factor = True  # accepted as a second factor in general - but not for this login
    _assert_asserts(monkeypatch, _user())

    response, status = _sign_in()

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "MFA_ENROLLMENT_REQUIRED"
    assert response["methods"] == ["totp"]
    assert response["enroll_token"]


def test_a_password_login_still_offers_the_passkey_as_a_second_factor(login: SimpleNamespace) -> None:  # noqa: ARG001
    """The stricter passkey rule must not leak into the paths that were already correct."""
    provider = SimpleNamespace(require_mfa=False)

    response, status = auth_manager._mfa_gate(provider, _user())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "MFA_REQUIRED"
    assert response["methods"] == ["passkey"]


def test_a_passkey_sign_in_inherits_the_policy_of_the_accounts_login_methods(login: SimpleNamespace) -> None:  # noqa: ARG001
    """Otherwise 'require MFA' on a provider would be bypassable by choosing a passkey."""
    user = _user(auth_identities=[_identity_at(require_mfa=True)])

    assert auth_manager.mfa_required(None, user) is True


def test_a_disabled_provider_no_longer_imposes_its_policy(login: SimpleNamespace) -> None:  # noqa: ARG001
    """A login method nobody can use any more must not keep demanding a second factor."""
    user = _user(auth_identities=[_identity_at(require_mfa=True, enabled=False)])

    assert auth_manager.mfa_required(None, user) is False


def test_passkey_sign_in_is_refused_when_it_is_not_a_first_factor(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001
    """With the switch off, neither ceremony step may be reached by calling it directly."""
    login.first_factor = False
    _assert_asserts(monkeypatch, _user())

    begin_response, begin_status = auth_manager.begin_passkey_authentication(None)
    finish_response, finish_status = _sign_in()

    assert (begin_status, begin_response["code"]) == (HTTPStatus.FORBIDDEN, "PASSKEY_LOGIN_DISABLED")
    assert (finish_status, finish_response["code"]) == (HTTPStatus.FORBIDDEN, "PASSKEY_LOGIN_DISABLED")


def test_second_factor_ceremonies_are_refused_when_that_switch_is_off(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001
    """A client holding a valid MFA token must not be able to answer with a passkey anyway."""
    login.second_factor = False
    _assert_asserts(monkeypatch, _user())
    mfa_token = auth_manager.make_scoped_token("alice", "mfa")

    begin_response, begin_status = auth_manager.begin_passkey_authentication(mfa_token)
    finish_response, finish_status = auth_manager.complete_mfa_passkey(mfa_token, "challenge", {"id": "credential"})

    assert (begin_status, begin_response["code"]) == (HTTPStatus.FORBIDDEN, "PASSKEY_NOT_ALLOWED")
    assert (finish_status, finish_response["code"]) == (HTTPStatus.FORBIDDEN, "PASSKEY_NOT_ALLOWED")


def test_an_expired_mfa_token_says_so_instead_of_blaming_the_password(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001, ARG001
    """A dead second-factor step must be reported as what it is.

    The first factor succeeded; only the five-minute scoped token carrying that
    fact ran out. Answering with a bare 401 left the GUI showing "username or
    password is incorrect" on a screen that asks for neither - the reason the
    redirect-login variant of this was so hard to diagnose.
    """
    expired = auth_manager.make_scoped_token("alice", "mfa", expires_minutes=-1)

    begin_response, begin_status = auth_manager.begin_passkey_authentication(expired)
    totp_response, totp_status = auth_manager.complete_mfa_totp(expired, "123456")
    finish_response, finish_status = auth_manager.complete_mfa_passkey(expired, "challenge", {"id": "credential"})

    for response, status in ((begin_response, begin_status), (totp_response, totp_status), (finish_response, finish_status)):
        assert status == HTTPStatus.UNAUTHORIZED
        assert response["code"] == "MFA_TOKEN_INVALID"


def test_an_expired_enrollment_token_says_so_too(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001, ARG001
    """The forced-enrollment step carries the same kind of token and the same risk."""
    expired = auth_manager.make_scoped_token("alice", "mfa_enroll", expires_minutes=-1)

    totp_response, totp_status = auth_manager.complete_totp_enrollment(expired, None)
    passkey_response, passkey_status = auth_manager.complete_passkey_enrollment(expired, None, None, "Passkey")

    assert (totp_status, totp_response["code"]) == (HTTPStatus.UNAUTHORIZED, "MFA_TOKEN_INVALID")
    assert (passkey_status, passkey_response["code"]) == (HTTPStatus.UNAUTHORIZED, "MFA_TOKEN_INVALID")


def test_the_login_page_is_told_whether_a_passkey_may_start_a_login(monkeypatch, login: SimpleNamespace) -> None:  # noqa: ANN001
    """The button has to disappear on its own switch, not on the master one."""
    monkeypatch.setattr(auth_manager.AuthProvider, "get_enabled", classmethod(lambda _cls: []))
    monkeypatch.setattr(webauthn_manager, "passkeys_enabled", lambda: True)
    login.first_factor = False

    methods = auth_manager.get_login_methods()

    assert methods["passkey_enabled"] is True
    assert methods["passkey_login_enabled"] is False
