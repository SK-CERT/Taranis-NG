"""Traefik dynamic configuration built from the configured public webs."""

from __future__ import annotations

import types

import pytest
from api.traefik import build_dynamic_config, is_valid_hostname

_NODE = types.SimpleNamespace(id=1, name="Default Public Web", api_url="http://public-web")


def _web(
    web_id: int,
    hostname: str,
    *,
    name: str = "Web",
    enabled: bool = True,
    node: object = _NODE,
    cert_resolver: str = "",
    hsts: str = "",
    tls_cert: str = "",
    tls_key: str = "",
) -> object:
    """A stand-in for a PublicWeb row (the builder only reads these attributes)."""
    return types.SimpleNamespace(
        id=web_id,
        name=name,
        hostname=hostname,
        enabled=enabled,
        node=node,
        cert_resolver=cert_resolver,
        hsts=hsts,
        tls_cert=tls_cert,
        get_tls_key_plaintext=lambda: tls_key,
    )


def _settings(
    *,
    security_headers: dict | None = None,
    tls_min_version: str = "",
    curves: list[str] | None = None,
    default_cert: str = "",
    default_key: str = "",
    hsts: str = "max-age=0",
    hsts_on: str = "max-age=31536000",
) -> object:
    """A stand-in for a TraefikSettings row (the builder only reads these attributes)."""

    def hsts_header_value(*, forced: bool | None = None) -> str:
        # Mirrors TraefikSettings.hsts_header_value: forced=None follows the
        # instance switch (the ``hsts`` value), True forces the parameters on
        # (``hsts_on``), False sends the release value.
        if forced is None:
            return hsts
        return hsts_on if forced else "max-age=0"

    return types.SimpleNamespace(
        security_headers=security_headers or {},
        tls_min_version=tls_min_version,
        default_cert=default_cert,
        get_curve_preferences=lambda: list(curves or []),
        get_default_key_plaintext=lambda: default_key,
        hsts_header_value=hsts_header_value,
    )


def _middlewares(config: dict) -> dict:
    return config.get("http", {}).get("middlewares", {})


# Absence, not an empty map, is how the builder says "none of these" - see
# test_no_section_is_ever_sent_as_an_empty_object for why it has to.
def _routers(config: dict) -> dict:
    return config.get("http", {}).get("routers", {})


def _services(config: dict) -> dict:
    return config.get("http", {}).get("services", {})


def test_enabled_web_becomes_a_router() -> None:
    config = build_dynamic_config([_web(3, "cyberfeed.example.org")], settings=_settings(security_headers={"X-Frame-Options": "SAMEORIGIN"}))
    routers = _routers(config)

    assert list(routers) == ["taranis-public-web-3"]
    router = routers["taranis-public-web-3"]
    assert router["rule"] == "Host(`cyberfeed.example.org`)"
    assert router["entryPoints"] == ["websecure"]
    # Unqualified, so they resolve against the middlewares this provider serves
    # alongside the routers rather than the file provider's fallback copy.
    assert router["middlewares"] == ["public-web-security-headers", "taranis-hsts"]
    # No explicit priority: Traefik's rule-length default already orders this
    # above the catch-all and below the GUI's longer rule.
    assert "priority" not in router


def test_service_is_declared_here_not_borrowed_from_the_docker_provider() -> None:
    config = build_dynamic_config([_web(3, "cyberfeed.example.org")])

    # Referencing "taranis-public-web@docker" would dangle whenever the container
    # is down, which is exactly what Traefik logs as "service does not exist".
    assert _routers(config)["taranis-public-web-3"]["service"] == "taranis-public-web-node-1"
    assert _services(config) == {"taranis-public-web-node-1": {"loadBalancer": {"servers": [{"url": "http://public-web"}]}}}


def test_webs_of_one_node_share_a_single_service() -> None:
    config = build_dynamic_config([_web(1, "one.example.org"), _web(2, "two.example.org")])

    assert sorted(_routers(config)) == ["taranis-public-web-1", "taranis-public-web-2"]
    assert list(_services(config)) == ["taranis-public-web-node-1"]


def test_each_node_gets_its_own_service() -> None:
    other = types.SimpleNamespace(id=7, name="Remote", api_url="https://feeds.example.net/")
    config = build_dynamic_config([_web(1, "one.example.org"), _web(2, "two.example.org", node=other)])

    assert _routers(config)["taranis-public-web-2"]["service"] == "taranis-public-web-node-7"
    # The trailing slash is dropped so the backend URL matches the node's root.
    assert _services(config)["taranis-public-web-node-7"]["loadBalancer"]["servers"] == [{"url": "https://feeds.example.net"}]


