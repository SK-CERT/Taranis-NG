"""Focused OAuth/OIDC PKCE and outbound-request security tests."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import pytest
from auth import oauth2_authenticator
from auth.oauth2_authenticator import OAuth2Authenticator, fetch_discovery, resolve_endpoints, verify_configuration
from auth.url_guard import MAX_JSON_BYTES, OUTBOUND_TIMEOUT, assert_auth_endpoint_url, fetch_auth_json, read_limited_json
from authlib.integrations.base_client import OAuthError

if TYPE_CHECKING:
    from collections.abc import Iterator


class FakeResponse:
    """Minimal streaming requests response used by the outbound guard tests."""

    def __init__(self, body: bytes = b"{}", *, status_code: int = 200, headers: dict | None = None) -> None:
        """Build a response with the given body, status and headers."""
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.is_redirect = status_code in {301, 302, 303, 307, 308}
        self.is_permanent_redirect = status_code in {301, 308}
        self.closed = False

    def raise_for_status(self) -> None:
        """Raise for a 4xx/5xx status, as requests does."""
        if self.status_code >= HTTPStatus.BAD_REQUEST:
            msg = f"HTTP {self.status_code}"
            raise RuntimeError(msg)

    def iter_content(self, chunk_size: int) -> Iterator[bytes]:
        """Yield the body in chunks, as a streamed response does."""
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset : offset + chunk_size]

    def close(self) -> None:
        """Record that the caller released the connection."""
        self.closed = True


def _provider(kind: str = "oauth2", **config: str) -> SimpleNamespace:
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
        secret="encrypted-secret",
        get_secret_plaintext=lambda: "secret",
    )


def test_private_https_auth_endpoint_remains_compatible() -> None:
    assert_auth_endpoint_url("https://10.20.30.40/realms/internal")


@pytest.mark.parametrize(
    "url",
    ["http://idp.example.test/token", "https://user:pass@idp.example.test/token", "https://idp.example.test/token#fragment"],
)
def test_insecure_auth_endpoint_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="authentication endpoint"):
        assert_auth_endpoint_url(url)


@pytest.mark.parametrize("url", ["http://localhost:8080/token", "http://127.0.0.1:8080/token", "http://[::1]:8080/token"])
def test_loopback_http_auth_endpoint_remains_available_for_development(url: str) -> None:
    assert_auth_endpoint_url(url)


def test_auth_json_fetch_disables_redirects_sets_timeouts_and_closes() -> None:
    response = FakeResponse(b'{"issuer":"https://idp.example.test"}')
    calls: list[tuple[str, dict]] = []

    def request_get(url: str, **kwargs: object) -> FakeResponse:
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


def test_oidc_discovery_requires_matching_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(kind="oidc", issuer_url="https://idp.example.test", pkce_method="S256")
    provider.config.pop("authorize_url")
    provider.config.pop("token_url")
    provider.config.pop("userinfo_url")
    monkeypatch.setattr(
        oauth2_authenticator,
        "fetch_auth_json",
        lambda _url, **_kwargs: {
            "issuer": "https://attacker.example.test",
            "authorization_endpoint": "https://idp.example.test/authorize",
            "token_endpoint": "https://idp.example.test/token",
            "jwks_uri": "https://idp.example.test/jwks",
        },
    )

    with pytest.raises(ValueError, match="does not match"):
        OAuth2Authenticator(provider)._metadata()


@pytest.mark.parametrize("pkce_method", ["S256", "plain"])
def test_token_exchange_disables_redirects_and_uses_bounded_timeout(monkeypatch: pytest.MonkeyPatch, pkce_method: str) -> None:
    calls: dict[str, object] = {}

    class FakeSession:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fetch_token(self, url: str, **kwargs: object) -> dict:
            calls["token"] = (url, kwargs)
            return {"access_token": "token"}

        def get(self, url: str, **kwargs: object) -> FakeResponse:
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


# An OIDC provider reachable under two names: the public issuer the browser and
# the `iss` claim use, and the internal address core reaches it at.
PUBLIC = "https://idp.example.com"
INTERNAL = "https://kc.internal:8443"


def _md(issuer: str = PUBLIC, base: str = PUBLIC) -> dict:
    """Return a discovery document whose endpoints all sit under ``base``."""
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{base}/realms/main/protocol/openid-connect/auth",
        "token_endpoint": f"{base}/realms/main/protocol/openid-connect/token",
        "userinfo_endpoint": f"{base}/realms/main/protocol/openid-connect/userinfo",
        "jwks_uri": f"{base}/realms/main/protocol/openid-connect/certs",
        "introspection_endpoint": f"{base}/realms/main/protocol/openid-connect/token/introspect",
        "revocation_endpoint": f"{base}/realms/main/protocol/openid-connect/revoke",
    }


def test_internal_issuer_rebases_back_channel_only() -> None:
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL}
    ep = resolve_endpoints("oidc", cfg, "p", _md())
    for key in ("token", "userinfo", "jwks_uri", "introspect", "revoke"):
        assert ep[key].startswith(INTERNAL), key
    # Front channel and identity are never rewritten.
    assert ep["authorize"].startswith(PUBLIC)
    assert ep["issuer"] == PUBLIC


def test_trailing_slash_issuer_produces_well_formed_urls() -> None:
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL}
    ep = resolve_endpoints("oidc", cfg, "p", _md(issuer=PUBLIC + "/"))
    assert ep["token"] == f"{INTERNAL}/realms/main/protocol/openid-connect/token"
    # The raw discovery issuer is preserved for `iss` validation.
    assert ep["issuer"] == PUBLIC + "/"


def test_missing_userinfo_endpoint_is_none_not_a_crash() -> None:
    md = _md()
    del md["userinfo_endpoint"]
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL}
    ep = resolve_endpoints("oidc", cfg, "p", md)
    assert ep["userinfo"] is None


def test_endpoint_outside_issuer_prefix_raises() -> None:
    md = _md()
    md["token_endpoint"] = "https://oauth2.googleapis.com/token"
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL}
    with pytest.raises(ValueError, match="token"):
        resolve_endpoints("oidc", cfg, "p", md)


def test_sibling_domain_is_not_rebased() -> None:
    # The public base echoed by a *sibling* domain (idp.example.com.evil.com)
    # starts with the issuer's hostname as a plain string, but is not under it:
    # the boundary check must anchor the prefix at the issuer's own "/".
    md = _md()
    md["token_endpoint"] = "https://idp.example.com.evil.com/token"
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL}
    with pytest.raises(ValueError, match="token"):
        resolve_endpoints("oidc", cfg, "p", md)


def test_rewrite_is_anchored_not_a_global_replace() -> None:
    md = _md()
    md["token_endpoint"] = f"{PUBLIC}/token?next={PUBLIC}/cb"
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": INTERNAL}
    ep = resolve_endpoints("oidc", cfg, "p", md)
    assert ep["token"] == f"{INTERNAL}/token?next={PUBLIC}/cb"


def test_no_internal_issuer_leaves_everything_alone() -> None:
    cfg = {"issuer_url": PUBLIC}
    ep = resolve_endpoints("oidc", cfg, "p", _md())
    for value in ep.values():
        assert value is None or not value.startswith(INTERNAL)


def test_http_internal_issuer_is_refused_by_default() -> None:
    cfg = {"issuer_url": PUBLIC, "internal_issuer_url": "http://keycloak:8080"}
    with pytest.raises(ValueError, match="HTTPS"):
        resolve_endpoints("oidc", cfg, "p", _md())


def test_http_internal_issuer_is_allowed_when_opted_in() -> None:
    cfg = {
        "issuer_url": PUBLIC,
        "internal_issuer_url": "http://keycloak:8080",
        "allow_insecure_internal_transport": True,
    }
    ep = resolve_endpoints("oidc", cfg, "p", _md())
    assert ep["token"] == "http://keycloak:8080/realms/main/protocol/openid-connect/token"


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "", None, [], {}])
def test_non_boolean_insecure_transport_values_do_not_enable_plain_http(value: object) -> None:
    # A free-form config dict can smuggle non-boolean values through the API;
    # bool("false") used to be True, silently opting into cleartext transport.
    cfg = {
        "issuer_url": PUBLIC,
        "internal_issuer_url": "http://keycloak:8080",
        "allow_insecure_internal_transport": value,
    }
    with pytest.raises(ValueError, match="HTTPS"):
        resolve_endpoints("oidc", cfg, "p", _md())


def test_blank_internal_issuer_never_activates_the_opt_in() -> None:
    # Runtime treats a blank string as set (bool(" ") is true), which would
    # fetch discovery from a whitespace-only URL; it must be treated as absent.
    for blank in ("", "   "):
        cfg = {
            "issuer_url": PUBLIC,
            "internal_issuer_url": blank,
            "allow_insecure_internal_transport": True,
        }
        ep = resolve_endpoints("oidc", cfg, "p", _md())
        assert ep["token"] == f"{PUBLIC}/realms/main/protocol/openid-connect/token"


def _fetch_discovery_with_stub(metadata: dict, config: dict, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Run ``fetch_discovery`` for ``config`` with the discovery document served from memory.

    The stub keeps the genuine URL guard on the fetch itself, so an opt-in that
    must not apply to the fetched URL cannot silently relax it.
    """

    def fake_fetch(url: str, **kwargs: object) -> dict:
        assert_auth_endpoint_url(url, allow_insecure=bool(kwargs.get("allow_insecure")))
        return metadata

    monkeypatch.setattr(oauth2_authenticator, "fetch_auth_json", fake_fetch)
    return fetch_discovery(
        config.get("issuer_url"),
        "p",
        config.get("internal_issuer_url"),
        allow_insecure_internal=bool(config.get("allow_insecure_internal_transport")),
    )


