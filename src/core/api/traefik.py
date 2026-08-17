"""Traefik dynamic-configuration provider.

A public-web node serves any number of branded webs, each on its own hostname,
and those hostnames are configured in the GUI — they live in the database and
nowhere else. Traefik reaches the feed through a catch-all router, which routes
fine but carries no ``Host()`` rule, so ACME has no domain to request a
certificate for.

These endpoints close that gap: Traefik's HTTP provider polls one and gets a real
router plus the service behind it per web, which gives ACME a domain per hostname.
Adding a web in the GUI stays the only step an administrator has to take.

There are two, because a web may be fronted by core's own Traefik or by the Traefik
on the node that hosts it:

- ``/traefik/dynamic`` — core's own, unauthenticated, and unrouted: it is reachable
  over the compose network and nothing publishes it. Carries the webs core fronts.
- ``/traefik/dynamic/node`` — polled by a remote node's Traefik, so it IS published
  (on the satellite entrypoint). Authenticated with the node's ``api_key`` and
  scoped to that node, since the payload inlines each web's private key.

Alongside the routers they serve the rest of the configuration Traefik accepts at
runtime and an administrator can edit — the security-headers middleware, the TLS
options and an optional default certificate (see :mod:`model.traefik_settings`).
Traefik's *static* configuration is a different thing entirely: entry points,
providers and the ACME resolvers themselves are read once at startup from
``docker/.env`` and ``docker/docker-compose.yml``, and nothing served here can
change them.
"""

from __future__ import annotations

import os
import re
from http import HTTPStatus
from typing import TYPE_CHECKING, Protocol

from flask import request
from flask_restful import Api, Resource
from managers.auth_manager import no_auth
from managers.log_manager import logger
from model.public_web import PublicWeb
from model.public_web_node import PublicWebNode
from model.traefik_settings import TraefikSettings
from shared.auth import AUTHORIZATION_SCHEME, UNAUTHORIZED_BODY, api_key_matches

if TYPE_CHECKING:
    from collections.abc import Iterable

# Unqualified, so Traefik resolves it within this provider — the definition
# below travels with the routers that use it, built from the GUI settings. The
# catch-all router declared on the public-web container's labels names the
# "@file" copy from docker/traefik/dynamic/fallback.yml instead: that one has to
# work when core is unreachable and this provider yields nothing, which is
# precisely when the node is serving its cache.
_MIDDLEWARE_NAME = "public-web-security-headers"

# Where a node's own Traefik finds the public-web container: the compose service name,
# on the network they share. Both sides ship it - docker-compose.yml names the service
# "public-web", and the ansible worker template names it after the worker_type. See
# build_dynamic_config's for_node for why a node payload must not use node.api_url.
_NODE_LOCAL_BACKEND = "http://public-web"

# Names the serversTransport that governs how Traefik talks TO a public-web node.
# Only bites in a distributed deployment: a single-host node is reached over the
# Docker network as plain http://, where TLS settings simply do not apply.
_TRANSPORT_NAME = "public-web-node"

# Strict-Transport-Security for the whole instance. Named by the GUI, API and SSE
# routers declared on container labels (docker-compose.yml) as well as by the
# generated public-web ones, so unlike the middleware above it is served
# unconditionally - Traefik disables a router naming a middleware it cannot find.
# When HSTS is off the value is "max-age=0", which is also what releases browsers
# that are already pinned. See TraefikSettings.hsts_header_value.
_HSTS_MIDDLEWARE_NAME = "taranis-hsts"
# The per-web overrides. HSTS is scoped to the host and each web is one hostname,
# so a web may opt out of (or into) the instance policy: "-on" forces the header
# with the instance parameters, "-off" sends max-age=0. Both are served whether
# referenced or not - an unreferenced middleware costs Traefik nothing, and a
# stable payload beats one whose shape depends on which override is in use.
_HSTS_ON_MIDDLEWARE_NAME = "taranis-hsts-on"
_HSTS_OFF_MIDDLEWARE_NAME = "taranis-hsts-off"
# public_web.hsts value -> middleware for that web's router.
_HSTS_CHOICES = {"on": _HSTS_ON_MIDDLEWARE_NAME, "off": _HSTS_OFF_MIDDLEWARE_NAME, "": _HSTS_MIDDLEWARE_NAME}

