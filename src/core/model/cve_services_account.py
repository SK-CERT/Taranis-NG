"""An organization's account at MITRE's CVE Services, for publishing CVE records as a CNA.

A CVE Numbering Authority (CNA) reserves CVE IDs and publishes CVE records through the CVE
Services API with three credentials: the CNA's short name, a user of it, and that user's API key.
An organization has at most one account, in one row: the environment (production, or the test
service for trying it out), the short name and the user as they are, the API key Fernet-encrypted.
``org_uuid`` is the CNA's UUID as CVE Services reports it; a record's provider metadata names it.
A CVD Report is published with the account of its organization (``report_item.organization_id``).
"""

from __future__ import annotations

from datetime import datetime

from config import Config
from managers import crypto_manager
from managers.db_manager import db
from shared.common import TZ
from shared.gcve import CVE_ENVIRONMENTS, CVE_SERVICES_URLS


class CveServicesAccount(db.Model):
    """The CNA account Taranis calls CVE Services with for an organization.

    Attributes:
        organization_id: The organization acting as the CNA.
        environment: ``production`` or ``test``.
        short_name: The CNA's short name (``CVE-API-ORG``).
        username: Its user Taranis acts as (``CVE-API-USER``).
        api_key: That user's API key (``CVE-API-KEY``), Fernet-encrypted.
        org_uuid: The CNA's UUID, as CVE Services last reported it.
    """

    __tablename__ = "cve_services_account"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"), nullable=False, unique=True)
    environment = db.Column(db.String(16), nullable=False, default="test")
    short_name = db.Column(db.String(64), nullable=False, default="")
    username = db.Column(db.String(255), nullable=False, default="")
    api_key = db.Column(db.String(), nullable=True)
    org_uuid = db.Column(db.String(64), nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime(timezone=True))

    @classmethod
    def get(cls, organization_id: int | None) -> CveServicesAccount | None:
        """The organization's account, if one has been saved."""
        return cls.query.filter_by(organization_id=organization_id).first() if organization_id is not None else None

    @classmethod
    def configured(cls, organization_id: int | None) -> CveServicesAccount | None:
        """The organization's account, when it holds everything a call needs; None otherwise."""
        account = cls.get(organization_id)
        return account if account is not None and account.complete else None

    @property
    def complete(self) -> bool:
        """Whether a call can be made: a short name, a user and an API key."""
        return bool((self.short_name or "").strip() and (self.username or "").strip() and self.api_key)

    @property
    def has_secret(self) -> bool:
        """Whether an API key is stored."""
        return bool(self.api_key)

    @property
    def base_url(self) -> str:
        """Where CVE Services answers for this account (``TARANIS_CVE_SERVICES_URL`` overrides it)."""
        return Config.CVE_SERVICES_URL or CVE_SERVICES_URLS.get(self.environment, CVE_SERVICES_URLS["test"])

    def get_api_key(self) -> str | None:
        """The API key in clear; None when none is stored or it cannot be decrypted."""
        return crypto_manager.decrypt(self.api_key) if self.api_key else None

    @classmethod
    def save(
        cls,
        organization_id: int,
        environment: str,
        short_name: str,
        username: str,
        api_key: str | None,
        user_name: str,
    ) -> CveServicesAccount:
        """Store the organization's account, in the caller's transaction; an empty ``api_key`` keeps the stored one.

        Raises:
            ValueError: For an unknown environment.
        """
        if environment not in CVE_ENVIRONMENTS:
            msg = f"The environment is one of: {', '.join(CVE_ENVIRONMENTS)}"
            raise ValueError(msg)
        account = cls.get(organization_id)
        if account is None:
            account = cls(organization_id=organization_id)
            db.session.add(account)
        if account.short_name != short_name.strip() or account.environment != environment:
            # Another CNA, or another service: its UUID is looked up again.
            account.org_uuid = None
        account.environment = environment
        account.short_name = short_name.strip()
        account.username = username.strip()
        if api_key:
            account.api_key = crypto_manager.encrypt(api_key)
        account.updated_by = user_name
        account.updated_at = datetime.now(TZ)
        return account

    def to_json(self) -> dict:
        """The account as the GUI shows it: never the API key."""
        return {
            "environment": self.environment,
            "short_name": self.short_name,
            "username": self.username,
            "has_secret": self.has_secret,
            "org_uuid": self.org_uuid,
            "complete": self.complete,
            "url": self.base_url,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
