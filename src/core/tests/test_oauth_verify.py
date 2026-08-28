"""The OIDC/OAuth2 configuration test tells a refused client secret from a refused grant.

Wrong client credentials used to surface only as an opaque failed login, long
after the provider was saved (issue #1515). ``verify_configuration`` puts the
client ID and secret to the provider up front, preferring the checks that test
nothing but the credentials: the introspection and revocation endpoints (client
authentication is their only precondition), then the client_credentials grant,
and only as a last resort an authorization code that was never issued.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar

import pytest
from auth import oauth2_authenticator
from authlib.integrations.base_client import OAuthError

DISCOVERY = {
    "issuer": "https://idp.example.test",
    "authorization_endpoint": "https://idp.example.test/authorize",
    "token_endpoint": "https://idp.example.test/token",
    "userinfo_endpoint": "https://idp.example.test/userinfo",
    "jwks_uri": "https://idp.example.test/jwks",
}

OAUTH2_CONFIG = {
    "authorize_url": "https://login.example.test/authorize",
    "token_url": "https://login.example.test/token",
    "userinfo_url": "https://login.example.test/userinfo",
    "client_id": "taranis",
}


class FakeHttpResponse:
    """Minimal requests response: only the status code carries the probe verdict."""

    def __init__(self, status_code: int) -> None:
        """Record the status code and start unclosed."""
        self.status_code = status_code
        self.closed = False

    def close(self) -> None:
        """Record that the probe released the connection."""
        self.closed = True


def _session_raising(error: Exception | None, *, hint_status: int | None = None) -> type:
    """Return an OAuth2Session double: ``error`` for token requests, ``hint_status`` for hint endpoints."""

    class FakeSession:
        instances: ClassVar[list[FakeSession]] = []

        def __init__(self, client_id: str, secret: str | None = None, **kwargs) -> None:  # noqa: ANN003
            self.client_id = client_id
            self.secret = secret
            self.kwargs = kwargs
            self.grants: list[str] = []
            self.hint_calls: list[tuple[str, str]] = []
            self.responses: list[FakeHttpResponse] = []
            FakeSession.instances.append(self)

        def fetch_token(self, url: str, **kwargs) -> dict:  # noqa: ANN003, ARG002
            self.grants.append(kwargs.get("grant_type", ""))
            if error:
                raise error
            return {"access_token": "unexpected"}

        def _hint(self, method: str, url: str, **_kwargs: object) -> FakeHttpResponse:
            self.hint_calls.append((method, url))
            if hint_status is None:
                msg = "no hint endpoint"
                raise RuntimeError(msg)
            response = FakeHttpResponse(hint_status)
            self.responses.append(response)
            return response

        def introspect_token(self, url: str, **kwargs) -> FakeHttpResponse:  # noqa: ANN003
            return self._hint("introspect_token", url, **kwargs)

        def revoke_token(self, url: str, **kwargs) -> FakeHttpResponse:  # noqa: ANN003
            return self._hint("revoke_token", url, **kwargs)

    FakeSession.instances = []
    return FakeSession


@pytest.fixture
def _no_discovery_needed(monkeypatch) -> None:  # noqa: ANN001
    """Serve the discovery document and JWKS from memory."""
    monkeypatch.setattr(
        oauth2_authenticator,
        "fetch_auth_json",
        lambda url, **_kwargs: DISCOVERY if "openid-configuration" in url else {"keys": []},
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (OAuthError(error="invalid_grant", description="Code not found"), "accepted"),
        (OAuthError(error="unsupported_grant_type", description=None), "accepted"),
        (OAuthError(error="invalid_client", description="Invalid client credentials"), "rejected"),
        # Keycloak answers a wrong secret with unauthorized_client, not invalid_client.
        (OAuthError(error="unauthorized_client", description="Invalid client or Invalid client credentials"), "rejected"),
        (OAuthError(error="temporarily_unavailable", description="Try later"), "inconclusive"),
    ],
)
def test_client_credentials_verdict_follows_the_token_endpoint_error(monkeypatch, error, expected) -> None:  # noqa: ANN001

    session = _session_raising(error)
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", session)

    result = oauth2_authenticator.verify_configuration("oauth2", OAUTH2_CONFIG, "s3cret", "https://taranis.example/callback")

    assert result["client_status"] == expected
    assert result["token_url"] == OAUTH2_CONFIG["token_url"]
    # The probe is only meaningful if it actually presents the configured credentials.
    assert (session.instances[0].client_id, session.instances[0].secret) == ("taranis", "s3cret")
    assert result["has_secret"] is True


def test_bare_401_without_a_parsable_body_still_counts_as_a_rejection(monkeypatch) -> None:  # noqa: ANN001
    unauthorized = RuntimeError("no JSON body")
    unauthorized.response = SimpleNamespace(status_code=401)
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", _session_raising(unauthorized))

    result = oauth2_authenticator.verify_configuration("oauth2", OAUTH2_CONFIG, "s3cret")

    assert result["client_status"] == "rejected"


def test_unreachable_token_endpoint_is_reported_rather_than_raised(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", _session_raising(OSError("connection refused")))

    result = oauth2_authenticator.verify_configuration("oauth2", OAUTH2_CONFIG, "s3cret")

    assert result["client_status"] == "inconclusive"
    assert "connection refused" in result["detail"]


def test_oidc_reports_the_discovered_endpoints_and_signing_keys(monkeypatch, _no_discovery_needed) -> None:  # noqa: ANN001, PT019
    monkeypatch.setattr(
        oauth2_authenticator,
        "OAuth2Session",
        _session_raising(OAuthError(error="invalid_grant", description="Code not found")),
    )
    monkeypatch.setattr(oauth2_authenticator.pyjwt, "PyJWKSet", SimpleNamespace(from_dict=lambda _jwks: SimpleNamespace(keys=[])))

    result = oauth2_authenticator.verify_configuration(
        "oidc",
        {"issuer_url": "https://idp.example.test", "client_id": "taranis"},
        "s3cret",
        "https://taranis.example/callback",
    )

    assert result["client_status"] == "accepted"
    assert result["issuer"] == "https://idp.example.test"
    assert result["authorize_url"] == DISCOVERY["authorization_endpoint"]
    assert result["userinfo_url"] == DISCOVERY["userinfo_endpoint"]
    assert result["signing_key_count"] == 0


def test_discovery_issuer_mismatch_is_a_configuration_error(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(oauth2_authenticator, "fetch_auth_json", lambda _url, **_kwargs: {**DISCOVERY, "issuer": "https://evil.example"})

    with pytest.raises(ValueError, match="issuer does not match"):
        oauth2_authenticator.verify_configuration("oidc", {"issuer_url": "https://idp.example.test", "client_id": "taranis"}, "s3cret")


def test_a_missing_client_id_is_refused_before_any_request_goes_out(monkeypatch) -> None:  # noqa: ANN001
    def explode(*_args: object, **_kwargs: object) -> None:
        pytest.fail("no outbound request may be made without a client ID")

    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", explode)

    with pytest.raises(ValueError, match="No client ID"):
        oauth2_authenticator.verify_configuration("oauth2", {**OAUTH2_CONFIG, "client_id": ""}, "s3cret")


def test_only_oauth_kinds_can_be_tested() -> None:
    with pytest.raises(ValueError, match=r"Only OIDC and OAuth 2\.0"):
        oauth2_authenticator.verify_configuration("saml", {}, None)


OIDC_WITH_HINT_ENDPOINTS = {
    **DISCOVERY,
    "introspection_endpoint": "https://idp.example.test/introspect",
    "revocation_endpoint": "https://idp.example.test/revoke",
}


@pytest.fixture
def _discovery_with_hint_endpoints(monkeypatch) -> None:  # noqa: ANN001
    """Serve a discovery document that advertises introspection and revocation."""
    monkeypatch.setattr(
        oauth2_authenticator,
        "fetch_auth_json",
        lambda url, **_kwargs: OIDC_WITH_HINT_ENDPOINTS if "openid-configuration" in url else {"keys": []},
    )
    monkeypatch.setattr(oauth2_authenticator.pyjwt, "PyJWKSet", SimpleNamespace(from_dict=lambda _jwks: SimpleNamespace(keys=[])))


def _verify_oidc(secret: str | None = "s3cret") -> dict:  # noqa: S107 - a throwaway value for the test double
    return oauth2_authenticator.verify_configuration(
        "oidc",
        {"issuer_url": "https://idp.example.test", "client_id": "taranis"},
        secret,
        "https://taranis.example/callback",
    )


@pytest.mark.parametrize(("hint_status", "expected"), [(200, "accepted"), (401, "rejected")])
def test_introspection_decides_the_credentials_on_its_own(monkeypatch, _discovery_with_hint_endpoints, hint_status, expected) -> None:  # noqa: ANN001, PT019
    """Client authentication is the introspection endpoint's only precondition, so it is decisive."""
    session = _session_raising(None, hint_status=hint_status)
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", session)

    result = _verify_oidc()

    assert result["client_status"] == expected
    probe = session.instances[0]
    assert probe.hint_calls == [("introspect_token", OIDC_WITH_HINT_ENDPOINTS["introspection_endpoint"])]
    # A decisive answer must not be second-guessed by weaker probes.
    assert probe.grants == []
    assert all(response.closed for response in probe.responses)


