"""Encryption of secrets stored in the database (Fernet, key derived from config)."""

import base64
import hashlib

from config import Config
from cryptography.fernet import Fernet, InvalidToken
from managers.log_manager import logger

_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(Config.SECRETS_ENCRYPTION_KEY.encode()).digest()))

if Config.SECRETS_ENCRYPTION_KEY_IS_FALLBACK:
    logger.warning(
        "Secret 'secrets_encryption_key' is not set; falling back to jwt_secret_key for encrypting stored secrets. "
        "Configure a dedicated secrets_encryption_key Docker secret.",
    )


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext secret for storage in the database.

    Args:
        plaintext (str): The secret to encrypt.

    Returns:
        str: The Fernet token as a string.
    """
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str | None:
    """Decrypt a stored secret.

    Args:
        token (str): The Fernet token from the database.

    Returns:
        str | None: The plaintext secret, or None when decryption fails
                    (e.g. the encryption key changed).
    """
    try:
        return _fernet.decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        logger.error("Failed to decrypt a stored secret - was the secrets encryption key changed? Re-enter the affected secret.")
        return None
