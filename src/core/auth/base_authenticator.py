"""BaseAuthenticator class provides methods for handling authentication processes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.user import User

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import timedelta
from http import HTTPStatus

from config import Config
from flask import current_app
from flask_jwt_extended import create_access_token
from managers import log_manager
from model.security_settings import SecuritySettings
from model.token_blacklist import TokenBlacklist

# The claim tying a session to the account's credentials as they were when it was issued.
CREDENTIAL_CLAIM = "cred"
# When the sign-in behind a token happened (epoch seconds); a refresh carries it over.
AUTH_TIME_CLAIM = "auth_time"
# A refresh that would leave less than this before the session's maximum length is refused. The
# GUI refreshes five minutes before a token runs out; with a token capped to the last minutes of
# the session, it would otherwise refresh every few seconds until the end.
MIN_SESSION_LEFT_SECONDS = 600
SESSION_EXPIRED = (
    {"error": "Your session has reached its maximum length; sign in again", "code": "SESSION_EXPIRED"},
    HTTPStatus.UNAUTHORIZED,
)


def session_seconds_left(auth_time: int, now: int) -> int | None:
    """Seconds until a session started at ``auth_time`` reaches its maximum length; None: no limit."""
    hours = SecuritySettings.get_session_max_hours()
    if not hours:
        return None
    return auth_time + hours * 3600 - now


def _default_token_seconds() -> int:
    """The configured access token lifetime, in seconds."""
    configured = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 900)
    return int(configured.total_seconds()) if isinstance(configured, timedelta) else int(configured)


def session_credential(user: User) -> str:
    """A fingerprint of what a session was opened with: the account and its password.

    It goes into every token, and a token whose fingerprint no longer matches is refused. So a
    password change - or a username change, or the password being removed - ends every other
    session of the account at once, instead of leaving a stolen token valid until it expires
    (and, refreshed, forever). It is an HMAC under the JWT key: a token reveals nothing about the
    password hash, and nobody without the key can compute it.

    Args:
        user (User): The account.

    Returns:
        str: 32 hex characters.
    """
    message = f"{user.id}:{user.username}:{user.password or ''}".encode()
    return hmac.new(str(Config.JWT_SECRET_KEY).encode(), message, hashlib.sha256).hexdigest()[:32]


class ProviderConfigurationError(Exception):
    """The identity provider rejected *our* configuration, not the subject's credentials.

    Raised when a login fails for a reason only an administrator can fix - a
    client secret the IdP refuses, or one stored under an encryption key we no
    longer hold. It is kept apart from an ordinary authentication failure so the
    login page can say so instead of blaming the person trying to log in; the
    detail stays in the audit log and never reaches the browser.
    """


@dataclass
class ExternalIdentity:
    """Identity of a subject authenticated by an external provider.

    Attributes:
        username (str): Username reported by the provider.
        external_id (str): Stable subject identifier (OIDC ``sub`` / LDAP DN).
        name (str): Display name reported by the provider.
        email (str): E-mail address reported by the provider.
    """

    username: str
    external_id: str | None = None
    name: str | None = None
    email: str | None = None


class BaseAuthenticator:
    """BaseAuthenticator class provides methods for handling authentication processes."""

    @staticmethod
    def logout(jwt_id: str) -> None:
        """Log out a user by adding their token to the blacklist.

        Args:
            jwt_id (str): The token to be blacklisted.
        """
        TokenBlacklist.add(jwt_id)

    @staticmethod
    def generate_error() -> tuple[dict, HTTPStatus]:
        """Generate an error response for authentication failure.

        Returns:
            tuple: A dictionary containing the error message and the HTTP status code 401.
        """
        return {"error": "Authentication failed"}, HTTPStatus.UNAUTHORIZED

    @staticmethod
    def generate_error_code(message: str, code: str, **extra: str) -> tuple[dict, HTTPStatus]:
        """Generate a login rejection response carrying a machine-readable code.

        Args:
            message (str): Human-readable error message.
            code (str): Machine-readable code for the GUI (e.g. PENDING_APPROVAL).
            **extra: Additional payload entries (e.g. mfa_token).

        Returns:
            tuple: The error payload and HTTP status 403.
        """
        return {"error": message, "code": code, **extra}, HTTPStatus.FORBIDDEN

    @staticmethod
    def check_user_status(user: User) -> tuple[dict, HTTPStatus] | None:
        """Refuse login of users that are not active.

        Args:
            user (User): The authenticated user.

        Returns:
            tuple | None: An error response for pending/disabled users, None when active.
        """
        if user.status == "pending":
            log_manager.store_auth_warning_activity(f"Login of user pending approval blocked: {user.username}")
            return BaseAuthenticator.generate_error_code("Your account is awaiting administrator approval", "PENDING_APPROVAL")
        if user.status != "active":
            log_manager.store_auth_warning_activity(f"Login of disabled user blocked: {user.username}")
            return BaseAuthenticator.generate_error_code("Your account is disabled", "ACCOUNT_DISABLED")
        return None

    @staticmethod
    def generate_jwt(user: User, *, record_login: bool = True, auth_time: int | None = None) -> tuple[dict, HTTPStatus]:
        """Generate a JSON Web Token (JWT) for a given user.

        A session lasts at most ``security_settings.session_max_hours`` from its sign-in: the
        token records the sign-in (``auth_time``), a refresh carries it over, the token expires
        no later than the session does, and a refresh close to that end is refused
        (SESSION_EXPIRED). The GUI used to keep a session alive for as long as a tab was open.

        Args:
            user (User): The user for whom the JWT is to be generated.
            record_login (bool): Whether this counts as a sign-in. Refreshing a token
                converges here too, and stamping it would turn the account's last login
                into the time of the GUI's last background refresh.
            auth_time (int | None): When the session's sign-in happened (epoch seconds), for a
                refresh; None: now, a new sign-in.

        Returns:
            tuple: A tuple containing a dictionary with the access token and an HTTP status code.
                   If the user is not active, or the session has run its course, an error response.
        """
        status_error = BaseAuthenticator.check_user_status(user)
        if status_error:
            return status_error
        now = int(time.time())
        auth_time = now if auth_time is None else int(auth_time)
        seconds_left = session_seconds_left(auth_time, now)
        if seconds_left is not None and seconds_left < MIN_SESSION_LEFT_SECONDS:
            return SESSION_EXPIRED
        expires = None if seconds_left is None else timedelta(seconds=min(seconds_left, _default_token_seconds()))
        log_manager.store_user_activity(user, "LOGIN", "Successful")
        if record_login:
            user.touch_login()
        access_token = create_access_token(
            identity=user.username,
            additional_claims={
                "auth_generation": SecuritySettings.get_auth_generation(),
                CREDENTIAL_CLAIM: session_credential(user),
                AUTH_TIME_CLAIM: auth_time,
                "user_claims": {
                    "id": user.id,
                    "name": user.name,
                    "organization_name": user.get_current_organization_name(),
                    "permissions": user.get_permissions(),
                },
            },
            expires_delta=expires,
        )

        return {"access_token": access_token}, HTTPStatus.OK