# RFC 1123 host names. The value is interpolated into a backtick-quoted Traefik
# rule, so anything looser would let a stray backtick corrupt the expression.
_HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$",
    re.IGNORECASE,
)


def is_valid_hostname(hostname: str) -> bool:
    """Whether a web's hostname is a syntactically valid host name."""
    return bool(hostname) and bool(_HOSTNAME_PATTERN.match(hostname))


class SettingsLike(Protocol):
    """Exactly what this module reads from the routing settings.

    A protocol rather than :class:`model.traefik_settings.TraefikSettings` itself,
    because the builder is deliberately duck-typed: the tests hand it plain
    stand-ins with these members and nothing else (tests/test_traefik_provider.py),
    which keeps them free of the database and the encryption stack.
    """

    security_headers: dict
    tls_min_version: str
    default_cert: str
    backend_insecure_skip_verify: bool
    backend_root_cas: str

    def get_curve_preferences(self) -> list[str]:
        """Return the TLS key-exchange groups, most preferred first."""
        ...

    def get_default_key_plaintext(self) -> str:
        """Return the decrypted default private key, empty when there is none."""
        ...

    def hsts_header_value(self, *, forced: bool | None = None) -> str:
        """Return the Strict-Transport-Security value; forced overrides the switch."""
        ...


