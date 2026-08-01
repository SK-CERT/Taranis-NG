"""WebAuthn (passkey) registration and authentication ceremonies.

The relying-party configuration (rp_id, rp_name, origins) is a site-wide
security setting (see :mod:`model.security_settings`) - passkeys are
credentials owned by users, not an identity provider. Challenges are
single-use and stored in Redis with a short TTL.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from managers.cache_manager import redis_client
from managers.log_manager import logger
from model.security_settings import SecuritySettings
from model.webauthn_credential import WebauthnCredential
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, options_to_json_dict
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

if TYPE_CHECKING:
    from model.user import User

CHALLENGE_TTL = 300


def passkeys_enabled() -> bool:
    """Tell whether passkey sign-in is enabled and fully configured."""
    return SecuritySettings.passkeys_enabled()


def passkey_second_factor_enabled() -> bool:
    """Tell whether a registered passkey may satisfy the second-factor step."""
    return SecuritySettings.passkey_second_factor_enabled()


def _rp_config() -> tuple[str, str, list[str]]:
    """Resolve rp_id, rp_name and allowed origins from the security settings.

    Raises:
        ValueError: When passkey sign-in is disabled or incompletely configured.
    """
    settings = SecuritySettings.get()
    if not settings.passkey_enabled:
        msg = "Passkey login is not configured"
        raise ValueError(msg)
    origins = settings.get_origins()
    if not settings.rp_id or not origins:
        msg = "Passkey login is missing the relying-party ID or origins"
        raise ValueError(msg)
    return settings.rp_id, settings.rp_name or "Taranis NG", origins


def _store_challenge(purpose: str, challenge: bytes, user_id: int | None) -> str:
    """Store a single-use challenge in Redis and return its handle."""
    challenge_id = str(uuid.uuid4())
    payload = json.dumps({"challenge": bytes_to_base64url(challenge), "user_id": user_id})
    redis_client.set(f"webauthn:{purpose}:{challenge_id}", payload, ex=CHALLENGE_TTL)
    return challenge_id


def _pop_challenge(purpose: str, challenge_id: str) -> dict | None:
    """Fetch and delete a stored challenge (single use)."""
    payload = redis_client.getdel(f"webauthn:{purpose}:{challenge_id}")
    if not payload:
        return None
    return json.loads(payload)


def begin_registration(user: User) -> dict:
    """Start a passkey registration ceremony for a logged-in user.

    Args:
        user (User): The registering user.

    Returns:
        dict: WebAuthn creation options (JSON-compatible) plus challenge_id.
    """
    rp_id, rp_name, _ = _rp_config()
    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(credential.credential_id))
        for credential in WebauthnCredential.get_for_user(user.id)
    ]
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=str(user.id).encode(),
        user_name=user.username,
        user_display_name=user.name or user.username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    challenge_id = _store_challenge("register", options.challenge, user.id)
    return {"options": options_to_json_dict(options), "challenge_id": challenge_id}


def finish_registration(user: User, challenge_id: str, credential: dict, name: str) -> WebauthnCredential:
    """Verify the authenticator's registration response and store the credential.

    Args:
        user (User): The registering user.
        challenge_id (str): Handle returned by begin_registration.
        credential (dict): The authenticator's response (WebAuthn JSON).
        name (str): User-facing label for the passkey.

    Returns:
        WebauthnCredential: The stored credential.

    Raises:
        ValueError: When the challenge is unknown/expired or verification fails.
    """
    rp_id, _, origins = _rp_config()
    stored = _pop_challenge("register", challenge_id)
    if not stored or stored.get("user_id") != user.id:
        msg = "Unknown or expired passkey registration challenge"
        raise ValueError(msg)
    verification = verify_registration_response(
        credential=credential,
        expected_challenge=base64url_to_bytes(stored["challenge"]),
        expected_rp_id=rp_id,
        expected_origin=origins,
    )
    from managers.db_manager import db  # noqa: PLC0415 - avoid import cycle at module load

    record = WebauthnCredential(
        user_id=user.id,
        name=name or "Passkey",
        credential_id=bytes_to_base64url(verification.credential_id),
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        transports=",".join(credential.get("response", {}).get("transports", []) or []),
    )
    db.session.add(record)
    db.session.commit()
    return record


def begin_authentication(user: User | None) -> dict:
    """Start a passkey authentication ceremony.

    Args:
        user (User): Restrict to this user's credentials (second-factor mode);
            None allows discoverable-credential (usernameless) login.

    Returns:
        dict: WebAuthn request options (JSON-compatible) plus challenge_id.
    """
    rp_id, _, _ = _rp_config()
    allow_credentials = None
    if user is not None:
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(credential.credential_id))
            for credential in WebauthnCredential.get_for_user(user.id)
        ]
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED if user is None else UserVerificationRequirement.PREFERRED,
    )
    challenge_id = _store_challenge("login", options.challenge, user.id if user else None)
    return {"options": options_to_json_dict(options), "challenge_id": challenge_id}


def finish_authentication(challenge_id: str, credential: dict) -> User | None:
    """Verify an authentication assertion and return the credential's owner.

    Args:
        challenge_id (str): Handle returned by begin_authentication.
        credential (dict): The authenticator's assertion (WebAuthn JSON).

    Returns:
        User: The owner of the asserted credential, or None on failure.
    """
    rp_id, _, origins = _rp_config()
    stored = _pop_challenge("login", challenge_id)
    if not stored:
        logger.warning("Unknown or expired passkey login challenge")
        return None
    record = WebauthnCredential.find_by_credential_id(credential.get("id", ""))
    if not record:
        logger.warning("Passkey assertion for unknown credential")
        return None
    if stored.get("user_id") is not None and stored["user_id"] != record.user_id:
        logger.warning("Passkey assertion does not belong to the challenged user")
        return None
    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(stored["challenge"]),
            expected_rp_id=rp_id,
            expected_origin=origins,
            credential_public_key=base64url_to_bytes(record.public_key),
            credential_current_sign_count=record.sign_count,
            require_user_verification=stored.get("user_id") is None,
        )
    except Exception as ex:
        logger.warning(f"Passkey assertion verification failed: {ex}")
        return None
    # Detect-only, not enforced: a non-increasing counter can signal a cloned
    # authenticator, but many legitimate authenticators (most passkeys/FIDO2
    # platform credentials) keep it at 0, so rejecting the login here would lock
    # those users out. We log the anomaly for auditing and let the login proceed.
    if verification.new_sign_count and record.sign_count and verification.new_sign_count <= record.sign_count:
        logger.warning(f"Passkey sign count did not increase for credential {record.id} - possible cloned authenticator")
    record.touch(verification.new_sign_count)
    return record.user
