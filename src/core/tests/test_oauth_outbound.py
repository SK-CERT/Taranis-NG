"""Focused OAuth/OIDC PKCE and outbound-request security tests."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from auth import oauth2_authenticator
from auth.oauth2_authenticator import OAuth2Authenticator
from auth.url_guard import MAX_JSON_BYTES, OUTBOUND_TIMEOUT, assert_auth_endpoint_url, fetch_auth_json, read_limited_json


class FakeResponse:
    """Minimal streaming requests response used by the outbound guard tests."""

    def __init__(self, body: bytes = b"{}", *, status_code: int = 200, headers: dict | None = None) -> None:
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.is_redirect = status_code in {301, 302, 303, 307, 308}
        self.is_permanent_redirect = status_code in {301, 308}
        self.closed = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset : offset + chunk_size]

    def close(self) -> None:
        self.closed = True


def _provider(kind: str = "oauth2", **config) -> SimpleNamespace:
    defaults = {
        "authorize_url": "https://login.example.test/authorize",
        "token_url": "https://login.example.test/token",
        "userinfo_url": "https://login.example.test/userinfo",
        "client_id": "taranis",
        "pkce_method": "S256",
    }
    defaults.update(config)
    return SimpleNamespace(
        id=17,
        name="Corporate login",
        kind=kind,
        config=defaults,
        updated_at="marker",
        get_secret_plaintext=lambda: "secret",
    )


def test_private_https_auth_endpoint_remains_compatible() -> None:
    assert_auth_endpoint_url("https://10.20.30.40/realms/internal")


@pytest.mark.parametrize(
    "url",
    ["http://idp.example.test/token", "https://user:pass@idp.example.test/token", "https://idp.example.test/token#fragment"],
)
def test_insecure_auth_endpoint_is_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        assert_auth_endpoint_url(url)


@pytest.mark.parametrize("url", ["http://localhost:8080/token", "http://127.0.0.1:8080/token", "http://[::1]:8080/token"])
def test_loopback_http_auth_endpoint_remains_available_for_development(url: str) -> None:
    assert_auth_endpoint_url(url)


def test_auth_json_fetch_disables_redirects_sets_timeouts_and_closes() -> None:
    response = FakeResponse(b'{"issuer":"https://idp.example.test"}')
    calls: list[tuple[str, dict]] = []

    def request_get(url: str, **kwargs) -> FakeResponse:
        calls.append((url, kwargs))
        return response

    result = fetch_auth_json("https://idp.example.test/.well-known/openid-configuration", request_get=request_get)

    assert result["issuer"] == "https://idp.example.test"
    assert calls == [
        (
            "https://idp.example.test/.well-known/openid-configuration",
            {"timeout": OUTBOUND_TIMEOUT, "allow_redirects": False, "stream": True},
        ),
    ]
    assert response.closed is True


def test_auth_json_rejects_redirect_and_oversized_stream() -> None:
    with pytest.raises(ValueError, match="redirect"):
        read_limited_json(FakeResponse(status_code=302))
    with pytest.raises(ValueError, match="exceeds"):
        read_limited_json(FakeResponse(b"x" * (MAX_JSON_BYTES + 1)))


def test_pkce_plain_and_none_are_explicitly_supported_but_unknown_values_fail() -> None:
    assert OAuth2Authenticator(_provider(pkce_method="plain")).pkce_method() == "plain"
    assert OAuth2Authenticator(_provider(pkce_method="none")).pkce_method() == "none"
    with pytest.raises(ValueError, match="Unsupported PKCE method 'legacy'"):
        OAuth2Authenticator(_provider(pkce_method="legacy")).pkce_method()


def test_s256_authorization_url_contains_only_the_challenge() -> None:
    authenticator = OAuth2Authenticator(_provider())
    verifier = authenticator.generate_code_verifier()

    url = authenticator.get_authorization_url("https://taranis.example.test/callback", "opaque-state", "nonce", verifier)
    query = parse_qs(urlparse(url).query)

    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0] != verifier
    assert verifier not in url


def test_plain_authorization_url_uses_the_verifier_as_an_explicit_legacy_challenge() -> None:
    authenticator = OAuth2Authenticator(_provider(pkce_method="plain"))
    verifier = authenticator.generate_code_verifier()

    url = authenticator.get_authorization_url("https://taranis.example.test/callback", "opaque-state", "nonce", verifier)
    query = parse_qs(urlparse(url).query)

    assert query["code_challenge_method"] == ["plain"]
    assert query["code_challenge"] == [verifier]


def test_oidc_discovery_requires_matching_issuer(monkeypatch) -> None:
    provider = _provider(kind="oidc", issuer_url="https://idp.example.test", pkce_method="S256")
    provider.config.pop("authorize_url")
    provider.config.pop("token_url")
    provider.config.pop("userinfo_url")
    monkeypatch.setattr(
        oauth2_authenticator,
        "fetch_auth_json",
        lambda _url: {
            "issuer": "https://attacker.example.test",
            "authorization_endpoint": "https://idp.example.test/authorize",
            "token_endpoint": "https://idp.example.test/token",
            "jwks_uri": "https://idp.example.test/jwks",
        },
    )

    with pytest.raises(ValueError, match="does not match"):
        OAuth2Authenticator(provider)._metadata()


@pytest.mark.parametrize("pkce_method", ["S256", "plain"])
def test_token_exchange_disables_redirects_and_uses_bounded_timeout(monkeypatch, pkce_method: str) -> None:
    calls: dict[str, object] = {}

    class FakeSession:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def fetch_token(self, url: str, **kwargs) -> dict:
            calls["token"] = (url, kwargs)
            return {"access_token": "token"}

        def get(self, url: str, **kwargs) -> FakeResponse:
            calls["userinfo"] = (url, kwargs)
            return FakeResponse(b'{"preferred_username":"alice","id":"stable-id"}')

    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", FakeSession)
    verifier = OAuth2Authenticator.generate_code_verifier()
    identity = OAuth2Authenticator(_provider(pkce_method=pkce_method)).handle_callback(
        "https://taranis.example.test/callback",
        "authorization-code",
        "nonce",
        verifier,
    )

    assert identity is not None
    assert identity.username == "alice"
    token_url, token_kwargs = calls["token"]
    assert token_url == "https://login.example.test/token"
    assert token_kwargs["timeout"] == OUTBOUND_TIMEOUT
    assert token_kwargs["allow_redirects"] is False
    assert token_kwargs["code_verifier"] == verifier
    _userinfo_url, userinfo_kwargs = calls["userinfo"]
    assert userinfo_kwargs == {"timeout": OUTBOUND_TIMEOUT, "allow_redirects": False, "stream": True}
