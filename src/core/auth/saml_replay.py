"""Atomic Redis replay protection for verified SAML message identifiers."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime

from managers.cache_manager import redis_client

KEY_PREFIX = "saml_replay:v1"
MAX_IDENTIFIER_LENGTH = 256
MAX_IDENTIFIERS = 2
MAX_ASSERTION_LIFETIME_SECONDS = 24 * 60 * 60

_CLAIM_SCRIPT = """
for index = 1, #KEYS do
    if redis.call('EXISTS', KEYS[index]) == 1 then
        return 0
    end
end
for index = 1, #KEYS do
    redis.call('SET', KEYS[index], '1', 'EX', ARGV[1])
end
return 1
"""


def _ttl_seconds(expires_at: datetime, now: datetime | None = None) -> int:
    """Return a bounded Redis TTL derived from a verified assertion expiry."""
    if expires_at.tzinfo is None:
        msg = "SAML assertion expiry must include a timezone"
        raise ValueError(msg)
    current = now or datetime.now(UTC)
    ttl = math.ceil((expires_at.astimezone(UTC) - current.astimezone(UTC)).total_seconds())
    if ttl < 1:
        msg = "SAML assertion has already expired"
        raise ValueError(msg)
    if ttl > MAX_ASSERTION_LIFETIME_SECONDS:
        msg = f"SAML assertion lifetime exceeds {MAX_ASSERTION_LIFETIME_SECONDS} seconds"
        raise ValueError(msg)
    return ttl


def claim(provider_id: int, identifiers: tuple[str, ...], expires_at: datetime) -> bool:
    """Atomically claim verified Response/Assertion IDs until assertion expiry.

    A false result means at least one identifier was already seen. No key is
    written in that case, so concurrent callbacks cannot partially reserve a
    Response/Assertion pair.
    """
    unique = tuple(dict.fromkeys(identifiers))
    if not isinstance(provider_id, int) or isinstance(provider_id, bool) or provider_id < 1:
        msg = "SAML replay provider ID must be a positive integer"
        raise ValueError(msg)
    if not unique or len(unique) > MAX_IDENTIFIERS:
        msg = "SAML replay protection needs one or two verified identifiers"
        raise ValueError(msg)
    if any(not isinstance(identifier, str) or not identifier or len(identifier) > MAX_IDENTIFIER_LENGTH for identifier in unique):
        msg = "SAML message identifier is missing or too long"
        raise ValueError(msg)

    ttl = _ttl_seconds(expires_at)
    keys = [f"{KEY_PREFIX}:{provider_id}:{hashlib.sha256(identifier.encode()).hexdigest()}" for identifier in unique]
    return bool(redis_client.eval(_CLAIM_SCRIPT, len(keys), *keys, ttl))
