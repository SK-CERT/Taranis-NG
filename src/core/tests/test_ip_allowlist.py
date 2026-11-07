"""IP allowlists of API keys: what is accepted, what matches, and which address is checked."""

from __future__ import annotations

import pytest
from flask import Flask
from managers import ip_allowlist
from werkzeug.middleware.proxy_fix import ProxyFix


@pytest.mark.parametrize(
    ("value", "stored"),
    [
        ("185.10.20.0/24", "185.10.20.0/24"),
        ("8.8.8.8", "8.8.8.8/32"),
        ("185.10.20.7/16", "185.10.0.0/16"),  # host bits are dropped, not refused
        ("2a01:4f8::/32", "2a01:4f8::/32"),
        ("2A01:4F8::1", "2a01:4f8::1/128"),
        ("::ffff:185.10.0.0/112", "185.10.0.0/16"),  # IPv4 written as IPv6 is stored as IPv4
        ("::ffff:8.8.8.8", "8.8.8.8/32"),
        ("185.10.20.0/24\n8.8.8.8, 2a01:4f8::/32;", "185.10.20.0/24\n8.8.8.8/32\n2a01:4f8::/32"),
        (["185.10.20.0/24", " 185.10.20.0/24 "], "185.10.20.0/24"),  # duplicates go
        ("", None),
        ("  \n ", None),
        (None, None),
        ([], None),
    ],
)
def test_entries_are_stored_normalised(value: object, stored: str | None) -> None:
    assert ip_allowlist.normalize(value) == stored


@pytest.mark.parametrize("value", ["example.com", "10.0.0.0/33", "300.1.1.1", "10.0.0.0/8/8", "2001:db8::/129", "*"])
def test_an_entry_that_is_no_address_is_refused_by_name(value: str) -> None:
    with pytest.raises(ValueError, match="is not an IP address or CIDR range"):
        ip_allowlist.normalize(value)


@pytest.mark.parametrize(
    "value",
    [
        "10.0.0.0/8",  # private
        "172.16.5.4",
        "192.168.1.0/24",
        "100.64.0.1",  # shared address space (CGNAT)
        "127.0.0.1",  # loopback
        "169.254.10.10",  # link-local
        "0.0.0.0/0",  # everything, special ranges included
        "8.0.0.0/5",  # public at both ends, but holds 10.0.0.0/8
        "224.0.0.1",  # multicast
        "255.255.255.255",  # broadcast
        "240.0.0.1",  # reserved
        "192.0.2.7",  # documentation
        "198.51.100.0/24",
        "203.0.113.9",
        "198.18.0.1",  # benchmarking
        "::",  # unspecified
        "::/0",
        "::1",  # loopback
        "fe80::1",  # link-local
        "fc00::/7",  # unique local
        "fd12:3456::1",
        "ff02::1",  # multicast
        "2001:db8::/32",  # documentation
        "3fff::1",
        "2001::1",  # Teredo
        "2002:c000:204::1",  # 6to4
        "4000::1",  # outside global unicast
        "::ffff:10.0.0.1",  # private IPv4, written as IPv6
    ],
)
def test_an_address_that_is_not_public_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="is not a public IP address or range"):
        ip_allowlist.normalize(value)


def test_the_callers_address_is_judged_by_the_same_rule() -> None:
    assert ip_allowlist.is_public_address("185.10.20.7") is True
    assert ip_allowlist.is_public_address("2a01:4f8::1") is True
    assert ip_allowlist.is_public_address("172.20.0.1") is False
    assert ip_allowlist.is_public_address("::1") is False
    assert ip_allowlist.is_public_address(None) is False
    assert ip_allowlist.is_public_address("not-an-ip") is False


def test_a_list_is_capped() -> None:
    entries = [f"185.10.{i // 256}.{i % 256}" for i in range(ip_allowlist.MAX_ENTRIES + 1)]
    with pytest.raises(ValueError, match="at most"):
        ip_allowlist.normalize(entries)
    assert ip_allowlist.normalize(entries[:-1]).count("\n") == ip_allowlist.MAX_ENTRIES - 1


@pytest.mark.parametrize(
    ("stored", "ip", "allowed"),
    [
        (None, "198.51.100.7", True),  # no list: any address
        ("", None, True),
        ("10.0.0.0/8", "10.20.30.40", True),
        ("10.0.0.0/8", "11.0.0.1", False),
        ("10.0.0.0/8\n2001:db8::/32", "2001:db8:1::5", True),
        ("2001:db8::/32", "10.0.0.1", False),  # the families never match each other
        ("10.0.0.0/8", "::ffff:10.0.0.1", True),  # a dual-stack socket's IPv4 client
        ("10.0.0.0/8", "fe80::1%eth0", False),
        ("10.0.0.0/8", None, False),  # a list is set and the address is unknown
        ("10.0.0.0/8", "not-an-ip", False),
        ("garbage", "10.0.0.1", False),  # a list whose entries no longer parse admits nothing
    ],
)
def test_matching(stored: str | None, ip: str | None, *, allowed: bool) -> None:
    assert ip_allowlist.allows(stored, ip) is allowed


def test_the_stored_list_is_given_to_the_gui_as_a_list() -> None:
    assert ip_allowlist.as_list("10.0.0.0/8\n2001:db8::/32") == ["10.0.0.0/8", "2001:db8::/32"]
    assert ip_allowlist.as_list(None) == []


def test_the_client_address_is_the_one_the_trusted_proxy_saw_never_the_clients_own_header() -> None:
    """Behind ProxyFix the leftmost X-Forwarded-For entry is whatever the client sent."""
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    seen: list[str | None] = []

    @app.get("/ip")
    def ip() -> str:
        seen.append(ip_allowlist.client_ip())
        return ""

    client = app.test_client()
    client.get("/ip", headers={"X-Forwarded-For": "10.0.0.5, 198.51.100.7"}, environ_base={"REMOTE_ADDR": "172.18.0.2"})
    client.get("/ip", environ_base={"REMOTE_ADDR": "::ffff:192.0.2.9"})
    assert seen == ["198.51.100.7", "192.0.2.9"]


def test_there_is_no_client_address_outside_a_request() -> None:
    assert ip_allowlist.client_ip() is None
