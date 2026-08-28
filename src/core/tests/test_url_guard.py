"""SSRF guard: server-side metadata fetches must target public http(s) hosts only."""

from __future__ import annotations

import pytest
from auth.url_guard import assert_auth_endpoint_url, assert_public_url, is_loopback_host


@pytest.mark.parametrize(
    "url",
    [
        "http://8.8.8.8/metadata",
        "https://8.8.8.8:8443/metadata",
    ],
)
def test_public_url_is_allowed(url: str) -> None:
    # a globally-routable address passes without raising
    assert_public_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",
        "https://10.0.0.5/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data",  # cloud instance metadata
        "http://[::1]/x",
    ],
)
def test_internal_address_is_refused(url: str) -> None:
    with pytest.raises(ValueError, match="non-public"):
        assert_public_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.org/x",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ],
)
def test_non_http_scheme_is_refused(url: str) -> None:
    with pytest.raises(ValueError, match="http"):
        assert_public_url(url)


def test_missing_host_is_refused() -> None:
    with pytest.raises(ValueError, match="host"):
        assert_public_url("http://")


def test_unresolvable_host_is_refused() -> None:
    # the reserved .invalid TLD never resolves, so no network is touched
    with pytest.raises(ValueError, match="could not be resolved"):
        assert_public_url("https://taranis-no-such-host.invalid/x")


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "LOCALHOST"])
def test_is_loopback_host_accepts_loopback(host: str) -> None:
    assert is_loopback_host(host) is True


@pytest.mark.parametrize("host", ["keycloak", "10.0.0.5", "8.8.8.8", ""])
def test_is_loopback_host_rejects_everything_else(host: str) -> None:
    assert is_loopback_host(host) is False


# The `allow_insecure` opt-in: an administrator-declared *internal* back-channel
# address may use plain HTTP, but nothing else may be relaxed by it.
@pytest.mark.parametrize("url", ["http://keycloak:8080/token", "http://10.0.0.5:8080/token", "http://8.8.8.8/token"])
def test_allow_insecure_permits_non_loopback_http_for_the_internal_hop(url: str) -> None:
    assert_auth_endpoint_url(url, allow_insecure=True)


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("https://user:pass@keycloak:8080/token", "credentials"),
        ("https://keycloak:8080/token#fragment", "fragment"),
        ("ftp://keycloak:8080/token", "http\\(s\\) URL"),
        ("http:///token", "host"),
    ],
)
def test_allow_insecure_still_rejects_credentials_fragments_bad_schemes(url: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        assert_auth_endpoint_url(url, allow_insecure=True)


def test_allow_insecure_default_keeps_the_strict_rule() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        assert_auth_endpoint_url("http://keycloak:8080/token")
