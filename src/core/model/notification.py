"""Notification channels and the outbox of messages waiting to be delivered through them.

A channel is a way of reaching users: e-mail today, other services (ntfy, Matrix, Mattermost)
later. There is one row per kind. Its non-secret settings live in the ``config`` JSON column and
its single secret (the SMTP password, an access token) is stored Fernet-encrypted in ``secret``.

A notification is rendered into the outbox when it is raised, in the recipient's language, and
delivered from there. A failed delivery stays in the outbox and is retried; administrators see
the outbox in Configuration > Application Settings > Notifications.

Administrators also choose which events users are notified of; an event without a row is on.
"""

from __future__ import annotations

from datetime import datetime

from managers import crypto_manager
from managers.db_manager import db
from shared.common import TZ

OUTBOX_STATUSES = ("pending", "sending", "sent", "failed")


class NotificationChannel(db.Model):
    """A way of delivering notifications, configured by an administrator.

    Attributes:
        id (int): Record ID.
        kind (str): Channel kind ("email"); one row per kind.
        enabled (bool): Whether notifications are delivered through this channel.
        config (dict): Kind-specific non-secret settings.
        secret (str): Fernet-encrypted secret (e.g. the SMTP password).
        updated_by (str): Who last changed the channel.
        updated_at (datetime): When the channel was last changed.
    """

    __tablename__ = "notification_channel"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(32), nullable=False, unique=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    config = db.Column(db.JSON, nullable=False, default=dict)
    secret = db.Column(db.String(), nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime(timezone=True))

    def __init__(self, kind: str, enabled: bool = False, config: dict | None = None) -> None:
        """Create a channel of the given kind."""
        self.kind = kind
        self.enabled = enabled
        self.config = config or {}
        self.secret = None

    @classmethod
    def find(cls, kind: str) -> NotificationChannel | None:
        """Find the channel of a kind.

        Args:
            kind (str): Channel kind.
        """
        return cls.query.filter_by(kind=kind).first()

    @classmethod
    def enabled_channels(cls) -> list[NotificationChannel]:
        """All channels that deliver notifications."""
        return cls.query.filter_by(enabled=True).order_by(cls.kind).all()

    @property
    def has_secret(self) -> bool:
        """Tell whether a secret is stored."""
        return bool(self.secret)

    def get_secret_plaintext(self) -> str | None:
        """Decrypt the stored secret, or None when absent or undecryptable."""
        if not self.secret:
            return None
        return crypto_manager.decrypt(self.secret)

    @classmethod
    def save(cls, kind: str, enabled: bool, config: dict, secret: str | None, user_name: str) -> NotificationChannel:
        """Create or update the channel of a kind.

        Args:
            kind (str): Channel kind.
            enabled (bool): Whether the channel delivers notifications.
            config (dict): Validated kind-specific settings.
            secret (str | None): A new secret; None or empty keeps the stored one.
            user_name (str): Who is saving.

        Returns:
            NotificationChannel: The saved channel.
        """
        channel = cls.find(kind)
        if channel is None:
            channel = cls(kind)
            db.session.add(channel)
        channel.enabled = bool(enabled)
        channel.config = config
        if secret:
            channel.secret = crypto_manager.encrypt(secret)
        channel.updated_by = user_name
        channel.updated_at = datetime.now(TZ)
        db.session.commit()
        return channel

    def clear_secret(self, user_name: str) -> None:
        """Forget the stored secret (e.g. when the SMTP server no longer needs a login)."""
        self.secret = None
        self.updated_by = user_name
        self.updated_at = datetime.now(TZ)
        db.session.commit()

    def to_json(self) -> dict:
        """Return the GUI-facing representation, never the secret itself."""
        return {
            "kind": self.kind,
            "enabled": self.enabled,
            "config": self.config or {},
            "has_secret": self.has_secret,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationEvent(db.Model):
    """Whether users are notified of one kind of event.

    Attributes:
        event (str): The event ("password_changed", "totp_enabled", ...).
        enabled (bool): Whether it is reported.
        updated_by (str): Who last changed it.
        updated_at (datetime): When it was last changed.
    """

    __tablename__ = "notification_event"

    event = db.Column(db.String(64), primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime(timezone=True))

    def __init__(self, event: str, enabled: bool = True) -> None:
        """Create the switch of an event."""
        self.event = event
        self.enabled = enabled

    @classmethod
    def is_enabled(cls, event: str) -> bool:
        """Tell whether users are notified of an event; one never switched off is."""
        record = db.session.get(cls, event)
        return record is None or bool(record.enabled)

    @classmethod
    def states(cls, events: tuple[str, ...]) -> list[dict]:
        """The switch of each event, in the given order."""
        stored = {record.event: record.enabled for record in cls.query.all()}
        return [{"event": event, "enabled": stored.get(event, True)} for event in events]

    @classmethod
    def save(cls, switches: dict[str, bool], user_name: str) -> None:
        """Turn events on or off.

        Args:
            switches (dict): Event to whether it is reported.
            user_name (str): Who is saving.
        """
        now = datetime.now(TZ)
        for event, enabled in switches.items():
            record = db.session.get(cls, event)
            if record is None:
                record = cls(event)
                db.session.add(record)
            record.enabled = bool(enabled)
            record.updated_by = user_name
            record.updated_at = now
        db.session.commit()


class NotificationOutbox(db.Model):
    """A notification rendered for one recipient on one channel, until it is delivered.

    Times are timezone-aware: the delivery queries compare them with the database clock.

    Attributes:
        id (int): Record ID.
        channel_kind (str): The channel to deliver through.
        recipient (str): The address on that channel (an e-mail address).
        event (str): What happened ("totp_enabled", ...).
        user_id (int): The user it was raised for; NULL once the user is deleted.
        subject (str): The rendered subject.
        body (str): The rendered text.
        status (str): pending, sending (claimed by a sender), sent or failed.
        attempts (int): Delivery attempts so far.
        next_attempt_at (datetime): When a pending notification is due.
        lease_until (datetime): Until when a sending notification belongs to its sender.
        last_error (str): Why the last attempt failed.
        created_at (datetime): When it was raised.
        sent_at (datetime): When it was delivered.
    """

    __tablename__ = "notification_outbox"
    __table_args__ = (db.Index("ix_notification_outbox_status_next_attempt_at", "status", "next_attempt_at"),)

    id = db.Column(db.Integer, primary_key=True)
    channel_kind = db.Column(db.String(32), nullable=False)
    recipient = db.Column(db.String(), nullable=False)
    event = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    subject = db.Column(db.String(), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending", server_default="pending")
    attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    lease_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __init__(self, channel_kind: str, recipient: str, event: str, subject: str, body: str, user_id: int | None = None) -> None:
        """Queue a rendered notification."""
        self.channel_kind = channel_kind
        self.recipient = recipient
        self.event = event
        self.subject = subject
        self.body = body
        self.user_id = user_id
        self.status = "pending"
        self.attempts = 0

    @classmethod
    def recent(cls, status: str | None = None, limit: int = 100) -> list[NotificationOutbox]:
        """The newest notifications, optionally of one status.

        Args:
            status (str | None): Only this status, when given.
            limit (int): At most this many.
        """
        query = cls.query
        if status in OUTBOX_STATUSES:
            query = query.filter_by(status=status)
        return query.order_by(cls.created_at.desc(), cls.id.desc()).limit(max(1, min(limit, 500))).all()

    @classmethod
    def retry(cls, notification_id: int) -> bool:
        """Put a failed notification back in the queue.

        Args:
            notification_id (int): Record ID.

        Returns:
            bool: True when a failed notification was found and requeued.
        """
        record = db.session.get(cls, notification_id)
        if record is None or record.status != "failed":
            return False
        record.status = "pending"
        record.attempts = 0
        record.next_attempt_at = datetime.now(TZ)
        record.lease_until = None
        db.session.commit()
        return True

    def to_json(self) -> dict:
        """Return the GUI-facing representation, without the body."""
        return {
            "id": self.id,
            "channel_kind": self.channel_kind,
            "recipient": self.recipient,
            "event": self.event,
            "subject": self.subject,
            "status": self.status,
            "attempts": self.attempts,
            "next_attempt_at": self.next_attempt_at.isoformat() if self.next_attempt_at else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
