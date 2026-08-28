"""OAuth state and redirect-result redemption use opaque one-time handles."""

from __future__ import annotations

from http import HTTPStatus
from http.cookies import SimpleCookie
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from api import auth
from auth.base_authenticator import ProviderConfigurationError
from flask import Flask
from managers import auth_manager
from managers.auth_transaction_manager import AuthTransactionKind

app = Flask(__name__)


class FakeOAuthAuthenticator:
    """OAuth authenticator test double recording browser and callback inputs."""

    def __init__(self) -> None:
        """Initialize the provider and empty call records."""
        self.provider = SimpleNamespace(id=17)
        self.config: dict = {}
        self.authorization: dict = {}
        self.callback: dict = {}

    @staticmethod
    def uses_pkce() -> bool:
        """Report that this test provider requires PKCE."""
        return True

    @staticmethod
    def generate_code_verifier() -> str:
        """Return a deterministic verifier for assertions."""
        return "server-side-verifier"

    @staticmethod
    def pkce_method() -> str:
        """Return the secure PKCE method under test."""
        return "S256"

    def get_authorization_url(self, redirect_uri: str, state: str, nonce: str, *, code_verifier: str) -> str:
        """Record authorization inputs and return a provider URL."""
        self.authorization = {
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_verifier": code_verifier,
        }
        return f"https://identity.example/authorize?{urlencode({'state': state})}"

    def handle_callback(self, redirect_uri: str, code: str, nonce: str, *, code_verifier: str) -> object:
        """Record callback inputs and return a stable external identity."""
        self.callback = {
            "redirect_uri": redirect_uri,
            "code": code,
            "nonce": nonce,
            "code_verifier": code_verifier,
        }
        return object()


def _transaction_store(monkeypatch) -> tuple[dict, list]:  # noqa: ANN001
    stored: dict[tuple[AuthTransactionKind, str], dict] = {}
    created: list[tuple[AuthTransactionKind, dict, int, str]] = []
    tokens = iter(("A" * 43, "B" * 43, "C" * 43))

    def create(kind: AuthTransactionKind, payload: dict, ttl_seconds: int) -> str:
        token = next(tokens)
        stored[(kind, token)] = payload
        created.append((kind, payload, ttl_seconds, token))
        return token

    def consume(kind: AuthTransactionKind, token: str) -> dict | None:
        return stored.pop((kind, token), None)

    monkeypatch.setattr(auth.auth_transaction_manager, "create", create)
    monkeypatch.setattr(auth.auth_transaction_manager, "consume", consume)
    return stored, created