def test_an_unusable_introspection_endpoint_falls_through_to_the_next_probe(monkeypatch, _discovery_with_hint_endpoints) -> None:  # noqa: ANN001, PT019
    """A 404 says nothing about the credentials, so the chain must keep going."""
    session = _session_raising(OAuthError(error="unsupported_grant_type", description=None), hint_status=404)
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", session)

    result = _verify_oidc()

    assert result["client_status"] == "accepted"
    probe = session.instances[0]
    assert [call[0] for call in probe.hint_calls] == ["introspect_token", "revoke_token"]
    assert probe.grants == ["client_credentials"]


def test_the_authorization_code_fallback_never_claims_a_secret_it_could_not_check(monkeypatch) -> None:  # noqa: ANN001
    """Without introspection or revocation, invalid_grant cannot prove the secret was read."""
    session = _session_raising(OAuthError(error="invalid_grant", description="Code not found"))
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", session)

    result = oauth2_authenticator.verify_configuration("oauth2", OAUTH2_CONFIG, "s3cret")

    # client_credentials answered invalid_grant, which is already post-authentication.
    assert result["client_status"] == "accepted"
    assert session.instances[0].grants == ["client_credentials"]


def test_a_public_client_is_told_the_secret_was_not_what_passed(monkeypatch, _discovery_with_hint_endpoints) -> None:  # noqa: ANN001, PT019
    """With no secret configured, a pass proves the client ID exists and nothing more."""
    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", _session_raising(None, hint_status=200))

    result = _verify_oidc(secret=None)

    assert result["client_status"] == "accepted"
    assert result["has_secret"] is False
    assert "no client secret is configured" in result["detail"]