def test_web_on_a_node_without_an_api_url_is_skipped() -> None:
    unreachable = types.SimpleNamespace(id=2, name="No URL", api_url="")
    config = build_dynamic_config([_web(1, "a.example.org", node=unreachable)])

    assert _routers(config) == {}
    assert _services(config) == {}


def test_hostname_is_normalised() -> None:
    routers = _routers(build_dynamic_config([_web(1, "  CyberFeed.Example.ORG  ")]))

    assert routers["taranis-public-web-1"]["rule"] == "Host(`cyberfeed.example.org`)"


def test_cert_resolver_is_attached_only_when_configured() -> None:
    with_resolver = _routers(build_dynamic_config([_web(1, "a.example.org")], "myresolver"))
    without = _routers(build_dynamic_config([_web(1, "a.example.org")]))

    assert with_resolver["taranis-public-web-1"]["tls"] == {"certResolver": "myresolver"}
    # A router naming a resolver Traefik does not know still serves traffic, but
    # on the default certificate, and logs an error on every poll - so an
    # unconfigured deployment must not get one.
    assert without["taranis-public-web-1"]["tls"] == {}


@pytest.mark.parametrize(
    "web",
    [
        _web(1, "a.example.org", enabled=False),
        _web(2, ""),
        _web(3, "   "),
    ],
)
def test_webs_without_a_published_hostname_are_skipped(web: object) -> None:
    assert _routers(build_dynamic_config([web])) == {}


def test_duplicate_hostname_yields_one_router() -> None:
    routers = _routers(build_dynamic_config([_web(1, "a.example.org"), _web(2, "A.example.org")]))

    assert list(routers) == ["taranis-public-web-1"]


@pytest.mark.parametrize(
    "hostname",
    [
        "evil.org`) || Host(`taranis.example.org",  # rule injection
        "has space.example.org",
        "http://a.example.org",
        "a.example.org/path",
        "-leading-dash.example.org",
        "a..example.org",
        "x" * 64 + ".example.org",
        "a." * 130 + "example.org",
    ],
)
def test_invalid_hostnames_never_reach_a_rule(hostname: str) -> None:
    assert not is_valid_hostname(hostname)
    assert _routers(build_dynamic_config([_web(1, hostname)])) == {}


@pytest.mark.parametrize(
    "hostname",
    [
        "cyberfeed.example.org",
        "public-web.localhost",
        "localhost",
        "a1.b2.c3.example",
        "x" * 63 + ".example.org",
    ],
)
def test_valid_hostnames_are_accepted(hostname: str) -> None:
    assert is_valid_hostname(hostname)


def test_security_headers_become_the_middleware_the_routers_name() -> None:
    config = build_dynamic_config(
        [_web(1, "a.example.org")],
        settings=_settings(security_headers={"X-Frame-Options": "SAMEORIGIN"}),
    )

    middleware = config["http"]["middlewares"]["public-web-security-headers"]
    assert middleware == {"headers": {"customResponseHeaders": {"X-Frame-Options": "SAMEORIGIN"}}}
    assert _routers(config)["taranis-public-web-1"]["middlewares"] == ["public-web-security-headers", "taranis-hsts"]


def test_without_settings_nothing_but_routing_is_served() -> None:
    # A deployment that has never opened the page gets Traefik's own defaults,
    # rather than being handed empty objects that override them.
    config = build_dynamic_config([_web(1, "a.example.org")])

    assert "middlewares" not in config["http"]
    assert "tls" not in config


def test_a_router_never_names_a_middleware_that_is_not_served() -> None:
    # Traefik disables a router whose middleware is missing. The security-headers
    # middleware is omitted when there are no headers - which an administrator can
    # do by clearing the table - so the reference has to go with it, or clearing
    # the headers would take every public web offline.
    for headers in ({}, {"X-Frame-Options": "SAMEORIGIN"}):
        config = build_dynamic_config([_web(1, "a.example.org")], settings=_settings(security_headers=headers))
        named = _routers(config)["taranis-public-web-1"]["middlewares"]
        assert [name for name in named if name not in _middlewares(config)] == []

    # With no headers left, HSTS is the only one that remains.
    config = build_dynamic_config([_web(1, "a.example.org")], settings=_settings(security_headers={}))
    assert _routers(config)["taranis-public-web-1"]["middlewares"] == ["taranis-hsts"]


