"""Failed-login throttling backed by Redis.

A failed form login (password or LDAP) or a wrong second factor increments a
per-username counter in Redis. Once the counter passes a threshold, further
attempts for that username are refused before any credential check happens, for
a lockout that doubles with each additional failure (5, 10, 20 ... minutes, up
to LOCKOUT_MAX_SECONDS). Successful logins reset the counter, and so does a
FAIL_WINDOW of quiet measured from the later of the last failure and the end of
the last lockout.

The counters are process-wide singletons reached through Redis, so every
gunicorn worker shares the same view of a username's failures. Redis being
momentarily unavailable degrades to "no throttling" rather than to "no login":
every helper swallows connection errors.
"""

from __future__ import annotations

import time

from managers.cache_manager import redis_client
from managers.log_manager import logger

# Attempt counter: the count resets once a username goes FAIL_WINDOW seconds
# without a new failure.
FAIL_THRESHOLD = 5
FAIL_WINDOW = 300  # seconds of quiet after which the failure count is forgotten

# Progressive lockout: locked_until = now + LOCKOUT_SECONDS * LOCKOUT_MULTIPLIER ** overkill,
# where overkill counts the failures past FAIL_THRESHOLD (5, 10, 20, ... minutes).
LOCKOUT_SECONDS = 300
LOCKOUT_MULTIPLIER = 2  # each failure beyond the threshold doubles the lockout
LOCKOUT_MAX_SECONDS = 86400  # a day; without a cap the doubling runs away to months

_KEY = "login_fail:{username}"


def _now() -> int:
    return int(time.time())


def _encode(fails: int, last_fail: int, locked_until: int) -> str:
    return f"{fails}:{last_fail}:{locked_until}"


def _decode(raw: bytes | str | None) -> tuple[int, int, int]:
    """Decode a counter entry; a missing or malformed one reads as zeroed."""
    if not raw:
        return 0, 0, 0
    try:
        fails_s, last_s, lock_s = raw.decode().split(":") if isinstance(raw, bytes) else str(raw).split(":")
        return int(fails_s), int(last_s), int(lock_s)
    except (ValueError, AttributeError):
        return 0, 0, 0


def _ttl_for(locked_until: int) -> int:
    """Seconds of Redis TTL that keeps the entry only as long as it matters.

    The entry has to outlive the lockout by a whole FAIL_WINDOW: an attacker who
    comes straight back the moment a lock lifts must find the count still there
    to escalate against, and only a genuinely quiet window may forget it.
    """
    return max(0, locked_until - _now()) + FAIL_WINDOW


def _read(username: str) -> tuple[int, int, int]:
    try:
        return _decode(redis_client.get(_KEY.format(username=username)))
    except Exception as ex:  # Redis being down must not break login
        logger.warning(f"Login throttle read failed for '{username}': {ex}")
        return 0, 0, 0


def _write(username: str, fails: int, last_fail: int, locked_until: int) -> None:
    try:
        redis_client.set(
            _KEY.format(username=username),
            _encode(fails, last_fail, locked_until),
            ex=_ttl_for(locked_until),
        )
    except Exception as ex:  # Redis being down must not break login
        logger.warning(f"Login throttle write failed for '{username}': {ex}")


def is_locked(username: str) -> bool:
    """Tell whether this username is currently locked out."""
    _, _, locked_until = _read(username)
    return locked_until > _now()


def check_lock(username: str) -> bool:
    """Pass-through gate returning True when the attempt may proceed."""
    if is_locked(username):
        logger.warning(f"Login attempt on locked account: {username}")
        return False
    return True


def register_failure(username: str) -> None:
    """Count one failed attempt, locking the account once past the threshold."""
    fails, last_fail, locked_until = _read(username)
    now = _now()
    # The quiet period is measured from whichever came later: the last failure,
    # or the end of a lockout. Measuring it from the last failure alone would
    # make escalation unreachable - the lockout runs at least as long as the
    # window, so the count would always look stale by the time an attacker is
    # let back in, and every burst would restart at one.
    if fails and now - max(last_fail, locked_until) > FAIL_WINDOW:
        fails = 0  # a genuinely quiet window; start a fresh count
    fails += 1
    locked_until = 0
    if fails >= FAIL_THRESHOLD:
        # Cap the exponent as well as the result - a long-running attack would
        # otherwise raise 2 to an arbitrarily large power just to clamp it away.
        overkill = min(fails - FAIL_THRESHOLD, 32)
        lockout = min(LOCKOUT_SECONDS * (LOCKOUT_MULTIPLIER**overkill), LOCKOUT_MAX_SECONDS)
        locked_until = now + lockout
        logger.warning(f"Account locked for {lockout}s after {fails} failed login attempts: {username}")
    _write(username, fails, now, locked_until)


def register_success(username: str) -> None:
    """Forget the failure history of a username that has just logged in."""
    try:
        redis_client.delete(_KEY.format(username=username))
    except Exception as ex:  # Redis being down must not break login
        logger.warning(f"Login throttle reset failed for '{username}': {ex}")
