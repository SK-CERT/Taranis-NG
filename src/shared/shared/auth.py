"""Shared API-key authentication for the satellite services.

Every satellite - collectors, bots, presenters, publishers and public-web - proves
itself to core, and is proven to by core, with the same credential in the same header:

    Authorization: ApiKey <the node's api_key>

The policy lives here once so the services cannot drift apart. It used to be a
byte-identical copy of the same decorator in each service, and the copies had already
started to diverge in their docstrings.

Flask is deliberately NOT imported. This package is framework-free (stdlib and
marshmallow), and making a schema/config library depend on a web framework would push
Flask onto every future consumer. The caller therefore injects the two accessors the
decorator needs, which also keeps both reads lazy - see ``make_api_key_required``.
"""

from __future__ import annotations

from functools import wraps
from http import HTTPStatus
from secrets import compare_digest
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# The scheme token that prefixes the key in the Authorization header.
AUTHORIZATION_SCHEME = "ApiKey"

# Body returned on a failed check. Copied before returning so a caller that mutates
# the response cannot corrupt it for every later request.
UNAUTHORIZED_BODY = {"error": "not authorized"}


def expected_authorization(api_key: str) -> str:
    """Return the exact ``Authorization`` value a caller must present.

    Args:
        api_key (str): The node's API key.

    Returns:
        (str): The full header value, scheme included.
    """
    return f"{AUTHORIZATION_SCHEME} {api_key}"


def api_key_matches(auth_header: str | None, api_key: str) -> bool:
    """Check an ``Authorization`` header against the expected key.

    Compared with :func:`secrets.compare_digest` rather than ``==``: the previous
    per-service implementations used a plain comparison, which short-circuits on the
    first differing byte and so leaks the key's prefix through timing.

    An empty or whitespace-only configured key never authenticates anyone. The services
    read their key from a mounted Docker secret and ``.strip()`` it, so a file that is
    present but blank yields ``""`` - and without this guard the expected header would
    collapse to the bare scheme, letting ``Authorization: ApiKey `` in from anywhere.

    Args:
        auth_header (str | None): The received header value, or None when absent.
        api_key (str): The node's API key.

    Returns:
        (bool): True only for an exact match against a non-empty key.
    """
    if not auth_header or not api_key or not api_key.strip():
        return False
    try:
        return compare_digest(auth_header, expected_authorization(api_key))
    except TypeError:
        # compare_digest rejects non-ASCII str; a header that cannot be the key is
        # simply unauthorized rather than a 500.
        return False


def make_api_key_required(
    get_api_key: Callable[[], str],
    get_auth_header: Callable[[], str | None],
) -> Callable:
    """Build the ``api_key_required`` decorator for one service.

    Both accessors are called per request rather than read at import time: public-web
    loads its key lazily from the mounted Docker secret, and the request object only
    exists inside a request context.

    Args:
        get_api_key (Callable): Returns this service's currently configured API key.
        get_auth_header (Callable): Returns the request's ``Authorization`` header.

    Returns:
        (Callable): A decorator that answers 401 unless the header carries the key.
    """

    def api_key_required(fn: Callable) -> Callable:
        """Reject the request unless it carries this service's API key.

        Args:
            fn (Callable): The endpoint to protect.

        Returns:
            (Callable): The wrapped endpoint.
        """

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            if not api_key_matches(get_auth_header(), get_api_key()):
                return dict(UNAUTHORIZED_BODY), HTTPStatus.UNAUTHORIZED
            return fn(*args, **kwargs)

        return wrapper

    return api_key_required