def test_oauth_state_keeps_pkce_verifier_server_side(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeOAuthAuthenticator()
    _stored, created = _transaction_store(monkeypatch)
    monkeypatch.setattr(auth_manager, "get_oauth_authenticator", lambda _slug: authenticator)

    with app.test_request_context(
        "/api/v1/auth/oauth/corporate/login?gotoUrl=/v2/dashboard",
        base_url="https://taranis.example",
    ):
        response = auth.OAuthLoginRedirect.get.__wrapped__(auth.OAuthLoginRedirect(), "corporate")

    state = parse_qs(urlparse(response.location).query)["state"][0]
    kind, payload, ttl, token = created[0]
    assert kind is AuthTransactionKind.OAUTH_STATE
    assert state == token == "A" * 43
    assert "." not in state
    assert "server-side-verifier" not in state
    assert payload == {
        "provider_id": 17,
        "goto_url": "/v2/dashboard",
        "nonce": authenticator.authorization["nonce"],
        "code_verifier": "server-side-verifier",
        "pkce_method": "S256",
    }
    assert ttl == auth_manager.OAUTH_STATE_MINUTES * 60


def test_legacy_environment_get_callback_accepts_tuple_response(monkeypatch) -> None:  # noqa: ANN001
    _stored, created = _transaction_store(monkeypatch)
    monkeypatch.setattr(
        auth_manager,
        "authenticate",
        lambda _credentials: ({"access_token": "legacy-environment-jwt"}, HTTPStatus.OK),
    )

    with app.test_request_context(
        "/api/v1/auth/login?gotoUrl=/dashboard&code=callback-code",
        base_url="https://taranis.example",
    ):
        response = auth.Login.get.__wrapped__(auth.Login())

    assert response.status_code == HTTPStatus.FOUND
    assert response.location == "/dashboard"
    assert created[0][:3] == (
        AuthTransactionKind.REDIRECT_REDEMPTION,
        {"response": {"access_token": "legacy-environment-jwt"}},
        auth.REDIRECT_REDEMPTION_SECONDS,
    )
    assert "legacy-environment-jwt" not in response.headers["Set-Cookie"]


def test_oauth_callback_and_redirect_result_are_each_redeemable_once(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeOAuthAuthenticator()
    stored, _created = _transaction_store(monkeypatch)
    state = "A" * 43
    stored[(AuthTransactionKind.OAUTH_STATE, state)] = {
        "provider_id": 17,
        "goto_url": "/dashboard",
        "nonce": "oidc-nonce",
        "code_verifier": "server-side-verifier",
        "pkce_method": "S256",
    }
    monkeypatch.setattr(auth_manager, "get_oauth_authenticator", lambda _slug: authenticator)
    monkeypatch.setattr(
        auth_manager,
        "provision_and_issue_jwt",
        lambda _provider, _identity: ({"access_token": "full.jwt.secret"}, HTTPStatus.OK),
    )

    with app.test_request_context(
        f"/api/v1/auth/oauth/corporate/callback?state={state}&code=authorization-code",
        base_url="https://taranis.example",
    ):
        callback_response = auth.OAuthCallback.get.__wrapped__(auth.OAuthCallback(), "corporate")

    assert callback_response.status_code == HTTPStatus.FOUND
    assert callback_response.location == "/dashboard"
    assert authenticator.callback["nonce"] == "oidc-nonce"
    assert authenticator.callback["code_verifier"] == "server-side-verifier"

    set_cookie = callback_response.headers["Set-Cookie"]
    assert "full.jwt.secret" not in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=Strict" in set_cookie
    cookie = SimpleCookie()
    cookie.load(set_cookie)
    redemption_handle = cookie[auth.REDIRECT_REDEMPTION_COOKIE].value
    # Typed Redis namespaces make reuse across transaction kinds harmless.
    assert redemption_handle == "A" * 43

    with app.test_request_context(
        "/api/v1/auth/redeem",
        method="POST",
        base_url="https://taranis.example",
        headers={
            "Cookie": f"{auth.REDIRECT_REDEMPTION_COOKIE}={redemption_handle}",
            "Origin": "https://taranis.example",
            "Sec-Fetch-Site": "same-origin",
        },
    ):
        redemption_response = auth.AuthRedemption.post.__wrapped__(auth.AuthRedemption())
    assert redemption_response.status_code == HTTPStatus.OK
    assert redemption_response.get_json() == {"access_token": "full.jwt.secret"}
    assert redemption_response.headers["Cache-Control"] == "no-store"
    assert f"{auth.REDIRECT_REDEMPTION_COOKIE}=;" in redemption_response.headers["Set-Cookie"]

    with app.test_request_context(
        "/api/v1/auth/redeem",
        method="POST",
        base_url="https://taranis.example",
        headers={"Cookie": f"{auth.REDIRECT_REDEMPTION_COOKIE}={redemption_handle}"},
    ):
        replay_response = auth.AuthRedemption.post.__wrapped__(auth.AuthRedemption())
    # A spent handle is "nothing to redeem", not an authentication failure - and it
    # must stay indistinguishable from never having had one (asserted below).
    assert replay_response.status_code == HTTPStatus.NO_CONTENT
    assert replay_response.headers["Cache-Control"] == "no-store"
    assert f"{auth.REDIRECT_REDEMPTION_COOKIE}=;" in replay_response.headers["Set-Cookie"]

    with app.test_request_context(
        f"/api/v1/auth/oauth/corporate/callback?state={state}&code=authorization-code",
        base_url="https://taranis.example",
    ):
        callback_replay = auth.OAuthCallback.get.__wrapped__(auth.OAuthCallback(), "corporate")
    assert callback_replay == ({"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED)


def test_oauth_state_is_bound_to_provider_and_consumed_on_mismatch(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeOAuthAuthenticator()
    authenticator.provider.id = 99
    stored, _created = _transaction_store(monkeypatch)
    state = "A" * 43
    stored[(AuthTransactionKind.OAUTH_STATE, state)] = {
        "provider_id": 17,
        "goto_url": "/dashboard",
        "nonce": "oidc-nonce",
        "code_verifier": "server-side-verifier",
        "pkce_method": "S256",
    }
    monkeypatch.setattr(auth_manager, "get_oauth_authenticator", lambda _slug: authenticator)

    with app.test_request_context(
        f"/api/v1/auth/oauth/different-provider/callback?state={state}&code=authorization-code",
        base_url="https://taranis.example",
    ):
        mismatch = auth.OAuthCallback.get.__wrapped__(auth.OAuthCallback(), "different-provider")
    assert mismatch == ({"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED)

    with app.test_request_context(
        f"/api/v1/auth/oauth/different-provider/callback?state={state}&code=authorization-code",
        base_url="https://taranis.example",
    ):
        replay = auth.OAuthCallback.get.__wrapped__(auth.OAuthCallback(), "different-provider")
    assert replay == ({"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED)


def test_oauth_callback_rejects_handle_from_another_transaction_kind(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeOAuthAuthenticator()
    stored, _created = _transaction_store(monkeypatch)
    handle = "A" * 43
    stored[(AuthTransactionKind.REDIRECT_REDEMPTION, handle)] = {"response": {"access_token": "jwt"}}
    monkeypatch.setattr(auth_manager, "get_oauth_authenticator", lambda _slug: authenticator)

    with app.test_request_context(
        f"/api/v1/auth/oauth/corporate/callback?state={handle}&code=authorization-code",
        base_url="https://taranis.example",
    ):
        response = auth.OAuthCallback.get.__wrapped__(auth.OAuthCallback(), "corporate")

    assert response == ({"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED)
    assert stored[(AuthTransactionKind.REDIRECT_REDEMPTION, handle)] == {"response": {"access_token": "jwt"}}


def test_refused_client_credentials_are_reported_as_a_misconfiguration(monkeypatch) -> None:  # noqa: ANN001
    """A provider the IdP refuses must not read as the user's authentication failing."""
    authenticator = FakeOAuthAuthenticator()
    stored, _created = _transaction_store(monkeypatch)
    state = "A" * 43
    stored[(AuthTransactionKind.OAUTH_STATE, state)] = {
        "provider_id": 17,
        "goto_url": "/v2/dashboard",
        "nonce": "oidc-nonce",
        "code_verifier": "server-side-verifier",
        "pkce_method": "S256",
    }

    def refuse(*_args: object, **_kwargs: object) -> None:
        msg = "Provider 'Corporate login' rejected our client credentials"
        raise ProviderConfigurationError(msg)

    authenticator.handle_callback = refuse
    monkeypatch.setattr(auth_manager, "get_oauth_authenticator", lambda _slug: authenticator)
    monkeypatch.setattr(
        auth_manager,
        "provision_and_issue_jwt",
        lambda *_args: pytest.fail("no account may be provisioned when the provider itself is refused"),
    )

    with app.test_request_context(
        f"/api/v1/auth/oauth/corporate/callback?state={state}&code=authorization-code",
        base_url="https://taranis.example",
    ):
        response = auth.OAuthCallback.get.__wrapped__(auth.OAuthCallback(), "corporate")

    assert response.status_code == HTTPStatus.FOUND
    assert response.location == "/v2/dashboard?login_error=provider_misconfigured"
    # The IdP's own wording stays in the audit log, never in the browser.
    assert "Corporate login" not in response.location


def test_a_visit_with_no_handle_is_indistinguishable_from_a_spent_one() -> None:
    """The login page asks on every visit, because the handle is HttpOnly.

    Answering that with 401 made every plain visit to /login log a failed request
    in the browser console, which is noise at best and a red herring while
    debugging a real login problem. It must stay indistinguishable from a spent
    or forged handle, so both answer 204 with no body.
    """
    app = Flask(__name__)

    with app.test_request_context(
        "/api/v1/auth/redeem",
        method="POST",
        base_url="https://taranis.example",
        headers={"Origin": "https://taranis.example", "Sec-Fetch-Site": "same-origin"},
    ):
        response = auth.AuthRedemption.post.__wrapped__(auth.AuthRedemption())

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.get_data() == b""
    assert response.headers["Cache-Control"] == "no-store"
