"""Opaque, typed, one-time authentication transactions backed by Redis."""

from __future__ import annotations

import json
import re
import secrets
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from managers.cache_manager import redis_client

TOKEN_BYTES = 32
TOKEN_LENGTH = 43
MAX_TTL_SECONDS = 30 * 60
MAX_SERIALIZED_BYTES = 64 * 1024
CREATE_ATTEMPTS = 4
KEY_PREFIX = "auth_transaction:v1"
TOKEN_PATTERN = re.compile(rf"^[A-Za-z0-9_-]{{{TOKEN_LENGTH}}}$")


class AuthTransactionKind(StrEnum):
    """Namespaces for authentication transactions that must not be interchangeable."""

    OAUTH_STATE = "oauth_state"
    REDIRECT_REDEMPTION = "redirect_redemption"
    SAML_DISCOVERY = "saml_discovery"
    SAML_STATE = "saml_state"
    MFA = "mfa"
    MFA_ENROLLMENT = "mfa_enrollment"


def _key(kind: AuthTransactionKind, token: str) -> str | None:
    """Return the Redis key for a valid opaque token, otherwise ``None``."""
    if not isinstance(kind, AuthTransactionKind) or not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        return None
    return f"{KEY_PREFIX}:{kind.value}:{token}"


def _decode(kind: AuthTransactionKind, raw: bytes | str | None) -> dict[str, Any] | None:
    """Decode and validate a stored transaction envelope."""
    if raw is None:
        return None
    if not isinstance(raw, (bytes, str)) or len(raw.encode() if isinstance(raw, str) else raw) > MAX_SERIALIZED_BYTES:
        return None
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(envelope, dict) or envelope.get("version") != 1 or envelope.get("kind") != kind.value:
        return None
    payload = envelope.get("payload")
    return payload if isinstance(payload, dict) else None


def create(kind: AuthTransactionKind, payload: Mapping[str, Any], ttl_seconds: int) -> str:
    """Store a transaction and return a 256-bit opaque handle.

    ``NX`` makes the already-improbable token collision harmless. Authentication
    fails closed if Redis cannot store the transaction.
    """
    if not isinstance(kind, AuthTransactionKind):
        msg = "Authentication transaction kind must be an AuthTransactionKind"
        raise TypeError(msg)
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        msg = f"Authentication transaction TTL must be between 1 and {MAX_TTL_SECONDS} seconds"
        raise ValueError(msg)
    if not isinstance(payload, Mapping):
        msg = "Authentication transaction payload must be a mapping"
        raise TypeError(msg)

    try:
        envelope = json.dumps(
            {"version": 1, "kind": kind.value, "payload": dict(payload)},
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as ex:
        msg = "Authentication transaction payload must be JSON serializable"
        raise ValueError(msg) from ex
    if len(envelope.encode()) > MAX_SERIALIZED_BYTES:
        msg = f"Authentication transaction envelope exceeds {MAX_SERIALIZED_BYTES} bytes"
        raise ValueError(msg)
    for _ in range(CREATE_ATTEMPTS):
        token = secrets.token_urlsafe(TOKEN_BYTES)
        key = _key(kind, token)
        if key and redis_client.set(key, envelope, ex=ttl_seconds, nx=True):
            return token
    msg = "Could not allocate a unique authentication transaction"
    raise RuntimeError(msg)


def peek(kind: AuthTransactionKind, token: str) -> dict[str, Any] | None:
    """Read a transaction without consuming it."""
    key = _key(kind, token)
    return _decode(kind, redis_client.get(key)) if key else None


def consume(kind: AuthTransactionKind, token: str) -> dict[str, Any] | None:
    """Atomically read and delete a transaction using Redis ``GETDEL``."""
    key = _key(kind, token)
    return _decode(kind, redis_client.getdel(key)) if key else None
