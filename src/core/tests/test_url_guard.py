"""SSRF guard: server-side metadata fetches must target public http(s) hosts only."""

from __future__ import annotations

import pytest
from auth.url_guard import assert_public_url


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