PUBLIC = DISCOVERY["issuer"]
INTERNAL = "https://kc.internal:8443"


def test_verify_configuration_fetches_discovery_from_internal_issuer(monkeypatch) -> None:  # noqa: ANN001
    """BUG 1: the Test-configuration button must use the back-channel URL."""
    seen: list[str] = []

    def fake_fetch(url, **_kwargs) -> dict:  # noqa: ANN001, ANN003
        seen.append(url)
        return DISCOVERY if "openid-configuration" in url else {"keys": []}

    monkeypatch.setattr(oauth2_authenticator, "fetch_auth_json", fake_fetch)
    monkeypatch.setattr(oauth2_authenticator.pyjwt, "PyJWKSet", SimpleNamespace(from_dict=lambda _jwks: SimpleNamespace(keys=[])))
    monkeypatch.setattr(
        oauth2_authenticator,
        "OAuth2Session",
        _session_raising(OAuthError(error="invalid_grant", description="Code not found")),
    )

    result = oauth2_authenticator.verify_configuration(
        "oidc",
        {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL, "client_id": "taranis"},
        None,
    )

    assert seen[0] == f"{INTERNAL}/.well-known/openid-configuration"
    # The signing keys are a back-channel fetch too, so they come from the internal host.
    assert seen[1] == f"{INTERNAL}/jwks"
    # ...while the identity reported back to the administrator stays the public issuer.
    assert result["issuer"] == PUBLIC
