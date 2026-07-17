"""This module contains the authentication manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import Flask
    from shared.time_manager import SchedulerManager

import os
import random
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from http import HTTPStatus

import jwt
from auth.base_authenticator import BaseAuthenticator
from auth.keycloak_authenticator import KeycloakAuthenticator
from auth.ldap_authenticator import LDAPAuthenticator
from auth.oauth2_authenticator import OAuth2Authenticator
from auth.openid_authenticator import OpenIDAuthenticator
from auth.password_authenticator import PasswordAuthenticator
from auth.saml_authenticator import SamlAuthenticator
from config import Config
from flask import request
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from managers import log_manager, totp_manager, webauthn_manager
from model.apikey import ApiKey
from model.auth_provider import FORM_KINDS, OAUTH_KINDS, AuthProvider, UserAuthIdentity
from model.bots_node import BotsNode
from model.collectors_node import CollectorsNode
from model.news_item import NewsItem
from model.osint_source import OSINTSourceGroup
from model.permission import Permission
from model.product_type import ProductType
from model.publishers_node import PublishersNode
from model.remote import RemoteAccess
from model.report_item import ReportItem
from model.security_settings import SecuritySettings
from model.token_blacklist import TokenBlacklist
from model.user import User
from shared.common import TZ

current_authenticator = None

SCOPED_TOKEN_MINUTES = 5
OAUTH_STATE_MINUTES = 10


def cleanup_token_blacklist(app: Flask) -> None:
    """Clean up the token blacklist by deleting tokens older than one day.

    Args:
        app: The Flask application object.
    """
    with app.app_context():
        TokenBlacklist.delete_older(datetime.now(TZ) - timedelta(days=1))


def initialize(app: Flask) -> None:
    """Initialize the authentication manager.

    This function sets up the authentication manager based on the configured authenticator.

    Args:
        app: The Flask application object.
    """
    global current_authenticator  # noqa: PLW0603

    JWTManager(app)

    # DEPRECATED: env-based keycloak/openid stay supported for existing deployments.
    # All other values are handled by the auth providers configured in the database
    # (a "Local accounts" provider - and an LDAP provider when previously configured
    # via env - are seeded by migration).
    which = os.getenv("TARANIS_NG_AUTHENTICATOR")
    if which is not None:
        which = which.lower()
    if which == "openid":
        current_authenticator = OpenIDAuthenticator()
    elif which == "keycloak":
        current_authenticator = KeycloakAuthenticator()
    else:
        current_authenticator = None

    if current_authenticator:
        current_authenticator.initialize(app)


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Schedule token blacklist cleanup.

    Args:
        manager: time manager class.
        app: The Flask application instance.
    """
    manager.schedule_job_every_day("00:00", cleanup_token_blacklist, "Token blacklist cleanup", app)


def get_required_credentials() -> list:
    """Get the required credentials.

    This function returns the required credentials for the current authenticator.

    Returns:
        The required credentials for the current authenticator.
    """
    if current_authenticator:
        return current_authenticator.get_required_credentials()
    return ["username", "password", "provider_id"]


def authenticate(credentials: dict) -> tuple[dict, HTTPStatus]:
    """Authenticate the user using the provided credentials.

    Args:
        credentials: The user's credentials.

    Returns:
        The result of the authentication process.
    """
    if current_authenticator:
        return current_authenticator.authenticate(credentials)
    return authenticate_with_provider((credentials or {}).get("provider_id"), credentials)


def refresh(user: User) -> tuple[dict, HTTPStatus]:
    """Refresh the authentication token for the given user.

    Args:
        user: The user object for which the authentication token needs to be refreshed.

    Returns:
        The refreshed authentication token.
    """
    if current_authenticator:
        return current_authenticator.refresh(user)
    return BaseAuthenticator.generate_jwt(user)


def logout(jwt_id: str) -> None:
    """Logout the user.

    This function logs out the user by calling the `logout` method of the current authenticator.

    Args:
        jwt_id (str): The authentication token of the user.

    Returns:
        None: This function does not return any value.
    """
    if jwt_id is not None:
        if current_authenticator:
            current_authenticator.logout(jwt_id)
        else:
            BaseAuthenticator.logout(jwt_id)


