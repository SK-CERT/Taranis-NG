"""Notify users of what happens to their account, through every channel they can be reached on.

``notify_user`` renders a notification in the user's language into the outbox, one row per
channel that is enabled and has an address for the user (a user without an e-mail address gets
no e-mail), and starts delivering it straight away. What cannot be delivered stays in the outbox:
the scheduler retries it with growing delays and gives up after ``MAX_ATTEMPTS``, leaving it
``failed`` for an administrator to retry.

Raising a notification never fails the change it reports: a broken channel costs the message,
not the user's request.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from flask import current_app, has_request_context
from managers import log_manager
from managers.db_manager import db
from managers.log_manager import logger
from managers.notifications import catalog
from managers.notifications.channels import CHANNELS, ChannelError
from model.notification import NotificationChannel, NotificationEvent, NotificationOutbox
from shared.common import TZ

if TYPE_CHECKING:
    from flask import Flask
    from model.user import User
    from shared.time_manager import SchedulerManager

PASSWORD_CHANGED = "password_changed"  # noqa: S105 - an event name
PASSWORD_REMOVED = "password_removed"  # noqa: S105 - an event name
TOTP_ENABLED = "totp_enabled"
TOTP_DISABLED = "totp_disabled"
PASSKEY_ADDED = "passkey_added"
PASSKEY_REMOVED = "passkey_removed"
MFA_RESET = "mfa_reset"
# In the order the settings list them.
EVENTS = (PASSWORD_CHANGED, PASSWORD_REMOVED, TOTP_ENABLED, TOTP_DISABLED, PASSKEY_ADDED, PASSKEY_REMOVED, MFA_RESET)

# Delays before the 2nd, 3rd, ... attempt, in minutes; the last one repeats.
RETRY_DELAYS_MINUTES = (1, 5, 15, 60, 180, 360)
MAX_ATTEMPTS = 7
CLAIM_BATCH = 20
# A sender that dies mid-delivery frees its notifications after this.
LEASE_MINUTES = 5
MAX_ERROR_LENGTH = 500
KEEP_SENT_DAYS = 30
KEEP_FAILED_DAYS = 90


def retry_delay_minutes(attempts: int) -> int:
    """How long to wait after the given number of failed attempts."""
    index = min(max(attempts, 1), len(RETRY_DELAYS_MINUTES)) - 1
    return RETRY_DELAYS_MINUTES[index]


def instance_url() -> str | None:
    """The address of this Taranis NG, for the signature of a message."""
    hostname = (os.getenv("TARANIS_NG_HOSTNAME") or "").strip()
    return f"https://{hostname}" if hostname else None


def _context(user: User, actor: User | None, details: dict) -> dict:
    """What every notification says about the change: whose account, when, by whom, from where."""
    context = {
        "name": user.name or user.username,
        "username": user.username,
        "time": datetime.now(TZ).strftime("%Y-%m-%d %H:%M %Z"),
        "actor": "self" if actor is None or actor.id == user.id else (actor.name or actor.username),
        "instance_url": instance_url(),
    }
    if has_request_context():
        context["ip"] = log_manager.resolve_ip_address()
    context.update({key: value for key, value in details.items() if value})
    return context


def passkey_details(credential: object) -> dict:
    """What a passkey notification says about the passkey: its name and, when known, its authenticator."""
    from managers import passkey_authenticator_manager  # noqa: PLC0415 - imports the credential model

    details = {"passkey_name": getattr(credential, "name", None)}
    try:
        described = passkey_authenticator_manager.describe(getattr(credential, "aaguid", None))
    except Exception:
        described = None
    if described and described.get("name"):
        details["authenticator"] = described["name"]
    return details


def password_event(before: str | None, after: str | None) -> str | None:
    """Which password event an edit of a user is, from the stored hash before and after it.

    Returns:
        str | None: PASSWORD_CHANGED, PASSWORD_REMOVED, or None when the password did not change.
    """
    if before == after:
        return None
    return PASSWORD_CHANGED if after else PASSWORD_REMOVED


def notify_user(user: User, event: str, *, actor: User | None = None, **details: object) -> int:
    """Queue a notification about the user's account on every channel that reaches them.

    Args:
        user (User): Whose account changed.
        event (str): What happened, one of ``EVENTS``.
        actor (User | None): Who did it, when not the user themself (an administrator).
        **details: Event details for the message (passkey_name, authenticator, factors).

    Returns:
        int: How many notifications were queued.
    """
    try:
        rows = []
        if not NotificationEvent.is_enabled(event):
            return 0
        channels = NotificationChannel.enabled_channels()
        if channels:
            locale = catalog.locale_for(user)
            subject, body = catalog.render(locale, event, _context(user, actor, details))
            for channel in channels:
                channel_class = CHANNELS.get(channel.kind)
                address = channel_class.address_for(user) if channel_class else None
                if address:
                    rows.append(NotificationOutbox(channel.kind, address, event, subject, body, user.id))
        if not rows:
            return 0
        db.session.add_all(rows)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception(f"Could not queue the '{event}' notification for user {getattr(user, 'id', None)}")
        return 0
    deliver_soon()
    return len(rows)


def deliver_soon() -> None:
    """Deliver what is due now, in the background, instead of at the scheduler's next round."""
    try:
        app = current_app._get_current_object()  # noqa: SLF001 - the thread needs the app itself
    except RuntimeError:
        return
    threading.Thread(target=job, args=(app,), name="notification-delivery", daemon=True).start()


