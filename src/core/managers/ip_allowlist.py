"""IP allowlists for API keys.

An allowlist is a list of IPv4/IPv6 addresses or CIDR ranges, stored as text with one normalised
network per line. An empty list allows every address. API keys have their own list and the
security settings a site-wide one; a request has to match both, wherever one is set.

Only public addresses can be listed: a range that reaches into private, shared (CGNAT),
loopback, link-local, multicast, broadcast, documentation, benchmarking or other reserved space
is refused (IANA special-purpose registries), and so is IPv6 outside global unicast (2000::/3).
The GUI repeats the check (``components/common/api-keys/apiKeys.ts``); keep the lists in step.

The address checked is ``request.remote_addr``. ProxyFix (``app.py``) has rewritten it from the
``X-Forwarded-For`` entries of the ``TRUSTED_PROXY_HOPS`` trusted proxies, so a client cannot
choose it. ``log_manager.resolve_ip_address()`` is not usable here: it returns the leftmost
``X-Forwarded-For`` entry, which the client sends itself.
"""

from __future__ import annotations

import ipaddress
import re

from flask import has_request_context, request

MAX_ENTRIES = 100

# Not globally routable. 240.0.0.0/4 includes the limited broadcast address 255.255.255.255.
SPECIAL_IPV4 = tuple(
    ipaddress.IPv4Network(network)
    for network in (
        "0.0.0.0/8",  # "this network"
        "10.0.0.0/8",  # private
        "100.64.0.0/10",  # shared address space (carrier-grade NAT)
        "127.0.0.0/8",  # loopback
        "169.254.0.0/16",  # link-local
        "172.16.0.0/12",  # private
        "192.0.0.0/24",  # IETF protocol assignments
        "192.0.2.0/24",  # documentation (TEST-NET-1)
        "192.88.99.0/24",  # deprecated 6to4 relay anycast
        "192.168.0.0/16",  # private
        "198.18.0.0/15",  # benchmarking
        "198.51.100.0/24",  # documentation (TEST-NET-2)
        "203.0.113.0/24",  # documentation (TEST-NET-3)
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved, and broadcast
    )
)
# IPv6 is public only inside global unicast, and outside these special blocks within it.
GLOBAL_UNICAST_IPV6 = ipaddress.IPv6Network("2000::/3")
SPECIAL_IPV6 = tuple(
    ipaddress.IPv6Network(network)
    for network in (
        "2001::/23",  # IETF protocol assignments (Teredo, ORCHID, benchmarking, ...)
        "2001:db8::/32",  # documentation
        "2002::/16",  # deprecated 6to4
        "3fff::/20",  # documentation
    )
)

IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def _unmapped(address: IpAddress) -> IpAddress:
    """Return the IPv4 address an IPv4-mapped IPv6 address (``::ffff:1.2.3.4``) stands for."""
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def _entries(value: str | list | tuple | None) -> list[str]:
    """Split a textarea value (lines, commas or spaces) or a list into non-empty entries."""
    if value is None:
        return []
    items = value if isinstance(value, list | tuple) else re.split(r"[\s,;]+", str(value))
    return [str(item).strip() for item in items if str(item).strip()]


def parse_network(entry: str) -> IpNetwork:
    """Parse one address or CIDR range; a host address becomes a /32 or /128 network.

    Raises:
        ValueError: When the entry is neither.
    """
    try:
        network = ipaddress.ip_network(entry, strict=False)
    except ValueError:
        msg = f"'{entry}' is not an IP address or CIDR range"
        raise ValueError(msg) from None
    if isinstance(network, ipaddress.IPv6Network) and network.network_address.ipv4_mapped is not None and network.prefixlen >= 96:  # noqa: PLR2004
        # ::ffff:10.0.0.0/104 is 10.0.0.0/8 written as IPv6
        network = ipaddress.ip_network(f"{network.network_address.ipv4_mapped}/{network.prefixlen - 96}", strict=False)
    return network


def is_public(network: IpNetwork) -> bool:
    """Tell whether a whole network is public: routable, and touching no special-purpose range."""
    if isinstance(network, ipaddress.IPv4Network):
        return not any(network.overlaps(special) for special in SPECIAL_IPV4)
    return network.subnet_of(GLOBAL_UNICAST_IPV6) and not any(network.overlaps(special) for special in SPECIAL_IPV6)


def is_public_address(ip: str | None) -> bool:
    """Tell whether an address could be put on an allowlist (see :func:`is_public`)."""
    if not ip:
        return False
    try:
        return is_public(parse_network(ip.split("%", 1)[0]))
    except ValueError:
        return False


def normalize(value: str | list | tuple | None) -> str | None:
    """Validate an allowlist and return it as stored: one network per line, duplicates dropped.

    Args:
        value: The entries, as text (one per line, or separated by commas or spaces) or a list.

    Returns:
        str | None: The normalised list, or None when it is empty.

    Raises:
        ValueError: When an entry is invalid or not public, or there are more than ``MAX_ENTRIES``.
    """
    networks: list[str] = []
    for entry in _entries(value):
        parsed = parse_network(entry)
        if not is_public(parsed):
            msg = (
                f"'{entry}' is not a public IP address or range; private, loopback, link-local, "
                "multicast, broadcast, documentation and other special ranges cannot be listed"
            )
            raise ValueError(msg)
        network = str(parsed)
        if network not in networks:
            networks.append(network)
    if len(networks) > MAX_ENTRIES:
        msg = f"An IP allowlist can hold at most {MAX_ENTRIES} entries"
        raise ValueError(msg)
    return "\n".join(networks) or None


def networks(stored: str | None) -> list[IpNetwork]:
    """Return the networks of a stored allowlist; entries that no longer parse are skipped."""
    result = []
    for entry in _entries(stored):
        try:
            result.append(parse_network(entry))
        except ValueError:
            continue
    return result


def as_list(stored: str | None) -> list[str]:
    """Return a stored allowlist as a list of strings, for JSON."""
    return [str(network) for network in networks(stored)]


def allows(stored: str | None, ip: str | None) -> bool:
    """Tell whether an allowlist admits an address. An empty list admits every address.

    A list that is set but whose entries all fail to parse admits nothing, and neither does any
    list for an address that is unknown or malformed.
    """
    if not _entries(stored):
        return True
    if not ip:
        return False
    try:
        address = _unmapped(ipaddress.ip_address(ip.strip().split("%", 1)[0]))
    except ValueError:
        return False
    return any(address.version == network.version and address in network for network in networks(stored))


def client_ip() -> str | None:
    """Return the trusted client address of the current request, IPv4-mapped IPv6 unmapped."""
    if not has_request_context():
        return None
    ip = request.remote_addr
    if not ip:
        return None
    try:
        return str(_unmapped(ipaddress.ip_address(ip.split("%", 1)[0])))
    except ValueError:
        return ip
