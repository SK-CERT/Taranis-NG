"""TOTP (time-based one-time password) enrollment and verification."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pyotp
from managers import crypto_manager
from managers.cache_manager import redis_client
from managers.db_manager import db

if TYPE_CHECKING:
    from model.user import User

TOTP_ISSUER = "Taranis NG"
TOTP_STEP = 30
ENROLLMENT_TTL = 600


def _enrollment_key(username: str) -> str:
    """Build the Redis key holding a pending enrollment secret."""
    return f"totp_enroll:{username}"


def _matching_step(secret: str, code: str) -> int | None:
    """Return the time step the code is valid for (+-1 step window), or None.

    Args:
        secret (str): The base32 TOTP secret.
        code (str): The submitted code.
    """
    totp = pyotp.TOTP(secret)
    now = int(time.time() // TOTP_STEP)
    for step in (now, now - 1, now + 1):
        if pyotp.utils.strings_equal(totp.at(step * TOTP_STEP), str(code).strip()):
            return step
    return None


def begin_enrollment(username: str) -> str:
    """Start TOTP enrollment: generate a secret and return the otpauth URI for the QR code.

    The secret is held in Redis until confirmed with a valid code.

    Args:
        username (str): The enrolling user's username.

    Returns:
        str: The otpauth:// provisioning URI.
    """
    secret = pyotp.random_base32()
    redis_client.set(_enrollment_key(username), secret, ex=ENROLLMENT_TTL)
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=TOTP_ISSUER)


def confirm_enrollment(user: User, code: str) -> bool:
    """Confirm a pending enrollment with a valid code and persist the encrypted secret.

    Args:
        user (User): The enrolling user.
        code (str): The TOTP code from the authenticator app.

    Returns:
        bool: True when enrollment succeeded.
    """
    secret = redis_client.get(_enrollment_key(user.username))
    if not secret:
        return False
    secret = secret.decode() if isinstance(secret, bytes) else secret
    step = _matching_step(secret, code)
    if step is None:
        return False
    user.totp_secret = crypto_manager.encrypt(secret)
    user.totp_last_used_step = step
    db.session.commit()
    redis_client.delete(_enrollment_key(user.username))
    return True


def verify_code(user: User, code: str) -> bool:
    """Verify a login TOTP code with a replay guard.

    A code is accepted at most once: the matched time step must be newer than
    the last accepted one.

    Args:
        user (User): The user logging in.
        code (str): The submitted code.

    Returns:
        bool: True when the code is valid and unused.
    """
    if not user.totp_secret or not code:
        return False
    secret = crypto_manager.decrypt(user.totp_secret)
    if not secret:
        return False
    step = _matching_step(secret, code)
    if step is None:
        return False
    if user.totp_last_used_step is not None and step <= user.totp_last_used_step:
        return False
    user.totp_last_used_step = step
    db.session.commit()
    return True


def disable(user: User, code: str) -> bool:
    """Disable TOTP for a user after verifying a current code.

    Args:
        user (User): The user disabling TOTP.
        code (str): A currently valid TOTP code.

    Returns:
        bool: True when TOTP was disabled.
    """
    if not verify_code(user, code):
        return False
    user.totp_secret = None
    user.totp_last_used_step = None
    db.session.commit()
    return True