CLAIM_SQL = sa.text(
    """
    UPDATE notification_outbox
    SET status = 'sending', attempts = attempts + 1, lease_until = now() + make_interval(mins => :lease)
    WHERE id IN (
        SELECT id FROM notification_outbox
        WHERE (status = 'pending' AND next_attempt_at <= now()) OR (status = 'sending' AND lease_until < now())
        ORDER BY next_attempt_at, id
        LIMIT :batch
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id, channel_kind, recipient, subject, body, attempts
    """,
)


def claim_due() -> list:
    """Take up to ``CLAIM_BATCH`` due notifications for this sender.

    They are marked ``sending`` and committed before anything is sent, so another sender (a
    second core, the scheduler, the immediate delivery thread) skips them; one whose sender died
    becomes due again when its lease runs out.
    """
    rows = db.session.execute(CLAIM_SQL, {"lease": LEASE_MINUTES, "batch": CLAIM_BATCH}).all()
    db.session.commit()
    return rows


def _mark_sent(notification_id: int) -> None:
    db.session.execute(
        sa.text(
            "UPDATE notification_outbox SET status = 'sent', sent_at = now(), lease_until = NULL, last_error = NULL WHERE id = :id",
        ),
        {"id": notification_id},
    )
    db.session.commit()


def _mark_failed(notification_id: int, attempts: int, error: str) -> bool:
    """Schedule a retry, or give up after ``MAX_ATTEMPTS``.

    Returns:
        bool: True when the notification was given up on.
    """
    error = error[:MAX_ERROR_LENGTH]
    if attempts >= MAX_ATTEMPTS:
        db.session.execute(
            sa.text("UPDATE notification_outbox SET status = 'failed', lease_until = NULL, last_error = :error WHERE id = :id"),
            {"id": notification_id, "error": error},
        )
    else:
        db.session.execute(
            sa.text(
                "UPDATE notification_outbox SET status = 'pending', lease_until = NULL, last_error = :error, "
                "next_attempt_at = now() + make_interval(mins => :delay) WHERE id = :id",
            ),
            {"id": notification_id, "error": error, "delay": retry_delay_minutes(attempts)},
        )
    db.session.commit()
    return attempts >= MAX_ATTEMPTS


def deliver_due() -> int:
    """Deliver the notifications that are due.

    Returns:
        int: How many were delivered.
    """
    delivered = 0
    channels = {}
    while rows := claim_due():
        for row in rows:
            if row.channel_kind not in channels:
                channels[row.channel_kind] = NotificationChannel.find(row.channel_kind)
            try:
                _send(row, channels[row.channel_kind])
            except ChannelError as error:
                _report_failure(row, str(error))
                continue
            except Exception as error:
                logger.exception(f"Unexpected error delivering notification {row.id}")
                _report_failure(row, f"Unexpected error: {error}")
                continue
            _mark_sent(row.id)
            delivered += 1
    return delivered


def _send(row: object, channel: NotificationChannel | None) -> None:
    """Deliver one claimed notification through its channel, as the channel is configured now."""
    channel_class = CHANNELS.get(row.channel_kind)
    if channel is None or channel_class is None or not channel.enabled:
        msg = f"The {row.channel_kind} channel is not enabled"
        raise ChannelError(msg)
    channel_class.send(channel.config or {}, channel.get_secret_plaintext(), row.recipient, row.subject, row.body)


def _report_failure(row: object, error: str) -> None:
    """Record a failed attempt; the outbox row is the record administrators see.

    Delivery runs in the scheduler and in a background thread, outside any request, so the
    request-bound activity log is not used here.
    """
    gave_up = _mark_failed(row.id, row.attempts, error)
    if gave_up:
        logger.error(f"Gave up delivering notification {row.id} to {row.recipient} after {row.attempts} attempts: {error}")
    else:
        logger.warning(f"Notification {row.id} to {row.recipient} not delivered (attempt {row.attempts}): {error}")


def purge() -> None:
    """Forget delivered notifications after a month and failed ones after three."""
    db.session.execute(
        sa.text(
            "DELETE FROM notification_outbox WHERE (status = 'sent' AND sent_at < now() - make_interval(days => :sent)) "
            "OR (status = 'failed' AND created_at < now() - make_interval(days => :failed))",
        ),
        {"sent": KEEP_SENT_DAYS, "failed": KEEP_FAILED_DAYS},
    )
    db.session.commit()


def job(app: Flask) -> None:
    """Deliver what is due (the scheduler's job, and the immediate delivery thread)."""
    with app.app_context():
        try:
            deliver_due()
        except Exception:
            db.session.rollback()
            logger.exception("Notification delivery failed")


def purge_job(app: Flask) -> None:
    """Purge old notifications (the scheduler's daily job)."""
    with app.app_context():
        try:
            purge()
        except Exception:
            db.session.rollback()
            logger.exception("Notification purge failed")


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Deliver due notifications every minute and purge old ones daily."""
    manager.schedule_job_minutes(1, job, "Notification delivery", app)
    manager.schedule_job_every_day("03:30", purge_job, "Notification purge", app)


def send_test(kind: str, config: dict, secret: str | None, recipient: str, user: User) -> None:
    """Send a test message right away, with settings that may not be saved yet.

    Raises:
        ValueError: For an unknown channel kind.
        ChannelError: When it could not be delivered.
    """
    channel_class = CHANNELS.get(kind)
    if channel_class is None:
        msg = f"Unknown notification channel: {kind}"
        raise ValueError(msg)
    context = {"name": user.name or user.username, "instance_url": instance_url()}
    subject, body = catalog.render(catalog.locale_for(user), "test", context)
    channel_class.send(config, secret, recipient, subject, body)
