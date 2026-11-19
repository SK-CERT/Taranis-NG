"""Keep server-side fetches of configured URLs away from internal addresses (SSRF).

A collector fetches whatever URL its source names, and then whatever that page links or
redirects to. Whoever may configure a source could otherwise aim it at a cloud metadata
endpoint (169.254.169.254), at a service on the collector's own network (the core API, the
database, Redis) or at the collector itself, and read the answer back as a news item.

So a URL is fetched only when it is http(s) and its host resolves to public addresses.
Sources that really live on an internal network are allowed per collectors node, by whoever
may configure nodes (Configuration, Collectors nodes, "Allowed internal targets") - on purpose
not by whoever configures sources. Core hands the node's list to the node with its sources.
An entry is a host name (``intranet.example.org``, or ``.example.org`` for a domain and its
subdomains), an address or a network (``10.20.0.0/16``); entries are separated by new lines or
commas.

This is a check before the connection, not a pinned connection: a host whose DNS answer
changes between the check and the fetch (DNS rebinding) is not caught here. Network policy on
the collectors node remains the place to enforce what it may reach.

Standard library only, so every service that ships ``shared`` can import it.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.request
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

if TYPE_CHECKING:
    from collections.abc import Callable
    from http.client import HTTPMessage, HTTPResponse
    from typing import IO

    IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
    IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

# Where a refusal sends the reader: the field of the collectors node in the GUI.
ALLOWED_TARGETS_WHERE = "the collectors node's allowed internal targets"
HOST_NAME = re.compile(r"(?=.{1,253}$)[a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?(\.[a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?)*")
ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}


class BlockedUrlError(ValueError):
    """A URL that must not be fetched: not http(s), or aimed at a non-public address."""


def is_non_public_address(ip: IPAddress) -> bool:
    """Tell whether an address is anything but a globally routable unicast address.

    Covers loopback, private (RFC 1918, unique local), link-local (the cloud metadata
    address among them), shared address space, reserved, multicast and unspecified addresses.
    An IPv4 address mapped into IPv6 is judged as the IPv4 address it stands for.

    Args:
        ip: The address.

    Returns:
        bool: True when a server-side fetch should not reach it by default.
    """
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified or not ip.is_global


def _entries(allowed: str | None) -> list[str]:
    """Split a node's list into its entries: lower case, without blanks or a trailing dot."""
    return [entry for entry in (raw.strip().lower().rstrip(".") for raw in re.split(r"[,\n]", allowed or "")) if entry]


def _allowed_private_targets(allowed: str | None) -> tuple[set[str], list[str], list[IPNetwork]]:
    """Read a node's exceptions: exact host names, domain suffixes, and networks."""
    hosts: set[str] = set()
    suffixes: list[str] = []
    networks: list[IPNetwork] = []
    for entry in _entries(allowed):
        try:
            networks.append(ipaddress.ip_network(entry.strip("[]"), strict=False))
            continue
        except ValueError:
            pass
        name = entry.removeprefix("*")
        if name.startswith("."):
            suffixes.append(name)
            hosts.add(name[1:])
        else:
            hosts.add(name)
    return hosts, suffixes, networks


def allowed_targets_problem(allowed: str | None) -> str | None:
    """Why a list of allowed internal targets cannot be saved; None when it can.

    Each entry must be a host name, a domain (``.example.org``), an address or a network. A
    network that covers every address (``0.0.0.0/0``, ``::/0``) is refused: it would switch
    the check off, which is not what an exception list is for.

    Args:
        allowed: The list as typed in, entries separated by new lines or commas.

    Returns:
        str | None: The reason, naming the entry, or None.
    """
    for entry in _entries(allowed):
        try:
            network = ipaddress.ip_network(entry.strip("[]"), strict=False)
        except ValueError:
            name = entry.removeprefix("*.").removeprefix(".")
            if not HOST_NAME.fullmatch(name):
                return f"'{entry}' is not a host name, a domain (.example.org), an address or a network (10.20.0.0/16)"
            continue
        if network.prefixlen == 0:
            return f"'{entry}' covers every address; name the internal networks that sources are on"
    return None


def _literal_address(host: str) -> IPAddress | None:
    """The address a URL host spells out, in any form a resolver would accept; None for a name.

    ``inet_aton`` reads the short and non-decimal spellings (``127.1``, ``0x7f000001``,
    ``2130706433``) that ``ipaddress`` refuses but an HTTP client would still connect to.
    """
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    try:
        return ipaddress.IPv4Address(socket.inet_aton(host))
    except (OSError, ValueError):
        return None


