"""WebAuthn (passkey) credential model."""

from __future__ import annotations

from datetime import datetime

from managers.db_manager import db
from shared.common import TZ


class WebauthnCredential(db.Model):
    """A WebAuthn credential (passkey) registered by a user.

    Attributes:
        id (int): Credential record ID.
        user_id (int): Owning user.
        name (str): User-facing label ("YubiKey", "MacBook Touch ID", ...).
        credential_id (str): base64url credential ID from the authenticator.
        public_key (str): base64 COSE public key.
        sign_count (int): Signature counter reported by the authenticator.
        transports (str): Comma-separated transport hints.
        created_at (datetime): Registration time.
        last_used_at (datetime): Last successful assertion.
    """

    __tablename__ = "user_webauthn_credential"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(), nullable=False)
    credential_id = db.Column(db.String(), nullable=False, unique=True)
    public_key = db.Column(db.String(), nullable=False)
    sign_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    transports = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="webauthn_credentials")

    def __init__(
        self,
        user_id: int,
        name: str,
        credential_id: str,
        public_key: str,
        sign_count: int = 0,
        transports: str | None = None,
    ) -> None:
        """Create a new passkey credential record."""
        self.user_id = user_id
        self.name = name
        self.credential_id = credential_id
        self.public_key = public_key
        self.sign_count = sign_count
        self.transports = transports
        self.created_at = datetime.now(TZ)

    @classmethod
    def find(cls, credential_record_id: int) -> WebauthnCredential | None:
        """Find a credential record by its database ID.

        Args:
            credential_record_id (int): Credential record ID.
        """
        return db.session.get(cls, credential_record_id)

    @classmethod
    def find_by_credential_id(cls, credential_id: str) -> WebauthnCredential | None:
        """Find a credential by the authenticator-provided credential ID.

        Args:
            credential_id (str): base64url credential ID.
        """
        return cls.query.filter_by(credential_id=credential_id).first()

    @classmethod
    def get_for_user(cls, user_id: int) -> list[WebauthnCredential]:
        """Get all passkeys of a user.

        Args:
            user_id (int): User ID.
        """
        return cls.query.filter_by(user_id=user_id).order_by(db.asc(WebauthnCredential.created_at)).all()

    @classmethod
    def rename(cls, credential_record_id: int, user_id: int, name: str) -> bool:
        """Rename a passkey owned by the given user.

        Args:
            credential_record_id (int): Credential record ID.
            user_id (int): The owner (scope check).
            name (str): New label.

        Returns:
            bool: True when the passkey was found and renamed.
        """
        record = db.session.get(cls, credential_record_id)
        if not record or record.user_id != user_id or not name:
            return False
        record.name = name
        db.session.commit()
        return True

    @classmethod
    def remove(cls, credential_record_id: int, user_id: int) -> bool:
        """Delete a passkey owned by the given user.

        Args:
            credential_record_id (int): Credential record ID.
            user_id (int): The owner (scope check).

        Returns:
            bool: True when the passkey was found and deleted.
        """
        record = db.session.get(cls, credential_record_id)
        if not record or record.user_id != user_id:
            return False
        db.session.delete(record)
        db.session.commit()
        return True

    @classmethod
    def delete_for_user(cls, user_id: int) -> None:
        """Delete all passkeys of a user (admin MFA reset).

        Args:
            user_id (int): User ID.
        """
        cls.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    def to_json(self) -> dict:
        """Return the GUI-facing representation (no key material)."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": str(self.created_at) if self.created_at else None,
            "last_used_at": str(self.last_used_at) if self.last_used_at else None,
        }

    def touch(self, sign_count: int) -> None:
        """Record a successful assertion.

        Args:
            sign_count (int): New signature counter value.
        """
        self.sign_count = sign_count
        self.last_used_at = datetime.now(TZ)
        db.session.commit()
