"""Best-effort guard against server-side request forgery to internal hosts.

Admin-configured URLs (SAML IdP metadata, federation metadata aggregates) are
fetched server-side. Only an administrator can set them, but resolve the host up
front anyway and refuse loopback, private, link-local and other non-global
targets so such a fetch cannot be aimed at a cloud metadata endpoint
(169.254.169.254) or an internal service.

This is a pre-connection check: it does not by itself defend against DNS
rebinding between this lookup and the actual request (a resolver could return a
different address the second time). Pinning the resolved address into the
connection would close that gap; given these fetches are admin-only it is
deliberately left out of scope here.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

DEFAULT_PORTS = {"http": 80, "https": 443}


def assert_public_url(url: str) -> None:
    """Refuse a URL that is not an http(s) URL to a globally-routable host.

    Args:
        url (str): The URL about to be fetched server-side.

    Raises:
        ValueError: When the scheme is not http(s), the host is missing or
            unresolvable, or any resolved address is non-global (loopback,
            private, link-local, reserved, multicast or unspecified).
    """
    parsed = urlparse(url)
    if parsed.scheme not in DEFAULT_PORTS:
        msg = "The URL must be an http(s) URL"
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
