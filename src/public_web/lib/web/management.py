"""Node management API — the endpoints Taranis-NG core calls *in* to this node.

Unlike the public site (host-routed, per web), these are node-level operations
authenticated by the shared node ApiKey (the same key public-web uses to talk to
core). Core uses them to health-check the node and to push a cache reset when a
web's configuration changes, so edits are visible immediately instead of after
the cache TTL. This is a separate blueprint, so the site's per-request ``Host``
routing (``reports_bp.before_request``) does not run here.
"""

from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request
from lib import config, send_mail
from lib.logger import get_logger
from lib.web.cache import WebCache

logger = get_logger("management", silent=True)

management_bp = Blueprint("management", __name__)
cache = WebCache()


def api_key_required(fn: Callable) -> Callable:
    """Require ``Authorization: ApiKey <node key>`` matching this node's key."""

    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> object:
        expected = f"ApiKey {config.taranis_api_key()}"
        if request.headers.get("Authorization") != expected:
            return jsonify({"error": "not authorized"}), HTTPStatus.UNAUTHORIZED
        return fn(*args, **kwargs)

    return wrapper


@management_bp.route("/management/isalive", methods=["GET"], endpoint="isalive")
@api_key_required
def isalive() -> tuple:
    """Liveness probe: core polls this to keep the node's status fresh."""
    return jsonify({"status": "ok"}), HTTPStatus.OK


@management_bp.route("/management/reset-cache", methods=["POST"], endpoint="reset_cache")
@api_key_required
def reset_cache() -> tuple:
    """Clear the cache so a config change made in the GUI takes effect now."""
    cache.clear()
    logger.info("Cache reset requested by core.")
    return jsonify({"reset": True}), HTTPStatus.OK


def _as_recipients(value: object) -> list[str]:
    if isinstance(value, list):
        return [address.strip() for address in value if isinstance(address, str) and address.strip()]
    if isinstance(value, str):
        return [address.strip() for address in value.split(",") if address.strip()]
    return []


def _smtp_from_payload(payload: dict) -> dict[str, str | int] | None:
    host = payload.get("smtp_url")
    if not isinstance(host, str) or not host.strip():
        return None

    host_value = host.strip()
    parsed = urlparse(host_value)
    if parsed.scheme and parsed.hostname:
        host_value = parsed.hostname

    smtp: dict[str, str | int] = {"host": host_value}

    port = payload.get("smtp_port")
    if isinstance(port, int):
        smtp["port"] = port
    elif isinstance(port, str) and port.strip().isdigit():
        smtp["port"] = int(port.strip())
    elif parsed.scheme and parsed.port:
        smtp["port"] = parsed.port

    user = payload.get("smtp_username")
    if isinstance(user, str) and user.strip():
        smtp["user"] = user.strip()

    password = payload.get("smtp_password")
    if isinstance(password, str) and password.strip():
        smtp["password"] = password.strip()

    return smtp


@management_bp.route("/management/test-email", methods=["POST"], endpoint="test_email")
@api_key_required
def test_email() -> tuple:
    """Send a test e-mail using SMTP settings provided by core."""
    payload = request.get_json(silent=True) or {}
    recipients = _as_recipients(payload.get("feedback_recipients"))
    if not recipients:
        return jsonify({"error": "Missing feedback recipients"}), HTTPStatus.BAD_REQUEST

    sender = payload.get("email_sender")
    sender_value = sender.strip() if isinstance(sender, str) and sender.strip() else "public-web@localhost"

    subject = payload.get("email_subject")
    subject_value = subject.strip() if isinstance(subject, str) and subject.strip() else "[public-web] Test e-mail"

    web_name = payload.get("name")
    hostname = payload.get("hostname")
    web_name_value = web_name.strip() if isinstance(web_name, str) and web_name.strip() else "unnamed web"
    host_value = hostname.strip() if isinstance(hostname, str) and hostname.strip() else "unknown-host"

    body = f"This is a public-web SMTP test e-mail.\n\nWeb: {web_name_value}\nHostname: {host_value}\nRecipients: {', '.join(recipients)}"

    success = send_mail(
        body=body,
        subject=subject_value,
        recipients=recipients,
        sender=sender_value,
        logger=logger,
        force_send=True,
        smtp=_smtp_from_payload(payload),
    )

    if success:
        return jsonify({"sent": True}), HTTPStatus.OK
    return jsonify({"error": "Failed to send test e-mail"}), HTTPStatus.BAD_GATEWAY
