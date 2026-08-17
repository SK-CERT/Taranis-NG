"""Validate the API-key authentication policy shared by every satellite service.

These endpoints answer on the public internet in a distributed deployment, so the
policy they all delegate to is worth pinning down: the exact header shape, what counts
as a match, and the reply given to anyone who fails.
"""

from http import HTTPStatus

import pytest
from shared.auth import (
    AUTHORIZATION_SCHEME,
    UNAUTHORIZED_BODY,
    api_key_matches,
    expected_authorization,
    make_api_key_required,
)

KEY = "0123456789abcdef"


def _decorated(api_key: str, auth_header: str | None) -> object:
    """Build and immediately call an endpoint protected with the given credentials."""
    decorator = make_api_key_required(lambda: api_key, lambda: auth_header)
    return decorator(lambda: {"isalive": True})()


def test_expected_header_carries_the_scheme_and_the_key() -> None:
    """The contract every satellite and every core client speaks."""
    assert expected_authorization(KEY) == f"{AUTHORIZATION_SCHEME} {KEY}"
    assert AUTHORIZATION_SCHEME == "ApiKey"


def test_the_matching_key_is_accepted() -> None:
    """The happy path: the header core sends is the header a satellite expects."""
    assert api_key_matches(f"ApiKey {KEY}", KEY) is True


@pytest.mark.parametrize(
    "auth_header",
    [
        None,
        "",
        KEY,  # the bare key, without the scheme
        f"Bearer {KEY}",  # right key, wrong scheme
        "ApiKey ",
        f"ApiKey {KEY} ",  # trailing whitespace is not stripped
        f"apikey {KEY}",  # the scheme is case-sensitive
        f"ApiKey {KEY.upper()}",
        "ApiKey wrong",
    ],
)
def test_anything_but_an_exact_match_is_rejected(auth_header: str | None) -> None:
    """No near-miss authenticates: the comparison is exact, not fuzzy."""
    assert api_key_matches(auth_header, KEY) is False


def test_a_non_ascii_header_is_rejected_rather_than_raising() -> None:
    """compare_digest rejects non-ASCII str; that must be a 401, not a 500."""
    assert api_key_matches("ApiKey é", KEY) is False


def test_an_empty_configured_key_never_authenticates() -> None:
    """A service whose key failed to load must not accept a bare scheme."""
    assert api_key_matches("ApiKey ", "") is False
    assert api_key_matches("ApiKey", "") is False


def test_the_endpoint_runs_when_the_key_matches() -> None:
    """A decorated endpoint is reached untouched on success."""
    assert _decorated(KEY, f"ApiKey {KEY}") == {"isalive": True}


@pytest.mark.parametrize("auth_header", [None, "", "ApiKey wrong"])
def test_the_endpoint_is_not_reached_without_the_key(auth_header: str | None) -> None:
    """A failed check answers 401 and never calls the endpoint."""
    assert _decorated(KEY, auth_header) == (UNAUTHORIZED_BODY, HTTPStatus.UNAUTHORIZED)


def test_the_unauthorized_body_cannot_be_mutated_between_requests() -> None:
    """The reply is copied per call, so one handler cannot corrupt the next."""
    body, _ = _decorated(KEY, None)
    body["error"] = "leaked"
    assert UNAUTHORIZED_BODY == {"error": "not authorized"}
    next_body, _ = _decorated(KEY, None)
    assert next_body == {"error": "not authorized"}


def test_both_accessors_are_read_per_request() -> None:
    """Keys are read lazily: public-web loads its secret on first use, not at import."""
    keys = iter(["first", "second"])
    headers = iter(["ApiKey first", "ApiKey first"])
    endpoint = make_api_key_required(lambda: next(keys), lambda: next(headers))(lambda: {"ok": True})

    assert endpoint() == {"ok": True}
    # Second call re-reads the key, which has rotated: the same header no longer matches.
    assert endpoint() == (UNAUTHORIZED_BODY, HTTPStatus.UNAUTHORIZED)