def test_tls_options_are_served_when_set() -> None:
    config = build_dynamic_config(
        [_web(1, "a.example.org")],
        settings=_settings(tls_min_version="VersionTLS13", curves=["X25519", "CurveP384"]),
    )

    assert config["tls"]["options"]["default"] == {
        "minVersion": "VersionTLS13",
        "curvePreferences": ["X25519", "CurveP384"],
    }
    assert "stores" not in config["tls"]


def test_default_certificate_is_inlined_as_pem() -> None:
    config = build_dynamic_config(
        [_web(1, "a.example.org")],
        settings=_settings(default_cert="-----BEGIN CERTIFICATE-----\nMII...\n", default_key="-----BEGIN PRIVATE KEY-----\nMII...\n"),
    )

    # Traefik's certFile/keyFile accept the PEM itself, so nothing is written to
    # a disk core has no access to.
    assert config["tls"]["stores"]["default"]["defaultCertificate"] == {
        "certFile": "-----BEGIN CERTIFICATE-----\nMII...\n",
        "keyFile": "-----BEGIN PRIVATE KEY-----\nMII...\n",
    }


def test_certificate_without_a_readable_key_is_not_served() -> None:
    # get_default_key_plaintext returns "" when decryption fails, e.g. after the
    # encryption key was rotated. Half a pair would break every handshake.
    config = build_dynamic_config(
        [_web(1, "a.example.org")],
        settings=_settings(default_cert="-----BEGIN CERTIFICATE-----\nMII...\n", default_key=""),
    )

    assert "stores" not in config.get("tls", {})


def test_several_webs_keep_their_own_routers() -> None:
    config = build_dynamic_config(
        [
            _web(1, "one.example.org"),
            _web(2, "two.example.org", enabled=False),
            _web(3, "three.example.org"),
        ],
    )

    assert sorted(_routers(config)) == ["taranis-public-web-1", "taranis-public-web-3"]
    assert _routers(config)["taranis-public-web-3"]["rule"] == "Host(`three.example.org`)"


# Traefik decodes this payload with paerser, which treats "routers": {} as a leaf
# value instead of an empty collection and rejects the whole document:
#   cannot decode configuration data: routers cannot be a standalone element
#   (type map[string]*dynamic.Router)
# One empty map therefore costs the middleware and the TLS options as well, and
# the provider silently keeps serving its last good configuration - which on a
# fresh start is nothing at all. Hence: no key for a section with no content.


def test_no_section_is_ever_sent_as_an_empty_object() -> None:
    config = build_dynamic_config([], settings=_settings(security_headers={"X-Frame-Options": "SAMEORIGIN"}))

    def empty_containers(node: object, path: str = "") -> list[str]:
        if isinstance(node, dict):
            return ([path] if not node and path else []) + [
                found for key, value in node.items() for found in empty_containers(value, f"{path}.{key}" if path else key)
            ]
        return []

    # A router's own "tls" may be {} - that is a struct meaning "TLS on, no
    # resolver", which Traefik accepts. Only the collections must be omitted.
    assert [p for p in empty_containers(config) if not p.endswith(".tls")] == []


def test_nothing_configured_yields_no_sections_at_all() -> None:
    # An empty document decodes cleanly; an empty section inside one does not.
    assert build_dynamic_config([]) == {}


def test_hsts_middleware_is_served_even_when_hsts_is_off() -> None:
    # The GUI, API and SSE routers name taranis-hsts@http from their container
    # labels, and Traefik disables a router whose middleware does not exist - so
    # omitting it when HSTS is off would take the whole site down. "max-age=0" is
    # also what releases browsers that are already pinned.
    config = build_dynamic_config([], settings=_settings(hsts="max-age=0"))

    assert _middlewares(config)["taranis-hsts"] == {
        "headers": {"customResponseHeaders": {"Strict-Transport-Security": "max-age=0"}},
    }


def test_hsts_value_comes_from_the_settings() -> None:
    config = build_dynamic_config([], settings=_settings(hsts="max-age=31536000; includeSubDomains"))

    headers = _middlewares(config)["taranis-hsts"]["headers"]["customResponseHeaders"]
    assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_all_three_hsts_middlewares_are_served() -> None:
    # "-on" and "-off" exist whether any web references them or not: a stable
    # payload beats one whose shape depends on which override is in use.
    config = build_dynamic_config([], settings=_settings(hsts="max-age=0", hsts_on="max-age=600"))

    hsts_value = lambda name: _middlewares(config)[name]["headers"]["customResponseHeaders"]["Strict-Transport-Security"]  # noqa: E731
    assert hsts_value("taranis-hsts") == "max-age=0"
    assert hsts_value("taranis-hsts-on") == "max-age=600"
    assert hsts_value("taranis-hsts-off") == "max-age=0"


