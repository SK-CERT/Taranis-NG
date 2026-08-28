"""Core's side of the core->public-web-node channel.

Every side effect here is gated on :func:`public_web_enabled`: a deployment
without at least one configured node has nothing to ping or push to, so the
health-check job and :func:`notify_nodes` return right after that single cheap
existence query instead of loading nodes that cannot exist.

A scheduled job calls each public-web node's management ``isalive`` endpoint and
records a successful contact in ``last_seen``, which drives the green/orange/red
status shown in the Configuration UI (mirroring the other nodes).

That same ``last_seen`` gates the cache-reset pushes sent when a web's
configuration or a product changes: only nodes seen recently are contacted, and
the push runs off the request thread. See :func:`notify_nodes`.

:func:`verify_node` is the third use of the channel — the up-front check run when
an administrator registers or re-points a node, so a URL that leads nowhere is
refused instead of stored.
"""

from __future__ import annotations

import threading
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from collections.abc import Iterable

    from flask import Flask
    from shared.time_manager import SchedulerManager

from managers.db_manager import db
from managers.log_manager import logger
from model.public_web_node import PublicWebNode
from remote.public_web_api import PublicWebApi

_ALLOWED_SCHEMES = ("http", "https")


def public_web_enabled() -> bool:
    """Tell whether this deployment has a public-web node at all.

    Every core-side public-web side effect - the health-check ping, the
    cache-reset pushes, the product hooks - is meaningless without a node to
    talk to, so they all short-circuit on this. Deliberately a live query and
    not a cached flag: core runs several worker processes plus the scheduler,
    so a cached answer would need cross-process invalidation to avoid silently
    swallowing pushes after the first node is registered.

    Returns:
        (bool): True when at least one public-web node is configured.
    """
    return db.session.query(PublicWebNode.id).first() is not None


def job(app: Flask) -> None:
    """Ping every public-web node that has a management URL; refresh last_seen."""
    with app.app_context():
        if not public_web_enabled():
            return
        for node in PublicWebNode.get_all():
            if not node.api_url:
                continue
            try:
                _, status = PublicWebApi(node.api_url, node.api_key).isalive()
                if status == HTTPStatus.OK:
                    node.update_last_seen()
            except Exception as ex:
                logger.debug(f"Public-web node '{node.name}' health check error: {ex}")


def validate_api_url(api_url: str) -> str | None:
    """Check the shape of a node's management URL.

    Deliberately only a format check — a node URL points at an internal service
    (``http://public-web``, a private address), so the SSRF guard used for
    admin-supplied *external* URLs does not apply here.

    Args:
        api_url (str): The URL to check.

    Returns:
        (str | None): A message describing what is wrong, or None if it is fine.
    """
    try:
        parsed = urlparse(api_url)
        port = parsed.port
    except ValueError:
        return "The API URL has an invalid port"
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return "The API URL must start with http:// or https://"
    if not parsed.hostname:
        return "The API URL has no host"
    if any(char.isspace() for char in api_url):
        return "The API URL must not contain whitespace"
    if port is not None and not (1 <= port <= 65535):  # noqa: PLR2004
        return "The API URL has an invalid port"
    if parsed.query or parsed.fragment:
        return "The API URL must not contain a query string or fragment"
    return None


def verify_node(api_url: str, api_key: str) -> str | None:
    """Check that a public-web node is actually there and accepts the API key.

    Mirrors what the collector/publisher/bot nodes do on create: the node is
    contacted before the record is stored, so a typo in the URL or key surfaces
    right away instead of as a node that silently never works.

    Args:
        api_url (str): The node's management URL.
        api_key (str): The shared node API key.

    Returns:
        (str | None): A message describing why the node is unusable, or None if
            it answered the liveness probe.
    """
    invalid = validate_api_url(api_url)
    if invalid:
        return invalid

    body, status = PublicWebApi(api_url, api_key).isalive()
    if status == HTTPStatus.OK:
        return None
    if status == HTTPStatus.UNAUTHORIZED:
        return "The node rejected the API key"
    if status == HTTPStatus.SERVICE_UNAVAILABLE:
        # The transport error itself (a DNS failure inside Docker, a refused
        # connection) is far too verbose for a dialog; it is already logged by
        # the API client at debug level.
        logger.debug(f"Public-web node verification failed for '{api_url}': {body.get('error')}")
        return f"No public-web node answered at '{api_url}' — check the URL and that the node is running"
    if status == HTTPStatus.NOT_FOUND:
        return f"'{api_url}' answered, but it is not a public-web node (no management API there)"
    return f"The node answered with HTTP {status.value}"


def _push_reset_cache(targets: list[tuple[str, str, str]]) -> None:
    """Send the cache reset to each target ``(name, api_url, api_key)``.

    Runs on a worker thread and touches no database state, so it needs no app
    context; failures are logged and otherwise ignored.
    """
    for name, api_url, api_key in targets:
        _, status = PublicWebApi(api_url, api_key).reset_cache()
        if status != HTTPStatus.OK:
            logger.debug(f"Public-web node '{name}' did not accept the cache reset ({status}).")


def notify_nodes(nodes: Iterable[PublicWebNode]) -> None:
    """Push a cache reset to the reachable nodes among ``nodes``, without blocking.

    Nodes with no management URL, and nodes the health check has not seen for a
    long time, are skipped: calling a node that is not running only stalls the
    caller — a failing DNS lookup inside Docker blocks for seconds regardless of
    the HTTP timeout, which is what made the GUI freeze on every edit. Skipping
    costs nothing there, because a node that is down has no cache to reset; it
    reads the current configuration when it starts.

    The push itself runs on a daemon thread so a slow node cannot hold up the API
    response either. It is best-effort in both directions: if it fails, the
    change simply appears once the node's cache TTL expires.

    With no node configured at all it returns before even looking at ``nodes``;
    see :func:`public_web_enabled`.
    """
    if not public_web_enabled():
        return
    targets = [(node.name, node.api_url, node.api_key) for node in nodes if node.api_url and node.is_reachable()]
    if not targets:
        return
    threading.Thread(target=_push_reset_cache, args=(targets,), daemon=True).start()


def initialize(app: Flask) -> None:
    """No-op initializer (kept for symmetry with the other managers)."""


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Schedule the public-web node health check every minute.

    Registered unconditionally: with no node configured the job costs one cheap
    existence query per minute (see :func:`public_web_enabled`), while a node
    registered after boot starts being health-checked without a core restart.
    """
    manager.schedule_job_minutes(1, job, "Public-web node health check", app)