def get_login_methods() -> dict:
    """List the enabled login methods for the (anonymous) login page.

    Returns:
        dict: Items with id, name, kind, form (credentials form applies) and
              login_url (redirect-based kinds only), plus passkey_enabled -
              passkeys are a site-wide capability, not a provider. No
              configuration or secrets are exposed.
    """
    items = []
    for provider in AuthProvider.get_enabled():
        if provider.kind in OAUTH_KINDS:
            login_url = f"/api/v1/auth/oauth/{provider.slug}/login"
        elif provider.kind == "saml":
            login_url = f"/api/v1/auth/saml/{provider.slug}/login"
        else:
            login_url = None
        items.append(
            {
                "id": provider.id,
                "name": provider.name,
                "kind": provider.kind,
                "form": provider.kind in FORM_KINDS,
                "login_url": login_url,
            },
        )
    return {"items": items, "passkey_enabled": webauthn_manager.passkeys_enabled()}


def make_scoped_token(username: str, scope: str, expires_minutes: int = SCOPED_TOKEN_MINUTES, **claims: str) -> str:
    """Mint a short-lived single-purpose token (MFA step, TOTP enrollment, OAuth state).

    These tokens carry a ``scope`` claim and no flask-jwt ``type`` claim, so they
    can never be used as API access tokens.

    Args:
        username (str): Subject username.
        scope (str): Purpose of the token (e.g. "mfa", "mfa_enroll", "oauth_state").
        expires_minutes (int): Token lifetime.
        **claims: Additional claims to embed.

    Returns:
        str: The encoded token.
    """
    payload = {
        "sub": username,
        "scope": scope,
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(TZ) + timedelta(minutes=expires_minutes),
        **claims,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


def decode_scoped_token(token: str, scope: str) -> dict | None:
    """Decode and validate a single-purpose token.

    Args:
        token (str): The encoded token.
        scope (str): The required scope.

    Returns:
        dict: The token payload, or None when invalid/expired/wrong scope.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except Exception as ex:
        log_manager.store_auth_error_activity(f"Invalid scoped token: {ex!s}")
        return None
    if payload.get("scope") != scope:
        log_manager.store_auth_error_activity(f"Scoped token used with wrong scope: expected {scope}")
        return None
    return payload


def mfa_required(provider: AuthProvider, user: User) -> bool:
    """Tell whether this user must hold a second factor.

    Four levels can demand it and they are OR-ed - the site, the user's
    organization, the login method, and the user themselves. Enforcement is the
    strictest of them: a level that requires MFA cannot be relaxed by another
    that does not.

    Args:
        provider (AuthProvider): The provider used for the first factor.
        user (User): The authenticated user.

    Returns:
        bool: Whether a second factor is mandatory for this user.
    """
    return bool(
        SecuritySettings.mfa_required()
        or any(organization.require_mfa for organization in user.organizations)
        or provider.require_mfa
        or user.require_mfa,
    )


def _mfa_gate(provider: AuthProvider, user: User) -> tuple[dict, HTTPStatus] | None:
    """Decide whether a login must complete a second factor.

    Triggered when any level requires MFA (see :func:`mfa_required`) or the user
    has a usable factor enrolled - one they enrolled themselves is always asked
    for, even where nothing requires it.

    A passkey only counts when passkeys are accepted as a second factor
    site-wide; with that switch off, TOTP is the only way to satisfy the step,
    and a user who owns nothing but passkeys is walked through TOTP enrollment.

    Args:
        provider (AuthProvider): The provider used for the first factor.
        user (User): The authenticated user.

    Returns:
        tuple | None: The MFA challenge response, or None when no MFA applies.
    """
    totp_enrolled = bool(user.totp_secret)
    has_passkeys = len(user.webauthn_credentials) > 0 and webauthn_manager.passkey_second_factor_enabled()
    if not (mfa_required(provider, user) or totp_enrolled or has_passkeys):
        return None
    if totp_enrolled or has_passkeys:
        methods = [method for method, enrolled in (("totp", totp_enrolled), ("passkey", has_passkeys)) if enrolled]
        return BaseAuthenticator.generate_error_code(
            "Additional authentication required",
            "MFA_REQUIRED",
            methods=methods,
            mfa_token=make_scoped_token(user.username, "mfa"),
        )
    # Nothing enrolled yet: offer every factor this installation accepts, so a user
    # forced to set one up is not pushed into an authenticator app when a passkey
    # would do.
    enrollable = ["totp", "passkey"] if webauthn_manager.passkey_second_factor_enabled() else ["totp"]
    return BaseAuthenticator.generate_error_code(
        "Two-factor authentication enrollment is required",
        "MFA_ENROLLMENT_REQUIRED",
        methods=enrollable,
        enroll_token=make_scoped_token(user.username, "mfa_enroll"),
    )


def _finalize_login(provider: AuthProvider, user: User) -> tuple[dict, HTTPStatus]:
    """Run the status gate, then the MFA gate, then issue the JWT.

    The MFA gate applies to every provider kind. A factor the user enrolled is
    theirs, not the provider's: skipping it for redirect logins would leave the
    external path weaker than the local one, and an attacker holding the account
    at the identity provider could then bypass the second factor by choosing it.

    Args:
        provider (AuthProvider): The provider the user authenticated against.
        user (User): The authenticated user.

    Returns:
        tuple: The login response.
    """
    status_error = BaseAuthenticator.check_user_status(user)
    if status_error:
        return status_error
    mfa_challenge = _mfa_gate(provider, user)
    if mfa_challenge:
        return mfa_challenge
    return BaseAuthenticator.generate_jwt(user)


def provision_and_issue_jwt(provider: AuthProvider, identity: object) -> tuple[dict, HTTPStatus]:
    """Resolve an externally authenticated identity to a local user and issue the JWT.

    Matching order: existing identity link (by external id, then external
    username) -> otherwise provisioning per the provider's mode: "manual"
    rejects unlinked identities, "approval"/"automatic" auto-create the user
    (pending/active) when the optional domain filter passes and the username
    is free.

    Args:
        provider (AuthProvider): The provider the subject authenticated against.
        identity (ExternalIdentity): The externally authenticated identity.

    Returns:
        tuple: The login response.
    """
    identity_row = UserAuthIdentity.find_by_external(provider.id, identity.external_id, identity.username)
    if identity_row:
        user = identity_row.user
        identity_row.touch_login()
        return _finalize_login(provider, user)

    if provider.provisioning_mode == "manual":
        log_manager.store_auth_error_activity(
            f"Unlinked identity '{identity.username}' rejected by provider '{provider.name}' (linked users only)",
        )
        return BaseAuthenticator.generate_error_code(
            "This identity is not linked to any account. Contact your administrator.",
            "ACCOUNT_NOT_LINKED",
        )

    allowed_domains = provider.get_allowed_domains()
    if allowed_domains:
        domain = identity.email.rsplit("@", 1)[1].lower() if identity.email and "@" in identity.email else None
        if not domain or domain not in allowed_domains:
            log_manager.store_auth_error_activity(f"Identity '{identity.username}' rejected by provider '{provider.name}' domain filter")
            return BaseAuthenticator.generate_error_code(
                "Your e-mail domain is not allowed to sign up. Contact your administrator.",
                "DOMAIN_NOT_ALLOWED",
            )

    if User.find(identity.username):
        log_manager.store_auth_error_activity(
            f"Provisioning of '{identity.username}' via provider '{provider.name}' collides with an existing username",
        )
        return BaseAuthenticator.generate_error_code(
            "An account with this username already exists. Ask your administrator to link this identity to it.",
            "USERNAME_COLLISION",
        )

    user = User.provision_external(provider, identity.username, identity.name, identity.email, identity.external_id)
    log_manager.store_user_activity(user, "PROVISION", f"Auto-created via auth provider '{provider.name}' with status '{user.status}'")
    return _finalize_login(provider, user)


def authenticate_with_provider(provider_id: object, credentials: dict) -> tuple[dict, HTTPStatus]:
    """Authenticate form credentials against one (or the fallback chain of) providers.

    Without a provider_id (legacy clients), local providers are tried first,
    then LDAP providers, in id order.

    Args:
        provider_id: The chosen provider ID (may be None or a string).
        credentials (dict): username/password credentials.

    Returns:
        tuple: The login response.
    """
    credentials = credentials or {}
    username = credentials.get("username")
    password = credentials.get("password")
    if not username or not password:
        return BaseAuthenticator.generate_error()

    if provider_id:
        try:
            provider = AuthProvider.find(int(provider_id))
        except (TypeError, ValueError):
            provider = None
        providers = [provider] if provider and provider.enabled and provider.kind in FORM_KINDS else []
    else:
        providers = AuthProvider.get_enabled_by_kind(("local",)) + AuthProvider.get_enabled_by_kind(("ldap",))

    for provider in providers:
        if provider.kind == "local":
            user = PasswordAuthenticator.verify(credentials)
            if user:
                return _finalize_login(provider, user)
        elif provider.kind == "ldap":
            identity = LDAPAuthenticator(provider).verify(credentials)
            if identity:
                return provision_and_issue_jwt(provider, identity)

    data = request.get_json(silent=True) or {}
    if data.get("password"):
        data["password"] = log_manager.sensitive_value(data["password"])
    log_manager.store_auth_error_activity(f"Authentication failed for user: {username}", request_data=data)
    time.sleep(random.uniform(1, 3))  # noqa: S311 - timing jitter, not cryptographic
    return BaseAuthenticator.generate_error()


def complete_mfa_totp(mfa_token: str, code: str) -> tuple[dict, HTTPStatus]:
    """Complete a login by verifying the TOTP code of the MFA step.

    Args:
        mfa_token (str): The scoped token from the MFA_REQUIRED response.
        code (str): The submitted TOTP code.

    Returns:
        tuple: The login response.
    """
    payload = decode_scoped_token(mfa_token, "mfa")
    user = User.find(payload["sub"]) if payload else None
    if not user:
        return BaseAuthenticator.generate_error()
    if not totp_manager.verify_code(user, code):
        log_manager.store_auth_error_activity(f"Invalid TOTP code for user: {user.username}")
        time.sleep(random.uniform(1, 3))  # noqa: S311 - timing jitter, not cryptographic
        return BaseAuthenticator.generate_error_code("Invalid authentication code", "TOTP_INVALID")
    return BaseAuthenticator.generate_jwt(user)


def complete_totp_enrollment(enroll_token: str, code: str | None) -> tuple[dict, HTTPStatus]:
    """Handle forced TOTP enrollment during login.

    Without a code, starts the enrollment and returns the otpauth URI for the
    QR code; with a code, confirms the enrollment and issues the JWT.

    Args:
        enroll_token (str): The scoped token from the MFA_ENROLLMENT_REQUIRED response.
        code (str): The confirmation TOTP code (None to begin enrollment).

    Returns:
        tuple: The enrollment payload or the login response.
    """
    payload = decode_scoped_token(enroll_token, "mfa_enroll")
    user = User.find(payload["sub"]) if payload else None
    if not user:
        return BaseAuthenticator.generate_error()
    if not code:
        return {"otpauth_uri": totp_manager.begin_enrollment(user.username)}, HTTPStatus.OK
    if not totp_manager.confirm_enrollment(user, code):
        return BaseAuthenticator.generate_error_code("Invalid authentication code", "TOTP_INVALID")
    return BaseAuthenticator.generate_jwt(user)


def complete_passkey_enrollment(enroll_token: str, challenge_id: str | None, credential: dict | None, name: str) -> tuple[dict, HTTPStatus]:
    """Handle forced enrollment during login when the user picks a passkey over TOTP.

    Without a credential, starts the registration ceremony and returns the WebAuthn
    creation options; with one, stores the passkey and issues the JWT - registering
    it *is* the second factor, so no further step is needed.

    The user is mid-login and holds no access token, which is why this is driven by
    the same scoped enrollment token as the TOTP path rather than by a session.

    Args:
        enroll_token (str): The scoped token from the MFA_ENROLLMENT_REQUIRED response.
        challenge_id (str): Handle from the begin step (None to begin).
        credential (dict): The authenticator's response (None to begin).
        name (str): User-facing label for the passkey.

    Returns:
        tuple: The creation options or the login response.
    """
    if not webauthn_manager.passkey_second_factor_enabled():
        return BaseAuthenticator.generate_error_code("Passkeys are not accepted as a second factor", "PASSKEY_NOT_ALLOWED")

    payload = decode_scoped_token(enroll_token, "mfa_enroll")
    user = User.find(payload["sub"]) if payload else None
    if not user:
        return BaseAuthenticator.generate_error()

    try:
        if not credential:
            return webauthn_manager.begin_registration(user), HTTPStatus.OK
        # the WebAuthn library raises its own exception types on a bad attestation
        webauthn_manager.finish_registration(user, challenge_id or "", credential, name or "Passkey")
    except Exception as ex:
        log_manager.store_auth_error_activity(f"Passkey enrollment failed for user: {user.username}", ex)
        return BaseAuthenticator.generate_error_code(f"Passkey registration failed: {ex}", "PASSKEY_INVALID")
    return BaseAuthenticator.generate_jwt(user)


def get_user_from_scoped_token(token: str, scope: str) -> User | None:
    """Resolve the user of a scoped token (for MFA passkey ceremonies).

    Args:
        token (str): The scoped token.
        scope (str): The required scope.

    Returns:
        User: The subject user, or None.
    """
    payload = decode_scoped_token(token, scope)
    return User.find(payload["sub"]) if payload else None


def begin_passkey_authentication(mfa_token: str | None) -> tuple[dict, HTTPStatus]:
    """Start a passkey ceremony for passwordless login or the MFA step.

    Args:
        mfa_token (str): Scoped MFA token (second-factor mode); None for
            passwordless (discoverable credential) login.

    Returns:
        tuple: WebAuthn request options and challenge handle, or an error.
    """
    user = None
    if mfa_token:
        user = get_user_from_scoped_token(mfa_token, "mfa")
        if not user:
            return BaseAuthenticator.generate_error()
    try:
        return webauthn_manager.begin_authentication(user), HTTPStatus.OK
    except ValueError as ex:
        return {"error": str(ex)}, HTTPStatus.BAD_REQUEST


def complete_passkey_login(challenge_id: str, credential: dict) -> tuple[dict, HTTPStatus]:
    """Complete a passwordless passkey login.

    Args:
        challenge_id (str): Handle from begin_passkey_authentication.
        credential (dict): The authenticator's assertion.

    Returns:
        tuple: The login response.
    """
    try:
        user = webauthn_manager.finish_authentication(challenge_id, credential)
    except ValueError as ex:
        return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
    if not user:
        return BaseAuthenticator.generate_error()
    return BaseAuthenticator.generate_jwt(user)


def complete_mfa_passkey(mfa_token: str, challenge_id: str, credential: dict) -> tuple[dict, HTTPStatus]:
    """Complete a login by verifying a passkey assertion as the second factor.

    Args:
        mfa_token (str): The scoped token from the MFA_REQUIRED response.
        challenge_id (str): Handle from begin_passkey_authentication.
        credential (dict): The authenticator's assertion.

    Returns:
        tuple: The login response.
    """
    payload = decode_scoped_token(mfa_token, "mfa")
    if not payload:
        return BaseAuthenticator.generate_error()
    try:
        owner = webauthn_manager.finish_authentication(challenge_id, credential)
    except ValueError as ex:
        return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
    if not owner or owner.username != payload["sub"]:
        return BaseAuthenticator.generate_error()
    return BaseAuthenticator.generate_jwt(owner)


def get_oauth_authenticator(slug: str) -> OAuth2Authenticator | None:
    """Build the OAuth2/OIDC authenticator for an enabled oauth-kind provider.

    Args:
        slug (str): The provider slug (from the auth URL).

    Returns:
        OAuth2Authenticator: The authenticator, or None for unknown/disabled providers.
    """
    provider = AuthProvider.find_by_slug(slug)
    if not provider or not provider.enabled or provider.kind not in OAUTH_KINDS:
        return None
    return OAuth2Authenticator(provider)


def get_saml_authenticator(slug: str) -> SamlAuthenticator | None:
    """Build the SAML authenticator for an enabled saml-kind provider.

    Args:
        slug (str): The provider slug (from the auth URL).

    Returns:
        SamlAuthenticator: The authenticator, or None for unknown/disabled providers.
    """
    provider = AuthProvider.find_by_slug(slug)
    if not provider or not provider.enabled or provider.kind != "saml":
        return None
    return SamlAuthenticator(provider)


class ACLCheck(Enum):
    """Enumeration for ACL checks.

    This enumeration defines the different types of access control checks that can be performed.

    Attributes:
        OSINT_SOURCE_GROUP_ACCESS: Access check for OSINT source group.
        NEWS_ITEM_ACCESS: Access check for news item.
        NEWS_ITEM_MODIFY: Modify check for news item.
        REPORT_ITEM_ACCESS: Access check for report item.
        REPORT_ITEM_MODIFY: Modify check for report item.
        PRODUCT_TYPE_ACCESS: Access check for product type.
        PRODUCT_TYPE_MODIFY: Modify check for product type.
    """

    OSINT_SOURCE_GROUP_ACCESS = auto()
    NEWS_ITEM_ACCESS = auto()
    NEWS_ITEM_MODIFY = auto()
    REPORT_ITEM_ACCESS = auto()
    REPORT_ITEM_MODIFY = auto()
    PRODUCT_TYPE_ACCESS = auto()
    PRODUCT_TYPE_MODIFY = auto()


def check_acl(item_id: str, acl_check: str, user: User) -> bool:
    """Check the access control list (ACL) for the given item.

    This function determines whether the user has the necessary permissions to perform the specified ACL check on the item.

    Args:
        item_id (str): The ID of the item.
        acl_check (str): The type of ACL check to perform.
        user (str): The user performing the ACL check.

    Returns:
        bool: True if the user is allowed to perform the ACL check, False otherwise.
    """
    check_see = "SEE" in str(acl_check)
    check_access = "ACCESS" in str(acl_check)
    check_modify = "MODIFY" in str(acl_check)
    allowed = False
    item_type = "UNKNOWN"

    if acl_check == ACLCheck.OSINT_SOURCE_GROUP_ACCESS:
        item_type = "OSINT Source Group"
        allowed = OSINTSourceGroup.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.NEWS_ITEM_ACCESS, ACLCheck.NEWS_ITEM_MODIFY]:
        item_type = "News Item"
        allowed = NewsItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.REPORT_ITEM_ACCESS, ACLCheck.REPORT_ITEM_MODIFY]:
        item_type = "Report Item"
        allowed = ReportItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.PRODUCT_TYPE_ACCESS, ACLCheck.PRODUCT_TYPE_MODIFY]:
        item_type = "Product Type"
        allowed = ProductType.allowed_product_with_acl(item_id, user, check_see, check_access, check_modify)

    if not allowed:
        if check_access:
            log_manager.store_user_auth_error_activity(user, f"Unauthorized access attempt to {item_type}: {item_id}")
        else:
            log_manager.store_user_auth_error_activity(user, f"Unauthorized modification attempt to {item_type}: {item_id}")

    return allowed


def no_auth(fn):  # noqa: ANN001, ANN201
    """Allow access to the decorated function without authentication.

    Args:
        fn (function): The function to be decorated.

    Returns:
        function: The decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        """Wrapper that permits unauthenticated access and logs the access.

        Args:
            *args: Positional arguments forwarded to the wrapped function.
            **kwargs: Keyword arguments forwarded to the wrapped function.

        Returns:
            Any: The result returned by the wrapped function.
        """
        log_manager.store_activity("API_ACCESS", None)
        return fn(*args, **kwargs)

    return wrapper


def get_id_name_by_acl(acl: ACLCheck) -> str:
    """Get the ID name based on the ACL.

    This function takes an ACL object and returns the corresponding ID name based on the ACL's name.

    Args:
        acl: The ACL object.

    Returns:
        The ID name corresponding to the ACL's name.
    """
    if "NEWS_ITEM" in acl.name:
        return "item_id"
    if "REPORT_ITEM" in acl.name:
        return "report_item_id"
    if "OSINT_SOURCE_GROUP" in acl.name:
        return "group_id"
    if "PRODUCT" in acl.name:
        return "product_id"
    return None


def _find_active_user(identity: str) -> User | None:
    """Find a user by username and require an active account.

    Central status enforcement: pending/disabled users are rejected here, so
    disabling a user also invalidates their existing sessions.

    Args:
        identity (str): The username from the token.

    Returns:
        User: The active user, or None.
    """
    user = User.find(identity)
    if not user:
        log_manager.store_auth_error_activity(f"Unknown identity: {identity}")
        return None
    if user.status != "active":
        # Expected policy rejection: a previously-issued token for an account
        # that was later disabled (or is still pending approval) being refused.
        # This fires on every authenticated call with the stale token, so it is
        # logged as a warning rather than an error.
        log_manager.store_auth_warning_activity(f"Access of non-active user blocked: {identity}")
        return None
    return user


def get_user_from_api_key() -> User:
    """Try to authenticate the user by API key.

    Returns:
        user (User object or None): The authenticated user object, or None if authentication fails.
    """
    try:
        if "Authorization" not in request.headers or not request.headers["Authorization"].__contains__("ApiKey "):
            return None
        api_key = get_api_key()
        apikey = ApiKey.find_by_key(api_key)
        if not apikey:
            return None
        user = User.find_by_id(apikey.user_id)
        if user and user.status != "active":
            # Expected policy rejection: an API key for an account that was
            # disabled (or is still pending approval) being refused. See the
            # matching note in _find_active_user for why this is a warning.
            log_manager.store_auth_warning_activity(f"API key access of non-active user blocked: {user.username}")
            return None
        return user

    except Exception as ex:
        log_manager.store_auth_error_activity("API key check presence error", ex)
        return None


def get_perm_from_user(user: User) -> set:
    """Get user permissions.

    Args:
        user: User object representing the user.

    Returns:
        Set of user's permissions (as permission IDs) or None if an error occurs.
    """
    try:
        all_users_perms = set()
        for perm in user.permissions:
            all_users_perms.add(perm.id)
        for role in user.roles:
            role_perms = {perm.id for perm in role.permissions}
            all_users_perms = all_users_perms.union(role_perms)
        return all_users_perms
    except Exception as ex:
        log_manager.store_auth_error_activity("Get permission from user error", ex)
        return None


def get_user_from_jwt_token() -> User | None:
    """Try to authenticate the user by API key.

    This function verifies the JWT token in the request and retrieves the user object associated with the token's identity.

    Returns:
        user (User object or None): The authenticated user object if successful, otherwise None.
    """
    try:
        verify_jwt_in_request()
    except JWTExtendedException as ex:
        log_manager.store_auth_error_activity("Missing JWT", ex)
        return None

    # does it encode an identity?
    identity = get_jwt_identity()
    if not identity:
        log_manager.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
        return None

    return _find_active_user(identity)


def get_perm_from_jwt_token(user: User, jwt_data: dict) -> set | None:
    """Get user permissions from JWT token.

    Args:
        user: The user object.
        jwt_data: The decoded JWT data containing user claims.

    Returns:
        A set of user's permissions or None if permissions are missing or an error occurs.

    """
    try:
        if not jwt_data or "user_claims" not in jwt_data:
            log_manager.store_user_auth_error_activity(user, "Missing user data in JWT")
            return None
        jwt_data = jwt_data["user_claims"]
        if "permissions" not in jwt_data:
            log_manager.store_user_auth_error_activity(user, "Missing user permissions in JWT")
            return None

        return set(jwt_data["permissions"])

    except Exception as ex:
        log_manager.store_auth_error_activity("Get permission from JWT error", ex)
        return None


def auth_required(required_permissions: str | list, *acl_args: ACLCheck) -> tuple[dict, HTTPStatus]:
    """Check if the user has the required permissions and ACL access.

    Args:
        required_permissions (str or list): The required permissions for the user.
        *acl_args: Variable number of arguments representing the ACLs to check.

    Returns:
        The decorated function.
    """

    def auth_required_wrap(fn):  # noqa: ANN001, ANN202
        @wraps(fn)
        def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            """Wrapper for checking permmisions.

            Args:
                *args: Positional arguments forwarded to the wrapped function.
                **kwargs: Keyword arguments forwarded to the wrapped function.

            Returns:
                Any: The result returned by the wrapped function.
            """
            error = ({"error": "not authorized"}, HTTPStatus.UNAUTHORIZED)

            required_permissions_set = set(required_permissions) if isinstance(required_permissions, list) else {required_permissions}

            # obtain the identity and current permissions of that identity
            user = get_user_from_jwt_token()
            if user:
                jwt_data = get_jwt()
                jwt_id = jwt_data.get("jti")
                if TokenBlacklist.is_blacklisted(jwt_id):
                    log_manager.store_auth_error_activity(f"Unauthorized API call acces (blacklisted token: {jwt_id})")
                    return error

                active_permissions_set = get_perm_from_jwt_token(user, jwt_data)

            else:
                # Fallback: check API key if JWT fails
                user = get_user_from_api_key()
                if not user:
                    log_manager.store_auth_error_activity("Unauthorized API call access (invalid user)")
                    return error

                active_permissions_set = get_perm_from_user(user)

            # is there at least one match with the permissions required by the call?
            if not required_permissions_set.intersection(active_permissions_set):
                log_manager.store_user_auth_error_activity(user, f"Insufficient permissions for user: {user.username}")
                return error

            # if the object does have an ACL, do we match it?
            if len(acl_args) > 0 and not check_acl(kwargs[get_id_name_by_acl(acl_args[0])], acl_args[0], user):
                log_manager.store_user_auth_error_activity(user, f"Access denied by ACL for user: {user.username}")
                return error

            # allow
            log_manager.store_user_activity(user, str(required_permissions_set), str(request.get_json(force=True, silent=True)))
            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(key_type: str | None) -> tuple[dict, HTTPStatus]:
    """Enforce API key authentication with additional resource type parameter.

    Args:
        key_type: The type of resource being accessed.

    Returns:
        function: The decorated function.
    """

    def decorator(fn):  # noqa: ANN001, ANN202
        @wraps(fn)
        def wrapper(*args, **kwargs) -> tuple[dict, HTTPStatus]:  # noqa: ANN002, ANN003
            error = ({"error": "not authorized"}, HTTPStatus.UNAUTHORIZED)

            # do we have the authorization header?
            if "Authorization" not in request.headers:
                log_manager.store_auth_error_activity("Missing Authorization header for external access")
                return error

            # is it properly encoded?
            auth_header = request.headers["Authorization"]
            if not auth_header.startswith("ApiKey"):
                log_manager.store_auth_error_activity("Missing Authorization ApiKey for external access")
                return error
            api_key = get_api_key()

            master_id = None
            if key_type == "collectors":
                master_class = CollectorsNode
                master_id = kwargs.get("collector_id")
            elif key_type == "publishers":
                master_class = PublishersNode
            elif key_type == "bots":
                master_class = BotsNode
            elif key_type == "remote":
                master_class = RemoteAccess
            else:
                log_manager.store_auth_error_activity(f"Incorrect validation type: {key_type}")
                return error

            # keep for debugging
            # import inspect
            # for frame in inspect.stack():
            #     if 'self' in frame.frame.f_locals:
            #         class_name = frame.frame.f_locals['self'].__class__.__name__
            #         break
            # print(f"api_key_required: {key_type},  {class_name}.{fn.__name__}", flush=True)

            # in case the same api_key is used for different nodes, we also need to check the node ID (if available)
            # otherwise return first node with valid api_key
            validated_object = master_class.get_by_api_key_id(api_key, master_id) if master_id else master_class.get_by_api_key(api_key)
            if not validated_object:
                api_key = log_manager.sensitive_value(api_key)
                log_manager.store_auth_error_activity(f"Incorrect api key: {api_key} for external access with type '{key_type}'")
                return error

            kwargs.update({key_type + "_node": validated_object})

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def jwt_token_required(fn) -> tuple[dict, HTTPStatus]:  # noqa: ANN001
    """Check if a valid JWT is present in the request headers.

    Args:
        fn: The function to be decorated.

    Returns:
        The decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs) -> tuple[dict, HTTPStatus]:  # noqa: ANN002, ANN003
        try:
            verify_jwt_in_request()
        except JWTExtendedException as ex:
            log_manager.store_auth_error_activity("Missing JWT", ex)
            return {"error": "authorization required"}, HTTPStatus.UNAUTHORIZED

        jwt_data = get_jwt()
        jwt_id = jwt_data.get("jti")
        if TokenBlacklist.is_blacklisted(jwt_id):
            log_manager.store_auth_error_activity(f"Blacklisted token: {jwt_id}")
            return {"error": "token revoked"}, HTTPStatus.UNAUTHORIZED

        identity = get_jwt_identity()
        if not identity:
            log_manager.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
            return {"error": "authorization failed"}, HTTPStatus.UNAUTHORIZED

        user = _find_active_user(identity)
        if user is None:
            return {"error": "authorization failed"}, HTTPStatus.UNAUTHORIZED

        log_manager.store_user_activity(user, "API_ACCESS", "Access permitted")
        return fn(*args, **kwargs)

    return wrapper


def get_api_key() -> str:
    """Get the API key from the request headers.

    This function retrieves the API key from the "Authorization" header of the request.
    The API key is expected to be in the format "ApiKey <api_key>".

    Returns:
        The API key extracted from the request headers.
    """
    return request.headers.get("Authorization", "").replace("ApiKey ", "")


def get_user_from_jwt() -> User:
    """Obtain the identity and current permissions.

    This function retrieves the user information from the JWT token. If the user information
    is not found in the JWT token, it falls back to retrieving the user information from the
    API key.

    Returns:
        The user object containing the identity and current permissions.
    """
    user = get_user_from_api_key()
    if user is None:
        user = get_user_from_jwt_token()
    return user


def decode_user_from_jwt(jwt_token: str) -> User:
    """Decode the user from a JWT token.

    Args:
        jwt_token (str): The JWT token to decode.

    Returns:
        User: The user object decoded from the JWT token.
    """
    decoded = None
    try:
        decoded = jwt.decode(jwt_token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except Exception as ex:  # e.g. "Signature has expired"
        log_manager.store_auth_error_activity(f"Invalid JWT: {ex!s}")
    if decoded is None:
        return None
    if decoded.get("scope"):
        # single-purpose tokens (MFA step, OAuth state) must never open a session
        log_manager.store_auth_error_activity("Scoped token rejected as session JWT")
        return None
    return _find_active_user(decoded["sub"])


def get_external_permissions_ids() -> list[str]:
    """Get the external permissions IDs."""
    return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG", "CONFIG_ACCESS"]


def get_external_permissions() -> list[Permission]:
    """Get the external permissions.

    This function retrieves a list of external permissions by calling the `get_external_permissions_ids` function
    and then fetching the corresponding permission objects using the `Permission.find` method.

    Returns:
        A list of external permission objects.
    """
    return [Permission.find(pid) for pid in get_external_permissions_ids()]
