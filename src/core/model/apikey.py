"""API key model.

An API key lets a script call the API as its owner: ``Authorization: ApiKey <key>`` works on
every ``auth_required`` endpoint that does not refuse keys (see
:func:`managers.auth_manager.auth_required`). Only a SHA-256 hash of the key is stored. The key
itself is shown once, when it is created, and ``key_prefix`` is kept so people can tell keys apart.

A key either acts with all of its owner's permissions, or, when ``restricted``, with the
permissions picked for it that the owner still has. A restricted key with nothing picked has no
permissions, so deleting a permission can never widen a key. Its IP allowlist and the site-wide
one (security settings) both have to admit the caller (see :mod:`managers.ip_allowlist`).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from managers import ip_allowlist
from managers.db_manager import db
from model.permission import Permission
from model.user import User
from shared.common import TZ
from sqlalchemy import or_, update

KEY_PREFIX = "tnk_"
PREFIX_LENGTH = 12
NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 500
TOUCH_INTERVAL = timedelta(seconds=60)
# An expiry picked as a date runs to the end of that day, up to a day past now + max_days.
EXPIRY_GRACE = timedelta(days=1)


def hash_key(plain: str) -> str:
    """Return the hex SHA-256 of a key: what is stored and looked up.

    A key carries 256 random bits, so a fast hash is enough; there is nothing to brute-force.
    """
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def new_secret() -> str:
    """Return a new random key: ``tnk_`` and 43 URL-safe characters (256 bits)."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def aware(value: datetime | None) -> datetime | None:
    """Return a datetime with a time zone; a naive one is taken to be in the server's zone."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=TZ)


def parse_expiry(value: object) -> datetime | None:
    """Parse an expiry from the API or the CLI: ISO 8601, a naive one in the server's zone.

    Raises:
        ValueError: When the value is not a date or a date and time.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return aware(value)
    try:
        parsed = datetime.fromisoformat(str(value).strip())
    except ValueError:
        msg = f"'{value}' is not a valid expiry date"
        raise ValueError(msg) from None
    return aware(parsed)


def check_expiry(expires_at: datetime | None, policy: dict, now: datetime | None = None) -> None:
    """Check an expiry of a new key against the policy.

    Raises:
        ValueError: When an expiry is required and missing, in the past, or beyond the maximum lifetime.
    """
    now = now or datetime.now(TZ)
    if expires_at is None:
        if policy.get("require_expiry") or policy.get("max_days"):
            msg = "API keys must have an expiry date"
            raise ValueError(msg)
        return
    if expires_at <= now:
        msg = "The expiry date must be in the future"
        raise ValueError(msg)
    max_days = policy.get("max_days")
    if max_days and expires_at > now + timedelta(days=max_days) + EXPIRY_GRACE:
        msg = f"API keys may be valid for at most {max_days} days"
        raise ValueError(msg)


def _iso(value: datetime | None) -> str | None:
    value = aware(value)
    return value.isoformat() if value else None


def _permission_ids(values: object) -> list[str]:
    """Permission ids from a list of ids or of ``{"id": ...}`` objects, in order, without duplicates."""
    ids: list[str] = []
    for value in values or []:
        permission_id = value.get("id") if isinstance(value, dict) else value
        if isinstance(permission_id, str) and permission_id and permission_id not in ids:
            ids.append(permission_id)
    return ids