def test_web_hsts_override_picks_the_matching_middleware() -> None:
    config = build_dynamic_config(
        [
            _web(1, "inherit.example.org"),
            _web(2, "pinned.example.org", hsts="on"),
            _web(3, "released.example.org", hsts="off"),
        ],
        settings=_settings(security_headers={"X-Frame-Options": "SAMEORIGIN"}),
    )

    routers = _routers(config)
    assert routers["taranis-public-web-1"]["middlewares"] == ["public-web-security-headers", "taranis-hsts"]
    assert routers["taranis-public-web-2"]["middlewares"] == ["public-web-security-headers", "taranis-hsts-on"]
    assert routers["taranis-public-web-3"]["middlewares"] == ["public-web-security-headers", "taranis-hsts-off"]


def test_web_cert_resolver_overrides_the_instance_default() -> None:
    routers = _routers(
        build_dynamic_config(
            [
                _web(1, "inherit.example.org"),
                _web(2, "own-ca.example.org", cert_resolver="otherresolver"),
            ],
            "myresolver",
        ),
    )

    assert routers["taranis-public-web-1"]["tls"] == {"certResolver": "myresolver"}
    assert routers["taranis-public-web-2"]["tls"] == {"certResolver": "otherresolver"}


def test_web_cert_resolver_applies_even_without_an_instance_default() -> None:
    routers = _routers(build_dynamic_config([_web(1, "own-ca.example.org", cert_resolver="otherresolver")]))

    assert routers["taranis-public-web-1"]["tls"] == {"certResolver": "otherresolver"}


def test_hsts_is_not_duplicated_into_the_public_web_headers() -> None:
    # One middleware owns the header. Two setting it would fight, and HSTS is
    # scoped to the host rather than the path, so a second policy is meaningless.
    config = build_dynamic_config(
        [_web(1, "a.example.org")],
        settings=_settings(security_headers={"X-Frame-Options": "SAMEORIGIN"}, hsts="max-age=600"),
    )

    public_web = _middlewares(config)["public-web-security-headers"]["headers"]["customResponseHeaders"]
    assert "Strict-Transport-Security" not in public_web


def test_settings_alone_are_served_without_any_routers() -> None:
    # The usual state right after enabling the feature: the settings row exists
    # but no web has a hostname yet. The middleware still has to reach Traefik,
    # because the catch-all router names it.
    config = build_dynamic_config([], settings=_settings(security_headers={"X-Robots-Tag": "noindex"}))

    assert "routers" not in config["http"]
    assert "services" not in config["http"]
    assert "public-web-security-headers" in config["http"]["middlewares"]


def test_web_certificate_is_served_as_an_sni_matched_entry() -> None:
    config = build_dynamic_config(
        [
            _web(1, "own-cert.example.org", tls_cert="-----BEGIN CERTIFICATE-----\nA\n", tls_key="-----BEGIN PRIVATE KEY-----\nB\n"),
            _web(2, "no-cert.example.org"),
        ],
    )

    # A list, not a store: Traefik matches these by SNI, so the router needs no
    # reference to them, and a web without a pair is simply not in it.
    assert config["tls"]["certificates"] == [{"certFile": "-----BEGIN CERTIFICATE-----\nA\n", "keyFile": "-----BEGIN PRIVATE KEY-----\nB\n"}]


def test_web_certificate_without_a_readable_key_is_skipped() -> None:
    # get_tls_key_plaintext returns "" when decryption fails, e.g. after the
    # encryption key was rotated. Half a pair would break every handshake.
    config = build_dynamic_config([_web(1, "a.example.org", tls_cert="-----BEGIN CERTIFICATE-----\nA\n", tls_key="")])

    assert "certificates" not in config.get("tls", {})


def test_web_certificates_and_the_default_store_coexist() -> None:
    config = build_dynamic_config(
        [_web(1, "own-cert.example.org", tls_cert="-----BEGIN CERTIFICATE-----\nA\n", tls_key="-----BEGIN PRIVATE KEY-----\nB\n")],
        settings=_settings(default_cert="-----BEGIN CERTIFICATE-----\nD\n", default_key="-----BEGIN PRIVATE KEY-----\nE\n"),
    )

    # Different keys, so no provider conflict: the list is matched by SNI first,
    # the store is the fallback for everything else.
    assert len(config["tls"]["certificates"]) == 1
    assert config["tls"]["stores"]["default"]["defaultCertificate"]["certFile"] == "-----BEGIN CERTIFICATE-----\nD\n"