def build_dynamic_config(
    webs: Iterable[PublicWeb],
    cert_resolver: str = "",
    settings: SettingsLike | None = None,
    *,
    for_node: bool = False,
) -> dict:
    """Build the Traefik dynamic configuration for a set of webs.

    Routers *and* their backend services are both declared here, so the result
    stands on its own. Pointing a generated router at the service the docker
    provider derives from the public-web container's labels would look tidier,
    but that service only exists while the container is running: every restart
    would leave the router dangling and Traefik logging "the service ... does not
    exist". A service declared here keeps the config valid, and a node that is
    down simply fails at request time, which is what a down node should do.

    The backend address is the node's own ``api_url`` — the address core already
    uses to reach it — so there is one place to configure it.

    Args:
        webs (Iterable[PublicWeb]): The webs to publish. Skipped: disabled webs,
            webs with no hostname or an invalid one, a hostname already claimed
            by an earlier web, and webs whose node has no ``api_url`` (core has
            no address to hand over).
        cert_resolver (str): Name of the ACME certificate resolver to attach.
            Empty means none, which is Traefik's own default. A name Traefik does
            not know still leaves the router serving traffic, but on the default
            certificate, and logs "Router uses a nonexistent certificate
            resolver" on every provider poll — so this stays opt-in.
        settings (SettingsLike | None): The routing and TLS settings
            (:class:`model.traefik_settings.TraefikSettings`). ``None`` omits
            everything derived from them, which is what the tests and a
            deployment with no row yet get.
        for_node (bool): Whether a NODE's own Traefik reads this payload rather
            than core's. Both effects follow from that Traefik sitting beside the
            public-web container:

            Services point at the container next door (``http://public-web``), not
            at ``node.api_url``. That url is the node's public address on the API
            port, so using it sends the node's Traefik out to the internet and back
            to itself, onto the API entrypoint carrying the web's Host header, which
            matches no router there. ``serversTransport`` is dropped too - the local
            hop is plain http.

            ``tls.options`` and ``tls.stores`` are omitted, because Traefik does not
            namespace those two per provider: the same key from two providers is
            *dropped* rather than merged, failing every router and entrypoint on
            that host with "unknown TLS options: default". A node has both from its
            own file provider, which is what keeps them working while core is
            unreachable. ``tls.certificates`` is per-web and always sent.

    Returns:
        (dict): A Traefik dynamic configuration: one router per hostname, one
            service per node, the security-headers middleware, each web's
            certificate, and - unless for_node - the instance's TLS options and
            default certificate when configured.
    """
    routers: dict[str, dict] = {}
    services: dict[str, dict] = {}
    certificates: list[dict] = []
    claimed: set[str] = set()

    # Built first, because a router may only name a middleware that is actually
    # served: Traefik disables one whose middleware is missing. The
    # security-headers middleware disappears when an administrator clears the
    # header table, and without this the reference would outlive it and take
    # every public web offline.
    middlewares = _build_middlewares(settings)
    servers_transport = _build_servers_transport(settings)

    for web in webs:
        hostname = (web.hostname or "").strip().lower()
        if not web.enabled:
            continue
        if not is_valid_hostname(hostname):
            if hostname:
                logger.debug(f"Public-web '{web.name}': ignoring invalid hostname '{web.hostname}' for Traefik")
            continue
        if hostname in claimed:
            logger.debug(f"Public-web '{web.name}': hostname '{hostname}' is already served by another web; ignoring")
            continue

        node = web.node
        if for_node:
            # The container beside the Traefik reading this. Reached over plain http on
            # a private network, so no api_url is needed - a node with none can still
            # serve its own webs - and no serversTransport either.
            node_url = _NODE_LOCAL_BACKEND
        else:
            node_url = (node.api_url or "").strip().removesuffix("/") if node else ""
            if not node_url:
                logger.debug(f"Public-web '{web.name}': its node has no API URL, so Traefik cannot be told where to send '{hostname}'")
                continue

        claimed.add(hostname)
        service_name = f"taranis-public-web-node-{node.id}"
        load_balancer: dict[str, object] = {"servers": [{"url": node_url}]}
        if servers_transport and not for_node:
            load_balancer["serversTransport"] = _TRANSPORT_NAME
        services[service_name] = {"loadBalancer": load_balancer}

        # Host-scoped overrides: the web's own resolver and HSTS choice win over
        # the instance-wide values, because both describe this one hostname.
        #
        # The NODE sits between them for the resolver, and has to: a resolver name is
        # only meaningful to the Traefik that defines it, and this router is served to
        # whichever Traefik fronts the node. Falling straight through to the
        # instance-wide name handed a remote worker core's name, which that worker does
        # not define - Traefik then logs "Router uses a nonexistent certificate
        # resolver", disables ACME for the router, and quietly serves its default
        # certificate, so the hostname is reachable but on the wrong certificate.
        web_resolver = (
            (getattr(web, "cert_resolver", "") or "").strip() or (getattr(node, "cert_resolver", "") or "").strip() or cert_resolver
        )
        hsts_middleware = _HSTS_CHOICES.get((getattr(web, "hsts", "") or "").strip(), _HSTS_MIDDLEWARE_NAME)
        # Only what is served, in a stable order.
        web_middlewares = [name for name in (_MIDDLEWARE_NAME, hsts_middleware) if name in middlewares]

        # This hostname's own certificate, if it has one. Traefik matches the
        # certificates list by SNI, so it needs no reference from the router.
        # Inline PEM rather than a path: core has no disk Traefik can read.
        # Passed through verbatim, like the default certificate: PEM is
        # whitespace-sensitive enough that trimming here would be a way to break
        # a certificate that parsed fine on save.
        web_cert = getattr(web, "tls_cert", "") or ""
        web_key = web.get_tls_key_plaintext() if hasattr(web, "get_tls_key_plaintext") else ""
        if web_cert.strip() and web_key:
            certificates.append({"certFile": web_cert, "keyFile": web_key})
        elif web_cert.strip():
            logger.error(f"Public-web '{web.name}': its certificate is stored but the private key could not be decrypted; ignoring it")

        # No explicit priority: Traefik orders by rule length, which already puts
        # a Host() rule above the catch-all (priority 1) and below the GUI's
        # longer "Host(...) && PathPrefix(`/`)".
        routers[f"taranis-public-web-{web.id}"] = {
            "entryPoints": ["websecure"],
            "rule": f"Host(`{hostname}`)",
            # Unqualified: Traefik resolves it within this provider.
            "service": service_name,
            "middlewares": web_middlewares,
            "tls": {"certResolver": web_resolver} if web_resolver else {},
        }

    # Every section is left out when it is empty, never sent as an empty object:
    # Traefik decodes this payload with paerser, which reads "routers": {} as a
    # leaf value rather than an empty collection and rejects the whole document
    # with "routers cannot be a standalone element". One empty map therefore
    # costs the middleware and the TLS options too, so nothing that has no
    # content gets a key.
    http: dict[str, dict] = {}
    if routers:
        http["routers"] = routers
    if services:
        http["services"] = services
    if middlewares:
        http["middlewares"] = middlewares
    if servers_transport:
        http["serversTransports"] = {_TRANSPORT_NAME: servers_transport}

    config: dict[str, dict] = {}
    if http:
        config["http"] = http
    tls = {} if for_node else _build_tls(settings)
    if certificates:
        tls["certificates"] = certificates
    if tls:
        config["tls"] = tls
    return config