class ApiKeyPermission(db.Model):
    """A permission picked for a restricted API key."""

    __tablename__ = "api_key_permission"

    api_key_id = db.Column(db.Integer, db.ForeignKey("api_key.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.String, db.ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True)


class ApiKey(db.Model):
    """API key model.

    Attributes:
        id (int): API key ID.
        name (str): Name, unique per owner.
        description (str | None): What the key is for.
        key_hash (str): Hex SHA-256 of the key.
        key_prefix (str): The first characters of the key, to recognise it by.
        created_at (datetime): When the key was created.
        created_by (str | None): Username of whoever created it (the owner, an admin, or the CLI).
        user_id (int): Owner; the key acts as this user.
        expires_at (datetime | None): When the key stops working; None is never.
        enabled (bool): False pauses the key.
        restricted (bool): Whether only the picked ``permissions`` apply.
        allowed_ips (str | None): The key's IP allowlist, one network per line; None is any address.
        last_used_at (datetime | None): When the key last authenticated a request (updated at most once a minute).
        last_used_ip (str | None): The trusted client address of that request.
        expiry_notified_at (datetime | None): When the owner was told the key expired; None until then.
    """

    __tablename__ = "api_key"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="api_key_user_id_name_key"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=True)
    key_hash = db.Column(db.String(64), nullable=False, unique=True)
    key_prefix = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(TZ))
    created_by = db.Column(db.String(), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    restricted = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    allowed_ips = db.Column(db.Text, nullable=True)
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_used_ip = db.Column(db.String(), nullable=True)
    expiry_notified_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship(User, lazy="joined")
    permissions = db.relationship(Permission, secondary="api_key_permission", lazy="selectin")

    # --- lookup ---------------------------------------------------------------------------

    @classmethod
    def find(cls, api_key_id: int) -> ApiKey | None:
        """Find an API key by ID."""
        return db.session.get(cls, api_key_id)

    @classmethod
    def find_for_user(cls, api_key_id: int, user_id: int) -> ApiKey | None:
        """Find an API key by ID when it belongs to the given user."""
        record = cls.find(api_key_id)
        return record if record and record.user_id == user_id else None

    @classmethod
    def find_by_key(cls, plain: str | None) -> ApiKey | None:
        """Find the API key a presented key belongs to, by its hash."""
        if not plain:
            return None
        return cls.query.filter_by(key_hash=hash_key(plain)).first()

    @classmethod
    def find_by_name(cls, name: str, user_id: int | None = None) -> ApiKey | None:
        """Find an API key by name, of one owner or, when not given, the first of any owner."""
        query = cls.query.filter_by(name=name)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.order_by(cls.id).first()

    @classmethod
    def get_filtered(cls, search: str | None = None, user_id: int | None = None) -> list[ApiKey]:
        """List API keys by name, optionally of one owner and matching a search string."""
        query = cls.query.join(User, cls.user_id == User.id)
        if user_id is not None:
            query = query.filter(cls.user_id == user_id)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    cls.name.ilike(pattern),
                    cls.description.ilike(pattern),
                    cls.key_prefix.ilike(pattern),
                    User.username.ilike(pattern),
                    User.name.ilike(pattern),
                ),
            )
        return query.order_by(db.func.lower(cls.name), cls.id).all()

    @classmethod
    def expired_unreported(cls, now: datetime) -> list[ApiKey]:
        """List keys that have expired and whose owner has not been told yet."""
        return cls.query.filter(cls.expires_at <= now, cls.expiry_notified_at.is_(None)).order_by(cls.id).all()

    @classmethod
    def get_all(cls) -> list[ApiKey]:
        """List every API key, by name."""
        return cls.get_filtered()

    # --- state ----------------------------------------------------------------------------

    def is_expired(self, now: datetime | None = None) -> bool:
        """Tell whether the key's expiry has passed."""
        expires_at = aware(self.expires_at)
        return expires_at is not None and expires_at <= (now or datetime.now(TZ))

    def refusal(self, ip: str | None, site_allowlist: str | None, now: datetime | None = None) -> str | None:
        """Say why the key cannot authenticate a request from ``ip``, or None when it can.

        The owner's account status is checked by the caller, which logs it on its own.
        """
        if not self.enabled:
            return "the key is disabled"
        if self.is_expired(now):
            return "the key has expired"
        if not ip_allowlist.allows(site_allowlist, ip):
            return f"client IP {ip} is not in the site-wide allowlist"
        if not ip_allowlist.allows(self.allowed_ips, ip):
            return f"client IP {ip} is not in the key's allowlist"
        return None

    def effective_permissions(self, owner_permissions: set[str] | None) -> set[str]:
        """Return what the key may do: the owner's permissions, or the picked ones the owner still has."""
        owner_permissions = set(owner_permissions or ())
        if not self.restricted:
            return owner_permissions
        return owner_permissions & {permission.id for permission in self.permissions}

    def touch(self, ip: str | None, now: datetime | None = None) -> None:
        """Record a use of the key, at most once a minute unless the address changed.

        Never fails the request it is called for: a failed write is rolled back and skipped.
        """
        now = now or datetime.now(TZ)
        last = aware(self.last_used_at)
        if last is not None and now - last < TOUCH_INTERVAL and self.last_used_ip == ip:
            return
        try:
            db.session.execute(update(ApiKey).where(ApiKey.id == self.id).values(last_used_at=now, last_used_ip=ip))
            db.session.commit()
        except Exception:
            db.session.rollback()

    def to_dict(self, now: datetime | None = None) -> dict:
        """Return the key for the API; never the hash."""
        owner = self.user
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "key_prefix": self.key_prefix,
            "user": {"id": owner.id, "username": owner.username, "name": owner.name} if owner else None,
            "user_id": self.user_id,
            "created_at": _iso(self.created_at),
            "created_by": self.created_by,
            "expires_at": _iso(self.expires_at),
            "expired": self.is_expired(now),
            "enabled": bool(self.enabled),
            "restricted": bool(self.restricted),
            "permissions": sorted(
                ({"id": permission.id, "name": permission.name, "description": permission.description} for permission in self.permissions),
                key=lambda permission: permission["id"],
            ),
            "allowed_ips": ip_allowlist.as_list(self.allowed_ips),
            "last_used_at": _iso(self.last_used_at),
            "last_used_ip": self.last_used_ip,
        }

    # --- changes --------------------------------------------------------------------------

    @staticmethod
    def _clean_name(value: object) -> str:
        name = str(value or "").strip()
        if not name:
            msg = "The API key needs a name"
            raise ValueError(msg)
        if len(name) > NAME_MAX_LENGTH:
            msg = f"The API key name may be at most {NAME_MAX_LENGTH} characters long"
            raise ValueError(msg)
        return name

    @staticmethod
    def _clean_description(value: object) -> str | None:
        description = str(value or "").strip()
        if len(description) > DESCRIPTION_MAX_LENGTH:
            msg = f"The API key description may be at most {DESCRIPTION_MAX_LENGTH} characters long"
            raise ValueError(msg)
        return description or None

    @classmethod
    def _check_name_free(cls, user_id: int, name: str, exclude_id: int | None = None) -> None:
        existing = cls.find_by_name(name, user_id)
        if existing and existing.id != exclude_id:
            msg = f"The user already has an API key named '{name}'"
            raise ValueError(msg)

    @staticmethod
    def _pick_permissions(requested: list[str], owner: User, already: set[str] | None = None) -> list[Permission]:
        """Resolve picked permission ids; each must be the owner's (or already on the key)."""
        allowed = set(owner.get_permissions()) | (already or set())
        foreign = [permission_id for permission_id in requested if permission_id not in allowed]
        if foreign:
            msg = f"An API key cannot grant permissions its owner does not have: {', '.join(foreign)}"
            raise ValueError(msg)
        permissions = [Permission.find(permission_id) for permission_id in requested]
        return [permission for permission in permissions if permission is not None]

    @classmethod
    def create(cls, owner: User, data: dict, *, created_by: str | None, policy: dict) -> tuple[ApiKey, str]:
        """Create an API key for ``owner``.

        Args:
            owner (User): Whom the key acts as.
            data (dict): name, description, expires_at, restricted, permissions, allowed_ips.
            created_by (str | None): Username of whoever creates it.
            policy (dict): The API key policy (``SecuritySettings.get_api_key_policy()``).

        Returns:
            tuple: The new key and its plaintext, which is not stored and cannot be shown again.

        Raises:
            ValueError: When the data breaks a rule; the message says which.
        """
        if owner is None:
            msg = "The API key needs an owner"
            raise ValueError(msg)
        name = cls._clean_name(data.get("name"))
        cls._check_name_free(owner.id, name)
        description = cls._clean_description(data.get("description"))
        expires_at = parse_expiry(data.get("expires_at"))
        check_expiry(expires_at, policy)
        restricted = bool(data.get("restricted"))
        permissions = cls._pick_permissions(_permission_ids(data.get("permissions")), owner) if restricted else []
        allowed_ips = ip_allowlist.normalize(data.get("allowed_ips"))
        if policy.get("require_allowlist") and not allowed_ips:
            msg = "API keys must have an IP allowlist"
            raise ValueError(msg)

        plaintext = new_secret()
        record = cls()
        record.name = name
        record.description = description
        record.key_hash = hash_key(plaintext)
        record.key_prefix = plaintext[:PREFIX_LENGTH]
        record.created_at = datetime.now(TZ)
        record.created_by = created_by
        record.user_id = owner.id
        record.user = owner
        record.expires_at = expires_at
        record.enabled = data.get("enabled", True) is not False
        record.restricted = restricted
        record.permissions = permissions
        record.allowed_ips = allowed_ips
        db.session.add(record)
        db.session.commit()
        return record, plaintext

    def apply_update(self, data: dict, *, policy: dict) -> None:
        """Change the fields present in ``data``: name, description, enabled, scope, allowed IPs.

        Everything is checked before anything changes. The owner and the expiry never change;
        a new key replaces one that should last longer.

        Raises:
            ValueError: When the data breaks a rule; the message says which.
        """
        changes: dict = {}
        if "name" in data:
            changes["name"] = self._clean_name(data.get("name"))
            self._check_name_free(self.user_id, changes["name"], exclude_id=self.id)
        if "description" in data:
            changes["description"] = self._clean_description(data.get("description"))
        if "enabled" in data:
            changes["enabled"] = bool(data.get("enabled"))
        if "restricted" in data or "permissions" in data:
            restricted = bool(data.get("restricted", self.restricted))
            current = [permission.id for permission in self.permissions]
            requested = _permission_ids(data["permissions"]) if "permissions" in data else current
            changes["restricted"] = restricted
            changes["permissions"] = self._pick_permissions(requested, self.user, already=set(current)) if restricted else []
        if "allowed_ips" in data:
            changes["allowed_ips"] = ip_allowlist.normalize(data.get("allowed_ips"))
            if policy.get("require_allowlist") and not changes["allowed_ips"]:
                msg = "API keys must have an IP allowlist"
                raise ValueError(msg)
        for field, value in changes.items():
            setattr(self, field, value)
        db.session.commit()

    @classmethod
    def delete(cls, api_key_id: int) -> None:
        """Delete an API key."""
        record = db.session.get(cls, api_key_id)
        if record is not None:
            db.session.delete(record)
            db.session.commit()