def assert_collector_url(url: str, *, via_proxy: bool = False, allowed: str | None = None) -> None:
    """Refuse a URL a collector must not fetch.

    Args:
        url: The URL about to be fetched: a source's URL, a link found in it, a redirect target.
        via_proxy: The request leaves through a proxy (or Tor), which resolves the host name
            itself - a name may not even resolve here (``.onion``). A name that does not resolve
            here is then let through. One that does is still checked: the proxy may well sit on
            the same network, where ``core`` or ``redis`` mean the same as they do here.
        allowed: The internal targets the source's collectors node may reach (see the module
            docstring); nothing internal when left out.

    Raises:
        BlockedUrlError: When the URL is not http(s), has no host, does not resolve, or reaches
            a non-public address that ``allowed`` does not name.
    """
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as error:
        msg = f"Refusing to fetch '{url}': not a valid URL ({error})"
        raise BlockedUrlError(msg) from error
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        msg = f"Refusing to fetch '{url}': only http and https URLs are fetched"
        raise BlockedUrlError(msg)
    if not host:
        msg = f"Refusing to fetch '{url}': the URL has no host"
        raise BlockedUrlError(msg)

    allowed_hosts, allowed_suffixes, allowed_networks = _allowed_private_targets(allowed)
    if host in allowed_hosts or any(host.endswith(suffix) for suffix in allowed_suffixes):
        return

    def refuse_unless_allowed(ip: IPAddress) -> None:
        if is_non_public_address(ip) and not any(ip.version == network.version and ip in network for network in allowed_networks):
            reaches = "is" if str(ip) == host else "resolves to"
            msg = f"Refusing to fetch '{url}': {host} {reaches} the non-public address {ip} (see {ALLOWED_TARGETS_WHERE})"
            raise BlockedUrlError(msg)

    literal = _literal_address(host)
    if literal is not None:
        refuse_unless_allowed(literal)
        return
    if host == "localhost" or host.endswith(".localhost"):
        msg = f"Refusing to fetch '{url}': {host} is this machine (see {ALLOWED_TARGETS_WHERE})"
        raise BlockedUrlError(msg)
    try:
        addresses = socket.getaddrinfo(host, port or DEFAULT_PORTS[parsed.scheme.lower()], proto=socket.IPPROTO_TCP)
    except OSError as error:
        if via_proxy:
            return
        msg = f"Refusing to fetch '{url}': the host '{host}' could not be resolved: {error}"
        raise BlockedUrlError(msg) from error
    for *_head, sockaddr in addresses:
        refuse_unless_allowed(ipaddress.ip_address(sockaddr[0].split("%", 1)[0]))


def collector_url_problem(url: str, *, via_proxy: bool = False, allowed: str | None = None) -> str | None:
    """Why a collector must not fetch a URL; None when it may.

    Args:
        url: The URL about to be fetched.
        via_proxy: See :func:`assert_collector_url`.
        allowed: See :func:`assert_collector_url`.

    Returns:
        str | None: The reason, or None.
    """
    try:
        assert_collector_url(url, via_proxy=via_proxy, allowed=allowed)
    except BlockedUrlError as error:
        return str(error)
    return None


class GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to a URL the collector could have been given directly."""

    def __init__(self, *, via_proxy: bool = False, allowed: str | None = None) -> None:
        """Remember how requests leave and what is allowed, for the check of each redirect target."""
        self.via_proxy = via_proxy
        self.allowed = allowed

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Check the redirect target before the standard handler builds the next request."""
        assert_collector_url(urljoin(req.full_url, newurl), via_proxy=self.via_proxy, allowed=self.allowed)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_guarded_opener(
    *handlers: urllib.request.BaseHandler,
    via_proxy: bool = False,
    allowed: str | None = None,
) -> Callable[..., HTTPResponse]:
    """Build the ``open`` function collectors fetch with: every URL and redirect is checked first.

    Args:
        *handlers: Extra urllib handlers, a proxy handler for one.
        via_proxy: See :func:`assert_collector_url`.
        allowed: See :func:`assert_collector_url`.

    Returns:
        Callable: Used like ``urllib.request.urlopen(request, timeout=...)``; raises
            :class:`BlockedUrlError` for a URL (or a redirect to one) that must not be fetched.
    """
    opener = urllib.request.build_opener(*handlers, GuardedRedirectHandler(via_proxy=via_proxy, allowed=allowed))

    def guarded_open(request: urllib.request.Request | str, *args: object, **kwargs: object) -> HTTPResponse:
        url = request if isinstance(request, str) else request.full_url
        assert_collector_url(url, via_proxy=via_proxy, allowed=allowed)
        return opener.open(request, *args, **kwargs)

    return guarded_open