def _build_middlewares(settings: SettingsLike | None) -> dict:
    """Build the middlewares: the public-web security headers, and HSTS.

    The security-headers one is omitted when there is nothing in it - an
    administrator may clear the table - and the generated routers then stop naming
    it, so nothing is left dangling. HSTS is always emitted when there are
    settings at all, because routers declared on container labels name it and
    Traefik disables a router whose middleware is missing.

    Args:
        settings (SettingsLike | None): The routing and TLS settings, or None.

    Returns:
        (dict): The middlewares, empty only when there are no settings.
    """
    if settings is None:
        return {}

    middlewares: dict[str, dict] = {}

    headers = getattr(settings, "security_headers", None) or {}
    if headers:
        middlewares[_MIDDLEWARE_NAME] = {"headers": {"customResponseHeaders": dict(headers)}}

    if hasattr(settings, "hsts_header_value"):
        for name, forced in ((_HSTS_MIDDLEWARE_NAME, None), (_HSTS_ON_MIDDLEWARE_NAME, True), (_HSTS_OFF_MIDDLEWARE_NAME, False)):
            middlewares[name] = {
                "headers": {"customResponseHeaders": {"Strict-Transport-Security": settings.hsts_header_value(forced=forced)}},
            }

    return middlewares


def _build_servers_transport(settings: SettingsLike | None) -> dict:
    """Build the serversTransport governing how Traefik connects to a public-web node.

    Relevant only when the node's ``api_url`` is https, which means a distributed
    deployment: on a single host the node is reached over the Docker network as plain
    http and none of this applies. There, Traefik is the TLS *client*, and a node
    presenting its own self-signed certificate is rejected unless it is told otherwise.

    Note this is a different trust store from the one the docs describe for the other
    node types: those are called by core's Python ``requests``, this one by Traefik.

    Nothing is emitted unless an administrator configured something, so verification
    stays on by default.

    Args:
        settings (SettingsLike | None): The routing and TLS settings.

    Returns:
        (dict): The transport, empty when nothing is configured.
    """
    if settings is None:
        return {}

    transport: dict[str, object] = {}
    # A CA bundle keeps verification on, so it is the better answer of the two and is
    # honoured even if the switch below is also set.
    root_cas = (getattr(settings, "backend_root_cas", "") or "").strip()
    if root_cas:
        # Inline PEM rather than a path, exactly like the certificates in _build_tls:
        # core has no disk Traefik can read.
        transport["rootCAs"] = [root_cas]
    if getattr(settings, "backend_insecure_skip_verify", False):
        transport["insecureSkipVerify"] = True
        if root_cas:
            logger.warning(
                "Public-web backend TLS: a CA bundle is configured but insecure-skip-verify is also on, "
                "so node certificates are not being verified. Turn the switch off to use the bundle.",
            )
    return transport


def _build_tls(settings: SettingsLike | None) -> dict:
    """Build the TLS section: the handshake options and the default certificate.

    Both are optional. An empty section is left out entirely rather than sent as
    an empty object, so a deployment that configures neither keeps whatever the
    file provider defines.

    Args:
        settings (SettingsLike | None): The routing and TLS settings, or None.

    Returns:
        (dict): The ``tls`` section, empty when nothing is configured.
    """
    tls: dict[str, object] = {}
    if settings is None:
        return tls

    options: dict[str, object] = {}
    if getattr(settings, "tls_min_version", ""):
        options["minVersion"] = settings.tls_min_version
    curves = settings.get_curve_preferences() if hasattr(settings, "get_curve_preferences") else []
    if curves:
        options["curvePreferences"] = curves
    if options:
        tls["options"] = {"default": options}

    # Passed through verbatim: PEM is whitespace-sensitive enough that trimming
    # it here would be a way to break a certificate that parsed fine on save.
    certificate = getattr(settings, "default_cert", "") or ""
    key = settings.get_default_key_plaintext() if hasattr(settings, "get_default_key_plaintext") else ""
    if certificate.strip() and key:
        # Traefik's certFile/keyFile take either a path or the PEM itself, so the
        # certificate travels in the configuration and never touches the disk of
        # a container core cannot write to anyway.
        tls["stores"] = {"default": {"defaultCertificate": {"certFile": certificate, "keyFile": key}}}
    elif certificate.strip():
        logger.error("A default TLS certificate is stored but its private key could not be decrypted; serving without it")

    return tls


