"""Traefik dynamic-configuration provider.

A public-web node serves any number of branded webs, each on its own hostname,
and those hostnames are configured in the GUI — they live in the database and
nowhere else. Traefik reaches the feed through a catch-all router, which routes
fine but carries no ``Host()`` rule, so ACME has no domain to request a
certificate for.

This endpoint closes that gap: Traefik's HTTP provider polls it and turns every
enabled web into a real router plus the service behind it, which gives ACME a
domain per hostname. Adding a web in the GUI stays the only step an
administrator has to take.

Alongside the routers it serves the rest of the configuration Traefik accepts at
runtime and an administrator can edit — the security-headers middleware, the TLS
options and an optional default certificate (see :mod:`model.traefik_settings`).
Traefik's *static* configuration is a different thing entirely: entry points,
providers and the ACME resolvers themselves are read once at startup from
``docker/.env`` and ``docker/docker-compose.yml``, and nothing served here can
change them.

The route deliberately sits outside ``/api/`` — Traefik only forwards ``/api/``
and ``/sse`` to core, so this is reachable on the compose network but not from
outside. It exposes public website hostnames and nothing else.
"""

from __future__ import annotations

import os
import re
from http import HTTPStatus
from typing import TYPE_CHECKING, Protocol

from flask_restful import Api, Resource
from managers.auth_manager import no_auth
from managers.log_manager import logger
from model.public_web import PublicWeb
from model.traefik_settings import TraefikSettings

if TYPE_CHECKING:
    from collections.abc import Iterable

# Unqualified, so Traefik resolves it within this provider — the definition
# below travels with the routers that use it, built from the GUI settings. The
# catch-all router declared on the public-web container's labels names the
# "@file" copy from docker/traefik/dynamic/fallback.yml instead: that one has to
# work when core is unreachable and this provider yields nothing, which is
# precisely when the node is serving its cache.
_MIDDLEWARE_NAME = "public-web-security-headers"

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

    def get_curve_preferences(self) -> list[str]:
        """Return the TLS key-exchange groups, most preferred first."""
        ...

    def get_default_key_plaintext(self) -> str:
        """Return the decrypted default private key, empty when there is none."""
        ...

    def hsts_header_value(self, *, forced: bool | None = None) -> str:
        """Return the Strict-Transport-Security value; forced overrides the switch."""
        ...


def build_dynamic_config(webs: Iterable[PublicWeb], cert_resolver: str = "", settings: SettingsLike | None = None) -> dict:
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

    Returns:
        (dict): A Traefik dynamic configuration: one router per hostname, one
            service per node, the security-headers middleware, and the TLS
            options and default certificate when configured.
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
        node_url = (node.api_url or "").strip().removesuffix("/") if node else ""
        if not node_url:
            logger.debug(f"Public-web '{web.name}': its node has no API URL, so Traefik cannot be told where to send '{hostname}'")
            continue

        claimed.add(hostname)
        service_name = f"taranis-public-web-node-{node.id}"
        services[service_name] = {"loadBalancer": {"servers": [{"url": node_url}]}}

        # Host-scoped overrides: the web's own resolver and HSTS choice win over
        # the instance-wide values, because both describe this one hostname.
        web_resolver = (getattr(web, "cert_resolver", "") or "").strip() or cert_resolver
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

    config: dict[str, dict] = {}
    if http:
        config["http"] = http
    tls = _build_tls(settings)
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


class PublicWebRouters(Resource):
    """Serve the GUI-managed configuration as a Traefik dynamic configuration."""

    @no_auth
    def get(self) -> tuple[dict, HTTPStatus]:
        """Return the routers, middleware and TLS settings for Traefik's HTTP provider.

        Returns:
            (dict, HTTPStatus): The dynamic configuration.
        """
        settings = TraefikSettings.get()
        # The GUI wins: an administrator who typed a resolver name meant it. The
        # environment variable stays the default for deployments that configured
        # it there before this was settable in the GUI.
        cert_resolver = (settings.cert_resolver or "").strip() or (os.getenv("TRAEFIK_CERT_RESOLVER") or "").strip()
        config = build_dynamic_config(PublicWeb.get_all_enabled(), cert_resolver, settings)
        return config, HTTPStatus.OK


def initialize(api: Api) -> None:
    """Register the Traefik provider endpoint (outside /api/, see the module docstring)."""
    api.add_resource(PublicWebRouters, "/traefik/dynamic")
