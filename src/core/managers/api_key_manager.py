"""Managing user API keys: what the admin and the self-service endpoints share.

Every change is written to the activity log and reported to the key's owner (see
:mod:`managers.notification_manager`). The plaintext of a new key is returned once, by
:func:`create`, and never stored or logged.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from managers import ip_allowlist, log_manager, notification_manager
from managers.db_manager import db
from managers.log_manager import logger
from model.apikey import ApiKey
from model.permission import Permission
from model.security_settings import SecuritySettings
from shared.common import TZ

if TYPE_CHECKING:
    from flask import Flask
    from model.user import User
    from shared.time_manager import SchedulerManager

EXPIRY_CHECK_MINUTES = 5


def public_policy() -> dict:
    """The API key policy as the GUI needs it; the site-wide list is only said to exist."""
    policy = SecuritySettings.get_api_key_policy()
    return {
        "require_expiry": policy["require_expiry"] or bool(policy["max_days"]),
        "max_days": policy["max_days"],
        "require_allowlist": policy["require_allowlist"],
        "site_allowlist_active": bool(ip_allowlist.as_list(policy["allowed_ips"])),
    }


def permission_options(user: User | None) -> list[dict]:
    """The permissions a key of ``user`` can be limited to: the user's own, by id."""
    if user is None:
        return []
    permissions = [Permission.find(permission_id) for permission_id in sorted(user.get_permissions())]
    return [
        {"id": permission.id, "name": permission.name, "description": permission.description}
        for permission in permissions
        if permission is not None
    ]


def list_payload(keys: list[ApiKey], *, permissions_of: User | None = None, owners: list[User] | None = None) -> dict:
    """The answer of a list request: the keys, the policy, the caller's address and the pickers' options."""
    payload = {
        "total_count": len(keys),
        "items": [key.to_dict() for key in keys],
        "policy": public_policy(),
        "client_ip": ip_allowlist.client_ip(),
    }
    payload["client_ip_public"] = ip_allowlist.is_public_address(payload["client_ip"])
    if permissions_of is not None:
        payload["available_permissions"] = permission_options(permissions_of)
    if owners is not None:
        payload["owners"] = [{"id": owner.id, "username": owner.username, "name": owner.name, "status": owner.status} for owner in owners]
    return payload


def _describe(api_key: ApiKey) -> str:
    owner = api_key.user.username if api_key.user else f"user id {api_key.user_id}"
    return f"API key '{api_key.name}' ({api_key.key_prefix}…) of {owner}"


def create(owner: User, data: dict, actor: User) -> tuple[dict, str]:
    """Create a key for ``owner`` on behalf of ``actor``.

    Returns:
        tuple: The key as the API shows it, and its plaintext (shown once).

    Raises:
        ValueError: When the data breaks a rule.
    """
    record, plaintext = ApiKey.create(owner, data, created_by=actor.username, policy=SecuritySettings.get_api_key_policy())
    log_manager.store_user_activity(actor, "API_KEY_CREATE", f"{_describe(record)} created")
    notification_manager.notify_user(owner, notification_manager.API_KEY_CREATED, actor=actor, **notification_manager.api_key_details(record))
    return record.to_dict(), plaintext


def update(record: ApiKey, data: dict, actor: User) -> dict:
    """Change a key on behalf of ``actor``.

    Raises:
        ValueError: When the data breaks a rule.
    """
    record.apply_update(data, policy=SecuritySettings.get_api_key_policy())
    fields = ("name", "description", "enabled", "restricted", "permissions", "allowed_ips")
    changed = ", ".join(field for field in fields if field in data)
    log_manager.store_user_activity(actor, "API_KEY_UPDATE", f"{_describe(record)} updated ({changed})")
    return record.to_dict()


def delete(record: ApiKey, actor: User) -> None:
    """Delete a key on behalf of ``actor``; its owner is told."""
    owner = record.user
    details = notification_manager.api_key_details(record)
    description = _describe(record)
    ApiKey.delete(record.id)
    log_manager.store_user_activity(actor, "API_KEY_DELETE", f"{description} deleted")
    if owner is not None:
        notification_manager.notify_user(owner, notification_manager.API_KEY_DELETED, actor=actor, **details)


def notify_expired(now: datetime | None = None) -> int:
    """Tell the owners of keys that have expired since the last run; each expiry is told once.

    Keys are marked before anyone is told, so a failure can lose a message but never repeat
    one. Disabled keys and keys of accounts that are not active are marked without a message.

    Returns:
        int: How many owners were told.
    """
    now = now or datetime.now(TZ)
    expired = ApiKey.expired_unreported(now)
    if not expired:
        return 0
    for record in expired:
        record.expiry_notified_at = now
    db.session.commit()
    told = 0
    for record in expired:
        owner = record.user
        if record.enabled and owner is not None and owner.status == "active":
            details = notification_manager.api_key_details(record, expired=True)
            notification_manager.notify_user(owner, notification_manager.API_KEY_EXPIRED, system=True, **details)
            told += 1
    return told


def expiry_job(app: Flask) -> None:
    """Report expired API keys (the scheduler's job)."""
    with app.app_context():
        try:
            notify_expired()
        except Exception:
            db.session.rollback()
            logger.exception("Reporting expired API keys failed")


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Look for expired API keys every few minutes."""
    manager.schedule_job_minutes(EXPIRY_CHECK_MINUTES, expiry_job, "API key expiry notices", app)