def _resolver_for(settings: SettingsLike) -> str:
    """Return the ACME resolver to attach to generated routers.

    The GUI wins: an administrator who typed a resolver name meant it. The environment
    variable stays the default for deployments that configured it there before this was
    settable in the GUI.

    Args:
        settings (SettingsLike): The routing and TLS settings.

    Returns:
        (str): The resolver name, empty when none is configured.
    """
    return (settings.cert_resolver or "").strip() or (os.getenv("TRAEFIK_CERT_RESOLVER") or "").strip()


class PublicWebRouters(Resource):
    """Serve CORE's own Traefik its slice of the configuration.

    Unauthenticated. That is safe only because nothing routes this path publicly: core is
    published at ``/api/`` and ``/sse`` alone, so the local Traefik reaches it over the
    Docker network. A *remote* Traefik must use :class:`PublicWebNodeRouters` instead,
    which authenticates and scopes the payload to the node that polled it.

    Scoped to the nodes core actually fronts, which is not the same as "all of them" -
    see :meth:`model.public_web.PublicWeb.get_enabled_fronted_by_core`.
    """

    @no_auth
    def get(self) -> tuple[dict, HTTPStatus]:
        """Return the routers, middleware and TLS settings for Traefik's HTTP provider.

        Returns:
            (dict, HTTPStatus): The dynamic configuration.
        """
        settings = TraefikSettings.get()
        config = build_dynamic_config(PublicWeb.get_enabled_fronted_by_core(), _resolver_for(settings), settings)
        return config, HTTPStatus.OK


class PublicWebNodeRouters(Resource):
    """Serve one node's slice of the Traefik configuration, to that node's own Traefik.

    This is the route a remote worker polls, so it is the one that may be published. It
    is authenticated with the node's own ``api_key`` - the same credential the node
    already uses everywhere else - and returns only that node's webs, with each web's
    own certificate.

    Scoping is the point. The unscoped payload inlines every web's private key, and a
    worker has no business holding another node's.

    Built with ``for_node``, which also decides the backend address and drops the
    instance-wide TLS section; see :func:`build_dynamic_config`.
    """

    @no_auth
    def get(self) -> tuple[dict, HTTPStatus]:
        """Return the polling node's routers, middleware and TLS settings.

        Returns:
            (dict, HTTPStatus): The node's dynamic configuration, or 401 when the
                request carries no recognised node key.
        """
        node = _authenticated_node(request.headers.get("Authorization"))
        if node is None:
            return dict(UNAUTHORIZED_BODY), HTTPStatus.UNAUTHORIZED
        settings = TraefikSettings.get()
        config = build_dynamic_config(
            PublicWeb.get_enabled_for_node(node.id),
            _resolver_for(settings),
            settings,
            for_node=True,
        )
        return config, HTTPStatus.OK


def _authenticated_node(auth_header: str | None) -> PublicWebNode | None:
    """Resolve the ``Authorization`` header to the node that sent it.

    The key is looked up first and then re-checked with the shared constant-time
    comparison, so the answer does not depend on how the database matched it.

    Args:
        auth_header (str | None): The request's ``Authorization`` header.

    Returns:
        (PublicWebNode | None): The node, or None when the header is missing, malformed
            or names no known node.
    """
    if not auth_header or not auth_header.startswith(f"{AUTHORIZATION_SCHEME} "):
        return None
    api_key = auth_header[len(AUTHORIZATION_SCHEME) + 1 :]
    node = PublicWebNode.get_by_api_key(api_key)
    if node is None or not api_key_matches(auth_header, node.api_key or ""):
        return None
    return node


def initialize(api: Api) -> None:
    """Register the Traefik provider endpoints (outside /api/, see the module docstring)."""
    api.add_resource(PublicWebRouters, "/traefik/dynamic")
    api.add_resource(PublicWebNodeRouters, "/traefik/dynamic/node")