def test_opt_in_does_not_relax_the_public_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag is about the internal hop only; a public http:// endpoint still fails."""
    md = _md()
    md["authorization_endpoint"] = "http://idp.example.com/auth"
    cfg = {"issuer_url": "http://idp.example.com", "allow_insecure_internal_transport": True}
    with pytest.raises(ValueError, match="HTTPS"):
        _fetch_discovery_with_stub(md, cfg, monkeypatch)


def test_opt_in_covers_every_back_channel_fetch_of_the_configuration_test(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Test-configuration button must fetch the rebased JWKS over the opted-in plain HTTP too."""
    seen: list[tuple[str, bool]] = []

    def fake_fetch(url: str, **kwargs: object) -> dict:
        seen.append((url, bool(kwargs.get("allow_insecure"))))
        if "openid-configuration" in url:
            md = _md()
            del md["introspection_endpoint"]
            del md["revocation_endpoint"]
            return md
        return {"keys": []}

    monkeypatch.setattr(oauth2_authenticator, "fetch_auth_json", fake_fetch)
    monkeypatch.setattr(oauth2_authenticator.pyjwt, "PyJWKSet", SimpleNamespace(from_dict=lambda _jwks: SimpleNamespace(keys=[])))

    class FakeSession:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fetch_token(self, *_args: object, **_kwargs: object) -> dict:
            raise OAuthError(error="invalid_grant", description="Code not found")

    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", FakeSession)

    result = verify_configuration(
        "oidc",
        {
            "issuer_url": PUBLIC,
            "internal_issuer_url": "http://keycloak:8080",
            "allow_insecure_internal_transport": True,
            "client_id": "taranis",
        },
        "s3cret",
    )

    assert seen == [
        ("http://keycloak:8080/.well-known/openid-configuration", True),
        ("http://keycloak:8080/realms/main/protocol/openid-connect/certs", True),
    ]
    assert result["client_status"] == "accepted", result["detail"]


def test_opted_in_login_reaches_the_internal_back_channel_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    """A full login against a plain-HTTP internal issuer must work when opted in.

    The rebased token, userinfo and JWKS URLs are re-checked at use time; the
    opt-in has to reach those checks or the callback swallows a guard ValueError
    and returns None.
    """
    calls: dict[str, object] = {}
    monkeypatch.setattr(oauth2_authenticator, "_metadata_cache", {})
    monkeypatch.setattr(oauth2_authenticator, "_jwks_cache", {})

    def fake_fetch(url: str, **kwargs: object) -> dict:
        calls.setdefault("fetches", []).append((url, bool(kwargs.get("allow_insecure"))))
        if "openid-configuration" in url:
            return _md()
        return {"keys": ["signing-key"]}

    monkeypatch.setattr(oauth2_authenticator, "fetch_auth_json", fake_fetch)
    signing_key = SimpleNamespace(algorithm_name="RS256", public_key_use="sig", key_id="k1", key="public-key")
    monkeypatch.setattr(
        oauth2_authenticator.pyjwt,
        "PyJWKSet",
        SimpleNamespace(from_dict=lambda _jwks: SimpleNamespace(keys=[signing_key])),
    )
    monkeypatch.setattr(oauth2_authenticator.pyjwt, "get_unverified_header", lambda _token: {"alg": "RS256", "kid": "k1"})
    monkeypatch.setattr(
        oauth2_authenticator.pyjwt,
        "decode",
        lambda *_args, **_kwargs: {"sub": "alice", "preferred_username": "alice", "nonce": "state-nonce"},
    )

    class FakeSession:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def fetch_token(self, url: str, **_kwargs: object) -> dict:
            calls["token"] = url
            return {"access_token": "token", "id_token": "header.payload.signature"}

        def get(self, url: str, **_kwargs: object) -> FakeResponse:
            calls["userinfo"] = url
            return FakeResponse(b'{"upn":"alice","sub":"alice"}')

    monkeypatch.setattr(oauth2_authenticator, "OAuth2Session", FakeSession)

    provider = _provider(kind="oidc", issuer_url=PUBLIC, internal_issuer_url="http://keycloak:8080", username_claim="upn")
    provider.config["allow_insecure_internal_transport"] = True

    identity = OAuth2Authenticator(provider).handle_callback(
        "https://taranis.example.test/callback",
        "the-code",
        "state-nonce",
        "the-verifier",
    )

    assert identity is not None
    assert identity.username == "alice"
    # Every back-channel request went to the opted-in internal address.
    assert calls["token"] == "http://keycloak:8080/realms/main/protocol/openid-connect/token"
    assert calls["userinfo"] == "http://keycloak:8080/realms/main/protocol/openid-connect/userinfo"
    assert calls["fetches"] == [
        ("http://keycloak:8080/.well-known/openid-configuration", True),
        ("http://keycloak:8080/realms/main/protocol/openid-connect/certs", True),
    ]
