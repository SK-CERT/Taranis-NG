"""Traefik dynamic configuration built from the configured public webs."""

from __future__ import annotations

import types

import api.traefik as traefik_api
import managers.log_manager as core_log_manager
import pytest
from api.traefik import build_dynamic_config, is_valid_hostname
from flask import Flask

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
    backend_insecure_skip_verify: bool = False,
    backend_root_cas: str = "",
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
        backend_insecure_skip_verify=backend_insecure_skip_verify,
        backend_root_cas=backend_root_cas,
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


# --- whose resolver name a router gets ---------------------------------------------
#
# A resolver name only means something inside the Traefik that declares it, and these
# routers are served to whichever Traefik fronts the node. Falling from the web straight
# to the INSTANCE name handed a remote worker core's name: Traefik logged "Router uses a
# nonexistent certificate resolver", disabled ACME for the router and served its default
# certificate, so the hostname answered on the wrong certificate. Hence web -> node ->
# instance.


def _node_with_resolver(resolver: str) -> object:
    return types.SimpleNamespace(id=9, name="Remote", api_url="https://public-web.w1.example.com:8443", cert_resolver=resolver)


def test_the_nodes_resolver_is_used_when_the_web_names_none() -> None:
    """The regression: a remote node used to inherit core's instance-wide name."""
    config = build_dynamic_config([_web(1, "a.example.org", node=_node_with_resolver("myresolver"))], "instance-wide")

    assert _routers(config)["taranis-public-web-1"]["tls"] == {"certResolver": "myresolver"}


def test_a_webs_own_resolver_still_beats_its_nodes() -> None:
    """Per-hostname override stays the most specific level."""
    web = _web(1, "a.example.org", node=_node_with_resolver("myresolver"), cert_resolver="web-only")
    config = build_dynamic_config([web], "instance-wide")

    assert _routers(config)["taranis-public-web-1"]["tls"] == {"certResolver": "web-only"}


def test_the_instance_resolver_applies_when_neither_names_one() -> None:
    """Which is the core-fronted case: core's own Traefik does declare that name."""
    config = build_dynamic_config([_web(1, "a.example.org", node=_node_with_resolver(""))], "instance-wide")

    assert _routers(config)["taranis-public-web-1"]["tls"] == {"certResolver": "instance-wide"}


def test_a_node_predating_the_column_does_not_break_the_builder() -> None:
    """_NODE has no cert_resolver attribute at all, as an older row would not."""
    config = build_dynamic_config([_web(1, "a.example.org")], "instance-wide")

    assert _routers(config)["taranis-public-web-1"]["tls"] == {"certResolver": "instance-wide"}


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


# --- the per-node provider route -------------------------------------------------
#
# The unscoped payload inlines every web's private key, so the route a remote Traefik
# polls must authenticate and must hand back that node's slice and nothing else.

_OTHER_NODE = types.SimpleNamespace(id=2, name="Second node", api_url="https://public-web.w2.example.com")


def _node_row(node: object, api_key: str) -> object:
    """A stand-in for a PublicWebNode row as _authenticated_node reads it."""
    return types.SimpleNamespace(id=node.id, name=node.name, api_url=node.api_url, api_key=api_key)


