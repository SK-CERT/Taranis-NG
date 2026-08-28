"""Guard authentication-related outbound HTTP against common SSRF paths.

Admin-configured URLs (SAML IdP metadata, federation metadata aggregates) are
fetched server-side. Only an administrator can set them, but resolve the host up
front anyway and refuse loopback, private, link-local and other non-global
targets so such a fetch cannot be aimed at a cloud metadata endpoint
(169.254.169.254) or an internal service.

The request helpers also reject redirects and bound response size. This remains
a pre-connection DNS check: callers that need full DNS-rebinding protection must
use a transport that pins the validated address while preserving TLS SNI.
"""

from __future__ import annotations

import ipaddress
import json
import socket
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import requests

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_PORTS = {"http": 80, "https": 443}
OUTBOUND_TIMEOUT = (3.05, 10)
MAX_JSON_BYTES = 1024 * 1024
REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})


def is_loopback_host(host: str) -> bool:
    """Tell whether a URL host is a loopback address (or the localhost name).

    Shared by :func:`assert_auth_endpoint_url` and the auth-provider model so
    "plain HTTP only on loopback" is one rule with one behaviour.

    Args:
        host (str): The parsed URL hostname.

    Returns:
        bool: True for IPv4/IPv6 loopback addresses and "localhost".
    """
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


def assert_public_url(url: str, *, require_https: bool = False) -> None:
    """Refuse a URL that is not an http(s) URL to a globally-routable host.

    Args:
        url (str): The URL about to be fetched server-side.
        require_https (bool): Reject plain HTTP when true.

    Raises:
        ValueError: When the scheme is not http(s), the host is missing or
            unresolvable, or any resolved address is non-global (loopback,
            private, link-local, reserved, multicast or unspecified).
    """
    parsed = urlparse(url)
    if parsed.scheme not in DEFAULT_PORTS:
        msg = "The URL must be an http(s) URL"
        raise ValueError(msg)
    if require_https and parsed.scheme != "https":
        msg = "The URL must use HTTPS"
        raise ValueError(msg)
    if parsed.username is not None or parsed.password is not None:
        msg = "The URL must not contain credentials"
        raise ValueError(msg)
    if parsed.fragment:
        msg = "The URL must not contain a fragment"
        raise ValueError(msg)
    host = parsed.hostname
    if not host:
        msg = "The URL has no host"
        raise ValueError(msg)

    try:
        addresses = socket.getaddrinfo(host, parsed.port or DEFAULT_PORTS[parsed.scheme], proto=socket.IPPROTO_TCP)
    except OSError as ex:
        msg = f"The URL host '{host}' could not be resolved: {ex}"
        raise ValueError(msg) from ex

    for *_head, sockaddr in addresses:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            msg = f"Refusing to fetch '{url}': the host resolves to the non-public address {ip}"
            raise ValueError(msg)


def assert_auth_endpoint_url(url: str, *, allow_insecure: bool = False) -> None:
    """Validate an OAuth/OIDC endpoint without breaking private HTTPS IdPs.

    HTTPS endpoints may resolve privately because intranet identity providers
    are a supported deployment shape. Plain HTTP is limited to loopback
    development endpoints. Redirects are controlled by the request helper.

    Args:
        url (str): The endpoint URL to validate.
        allow_insecure (bool): Permit plain HTTP for an administrator-declared
            internal back-channel address. Every other check still applies: the
            URL must be http(s), carry a host, and contain neither embedded
            credentials nor a fragment.
    """
    parsed = urlparse(url)
    if parsed.scheme not in DEFAULT_PORTS:
        msg = "The authentication endpoint must be an http(s) URL"
        raise ValueError(msg)
    if not parsed.hostname:
        msg = "The authentication endpoint URL has no host"
        raise ValueError(msg)
    if parsed.username is not None or parsed.password is not None:
        msg = "The authentication endpoint URL must not contain credentials"
        raise ValueError(msg)
    if parsed.fragment:
        msg = "The authentication endpoint URL must not contain a fragment"
        raise ValueError(msg)
    if parsed.scheme == "http" and not allow_insecure and not is_loopback_host(parsed.hostname):
        msg = "The authentication endpoint must use HTTPS except on localhost"
        raise ValueError(msg)


def read_limited_json(response: requests.Response, *, max_bytes: int = MAX_JSON_BYTES) -> dict[str, Any]:
    """Read a successful non-redirect response as a size-bounded JSON object."""
    if response.status_code in REDIRECT_STATUS_CODES or response.is_redirect or response.is_permanent_redirect:
        msg = "Authentication endpoint redirects are not allowed"
        raise ValueError(msg)
    response.raise_for_status()

    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as ex:
            msg = "Authentication endpoint returned an invalid Content-Length"
            raise ValueError(msg) from ex
        if declared_size < 0 or declared_size > max_bytes:
            msg = f"Authentication endpoint response exceeds the {max_bytes}-byte limit"
            raise ValueError(msg)

    body = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        body.extend(chunk)
        if len(body) > max_bytes:
            msg = f"Authentication endpoint response exceeds the {max_bytes}-byte limit"
            raise ValueError(msg)

    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as ex:
        msg = "Authentication endpoint returned invalid JSON"
        raise ValueError(msg) from ex
    if not isinstance(payload, dict):
        msg = "Authentication endpoint returned a non-object JSON document"
        raise ValueError(msg)  # noqa: TRY004 - invalid remote value, not a caller type error
    return payload


def fetch_auth_json(
    url: str,
    *,
    max_bytes: int = MAX_JSON_BYTES,
    allow_insecure: bool = False,
    request_get: Callable[..., requests.Response] = requests.get,
) -> dict[str, Any]:
    """Fetch bounded JSON from a validated auth URL without following redirects."""
    assert_auth_endpoint_url(url, allow_insecure=allow_insecure)
    response = request_get(
        url,
        timeout=OUTBOUND_TIMEOUT,
        allow_redirects=False,
        stream=True,
    )
    try:
        return read_limited_json(response, max_bytes=max_bytes)
    finally:
        response.close()