@pytest.fixture
def known_nodes(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Resolve api keys to node rows without touching the database."""
    rows = {"key-one": _node_row(_NODE, "key-one"), "key-two": _node_row(_OTHER_NODE, "key-two")}
    monkeypatch.setattr(
        traefik_api.PublicWebNode,
        "get_by_api_key",
        classmethod(lambda _cls, api_key: rows.get(api_key)),
    )
    return rows


@pytest.mark.parametrize(
    "auth_header",
    [
        None,
        "",
        "key-one",  # the bare key, without the scheme
        "Bearer key-one",  # right key, wrong scheme
        "ApiKey unknown-key",
        "ApiKey ",
        "apikey key-one",  # the scheme is case-sensitive
    ],
)
@pytest.mark.usefixtures("known_nodes")
def test_no_node_is_resolved_without_an_exact_api_key(auth_header: str | None) -> None:
    """Anything short of this node's own credential is anonymous, and gets a 401."""
    assert traefik_api._authenticated_node(auth_header) is None


@pytest.mark.usefixtures("known_nodes")
def test_each_key_resolves_to_its_own_node() -> None:
    """The polling node is identified by the key it presents."""
    assert traefik_api._authenticated_node("ApiKey key-one").id == _NODE.id
    assert traefik_api._authenticated_node("ApiKey key-two").id == _OTHER_NODE.id


def test_a_row_whose_key_no_longer_matches_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lookup is re-checked, so a loose database match cannot authenticate."""
    stale = _node_row(_NODE, "rotated-key")
    monkeypatch.setattr(
        traefik_api.PublicWebNode,
        "get_by_api_key",
        classmethod(lambda _cls, _api_key: stale),
    )
    assert traefik_api._authenticated_node("ApiKey key-one") is None


def test_a_scoped_payload_carries_only_the_polling_nodes_webs() -> None:
    """A worker is never handed another node's hostnames - nor the keys beside them."""
    mine = _web(1, "mine.example.com", node=_NODE, tls_cert="CERT-MINE", tls_key="KEY-MINE")
    theirs = _web(2, "theirs.example.com", node=_OTHER_NODE, tls_cert="CERT-THEIRS", tls_key="KEY-THEIRS")

    scoped = build_dynamic_config([mine], "", _settings())
    unscoped = build_dynamic_config([mine, theirs], "", _settings())

    assert [r["rule"] for r in _routers(scoped).values()] == ["Host(`mine.example.com`)"]
    assert len(_routers(unscoped)) == 2

    serialized = repr(scoped)
    assert "theirs.example.com" not in serialized
    assert "KEY-THEIRS" not in serialized
    assert f"taranis-public-web-node-{_OTHER_NODE.id}" not in _services(scoped)


def _global_tls_settings() -> object:
    return _settings(tls_min_version="VersionTLS13", default_cert="DEFAULT-CERT", default_key="DEFAULT-KEY")


def test_the_unscoped_payload_carries_the_instance_wide_tls_settings() -> None:
    """Core's own Traefik has no other source for them."""
    config = build_dynamic_config([_web(1, "mine.example.com")], "", _global_tls_settings())

    assert config["tls"]["options"]["default"]["minVersion"] == "VersionTLS13"
    assert config["tls"]["stores"]["default"]["defaultCertificate"]["certFile"] == "DEFAULT-CERT"


def test_a_scoped_payload_omits_the_instance_wide_tls_settings() -> None:
    """Sending these to a node took down every router on it, its own API included.

    Traefik does not namespace ``tls.options``/``tls.stores`` per provider, so the same
    key from two providers is dropped rather than merged and the node fails every router
    with "unknown TLS options: default". Not a degraded web - no TLS at all.
    """
    config = build_dynamic_config([_web(1, "mine.example.com")], "", _global_tls_settings(), for_node=True)

    tls = config.get("tls", {})
    assert "options" not in tls, "tls.options in a node payload breaks every router on that worker"
    assert "stores" not in tls, "tls.stores is instance-wide too, and core's default certificate is not the worker's"


def test_a_scoped_payload_points_at_the_container_next_door() -> None:
    """api_url here sent the node's Traefik out to the internet and back to itself.

    It arrived on the API entrypoint still carrying the web's Host header, matching no
    router there, so Traefik answered its own 404 - with the web's security headers
    attached, making it look like the application refused its own hostname.
    """
    remote = types.SimpleNamespace(id=5, name="Remote", api_url="https://public-web.w1.example.com:8443")
    config = build_dynamic_config([_web(1, "a.example.org", node=remote)], "", _settings(), for_node=True)

    assert _services(config)["taranis-public-web-node-5"]["loadBalancer"]["servers"] == [{"url": "http://public-web"}]


def test_cores_own_payload_still_points_at_the_nodes_api_url() -> None:
    """Core is not beside the container, so for it the api_url is the only way there."""
    remote = types.SimpleNamespace(id=5, name="Remote", api_url="https://public-web.w1.example.com:8443")
    config = build_dynamic_config([_web(1, "a.example.org", node=remote)], "", _settings())

    assert _services(config)["taranis-public-web-node-5"]["loadBalancer"]["servers"] == [
        {"url": "https://public-web.w1.example.com:8443"},
    ]


def test_a_node_without_an_api_url_still_serves_its_own_webs() -> None:
    """No api_url means core cannot reach it - it does not stop the node serving itself."""
    unreachable = types.SimpleNamespace(id=6, name="No URL", api_url="")
    config = build_dynamic_config([_web(1, "a.example.org", node=unreachable)], "", _settings(), for_node=True)

    assert list(_routers(config)) == ["taranis-public-web-1"]
    assert _services(config)["taranis-public-web-node-6"]["loadBalancer"]["servers"] == [{"url": "http://public-web"}]


def test_a_scoped_payload_carries_no_servers_transport() -> None:
    """The local hop is plain http, so the backend-TLS settings do not apply to it."""
    remote = types.SimpleNamespace(id=5, name="Remote", api_url="https://public-web.w1.example.com:8443")
    settings = _settings(backend_insecure_skip_verify=True)
    config = build_dynamic_config([_web(1, "a.example.org", node=remote)], "", settings, for_node=True)

    assert "serversTransport" not in _services(config)["taranis-public-web-node-5"]["loadBalancer"]


def test_a_scoped_payload_still_carries_each_webs_own_certificate() -> None:
    """The per-web certificates are the point of the payload, and are not global.

    ``tls.certificates`` is a list matched by SNI rather than a named key, so it merges
    across providers instead of colliding - which is why omitting the other two costs
    nothing here.
    """
    config = build_dynamic_config(
        [_web(1, "mine.example.com", tls_cert="CERT-MINE", tls_key="KEY-MINE")],
        "",
        _global_tls_settings(),
        for_node=True,
    )

    assert config["tls"]["certificates"] == [{"certFile": "CERT-MINE", "keyFile": "KEY-MINE"}]


def test_a_node_with_no_enabled_webs_yields_no_router_section() -> None:
    """Still a valid document: Traefik rejects a payload with an empty routers map."""
    config = build_dynamic_config([], "", _settings())
    assert "routers" not in config.get("http", {})


# --- backend TLS to the node ------------------------------------------------------
#
# Traefik is the TLS *client* when it proxies to a remote node, so a node presenting
# its own certificate needs this. Verification stays on unless asked otherwise.


def _transports(config: dict) -> dict:
    return config.get("http", {}).get("serversTransports", {})


def _load_balancer(config: dict) -> dict:
    return next(iter(_services(config).values()))["loadBalancer"]


def test_nothing_is_emitted_until_backend_tls_is_configured() -> None:
    """The default must not weaken verification, nor add an unused section."""
    config = build_dynamic_config([_web(1, "a.example.com")], "", _settings())
    assert _transports(config) == {}
    assert "serversTransport" not in _load_balancer(config)


def test_skip_verify_is_emitted_and_referenced_by_the_service() -> None:
    """A transport nothing names would silently do nothing."""
    config = build_dynamic_config([_web(1, "a.example.com")], "", _settings(backend_insecure_skip_verify=True))
    assert _transports(config) == {"public-web-node": {"insecureSkipVerify": True}}
    assert _load_balancer(config)["serversTransport"] == "public-web-node"


def test_a_ca_bundle_is_inlined_like_the_certificates() -> None:
    """Core has no disk Traefik can read, so the PEM travels in the payload."""
    config = build_dynamic_config([_web(1, "a.example.com")], "", _settings(backend_root_cas="-----BEGIN CERTIFICATE-----"))
    assert _transports(config)["public-web-node"] == {"rootCAs": ["-----BEGIN CERTIFICATE-----"]}
    assert _load_balancer(config)["serversTransport"] == "public-web-node"


def test_a_ca_bundle_and_skip_verify_together_still_emit_both() -> None:
    """Traefik would ignore the bundle; the payload stays truthful and warns."""
    config = build_dynamic_config(
        [_web(1, "a.example.com")],
        "",
        _settings(backend_root_cas="-----BEGIN CERTIFICATE-----", backend_insecure_skip_verify=True),
    )
    assert _transports(config)["public-web-node"] == {
        "rootCAs": ["-----BEGIN CERTIFICATE-----"],
        "insecureSkipVerify": True,
    }


def test_every_node_service_shares_the_one_transport() -> None:
    """One transport definition, named by each node's service."""
    other = types.SimpleNamespace(id=7, name="Other", api_url="https://public-web.w7.example.com")
    config = build_dynamic_config(
        [_web(1, "a.example.com"), _web(2, "b.example.com", node=other)],
        "",
        _settings(backend_insecure_skip_verify=True),
    )
    assert len(_transports(config)) == 1
    assert all(service["loadBalancer"]["serversTransport"] == "public-web-node" for service in _services(config).values())


# --- which webs each route publishes -----------------------------------------------
#
# Two Traefiks poll core: its own, and each remote node's. Handing them the same web
# puts them in competition for the hostname - both building a router, both asking their
# own ACME account for its certificate, only one able to serve it.


@pytest.fixture
def route_context(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """What the two resources need to be callable without a running instance.

    A request context because both read ``request``, and a silenced activity log because
    @no_auth records every access - which is a database write, and these tests are about
    which query a route chooses, not about logging.
    """
    monkeypatch.setattr(core_log_manager, "store_activity", lambda *_a, **_k: None)
    with Flask(__name__).test_request_context("/traefik/dynamic"):
        yield


def _stub_queries(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """Record which model query a route reaches for, without a database."""
    called = {"all_enabled": False, "core_fronted": False}

    def all_enabled() -> list:
        called["all_enabled"] = True
        return []

    def core_fronted() -> list:
        called["core_fronted"] = True
        return []

    settings = _settings()
    # _resolver_for reads this off the row; _settings() covers everything else the
    # builder touches.
    settings.cert_resolver = ""

    monkeypatch.setattr(traefik_api.PublicWeb, "get_all_enabled", staticmethod(all_enabled))
    monkeypatch.setattr(traefik_api.PublicWeb, "get_enabled_fronted_by_core", staticmethod(core_fronted))
    monkeypatch.setattr(traefik_api.TraefikSettings, "get", staticmethod(lambda: settings))
    return called


@pytest.mark.usefixtures("route_context")
def test_cores_own_route_asks_only_for_the_webs_core_fronts(monkeypatch: pytest.MonkeyPatch) -> None:
    """The regression: get_all_enabled here gave core every node's hostnames."""
    called = _stub_queries(monkeypatch)

    traefik_api.PublicWebRouters().get()

    assert called["core_fronted"], "core's route must ask for the core-fronted webs"
    assert not called["all_enabled"], (
        "core's route asked for every enabled web again - it will request certificates for "
        "hostnames a remote node serves, and claim them alongside it"
    )


@pytest.mark.usefixtures("route_context")
def test_the_node_route_asks_only_for_the_polling_nodes_webs(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the node route stays scoped to its own caller, by node id."""
    called = _stub_queries(monkeypatch)
    asked_for: list[int] = []

    def for_node(node_id: int) -> list:
        asked_for.append(node_id)
        return []

    monkeypatch.setattr(traefik_api.PublicWeb, "get_enabled_for_node", staticmethod(for_node))
    monkeypatch.setattr(
        traefik_api,
        "_authenticated_node",
        lambda _header: types.SimpleNamespace(id=7),
    )

    traefik_api.PublicWebNodeRouters().get()

    assert asked_for == [7]
    assert not called["all_enabled"]
    assert not called["core_fronted"], "a node must not be handed the webs core fronts"
