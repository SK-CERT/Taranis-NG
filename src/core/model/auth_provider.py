"""Authentication provider model (multiple simultaneous identity providers).

Kind-specific non-secret settings live in the ``config`` JSON column:

- oidc: issuer_url, client_id, scopes, username_claim, name_claim, email_claim,
  redirect_uri_override, logout_url
- oauth2: authorize_url, token_url, userinfo_url, client_id, scopes,
  username_claim, name_claim, email_claim
- saml (single IdP): idp_sso_url, idp_entity_id, idp_certificate, sp_entity_id,
  acs_url_override, username_attr, name_attr, email_attr
- saml (federation / discovery mode, when discovery_url is set): discovery_url,
  discovery_params (raw query string appended to the WAYF; some federations
  accept a filter parameter here), federation_metadata_url,
  federation_metadata_cert (PEM trust anchor), federation_metadata_refresh_hours;
  the idp_* fields are then unused, the chosen IdP being resolved from the
  verified federation metadata
- ldap: server_url, use_tls, ca_cert, user_dn_template OR (bind_dn, search_base,
  search_filter, username_attr, name_attr)
- local: (empty)

Passkeys are NOT a provider kind: they are credentials owned by users, and the
relying-party configuration they need is a site-wide security setting (see
:mod:`model.security_settings`).

The single secret per provider (OIDC/OAuth2 client secret, LDAP bind password)
is stored Fernet-encrypted in the ``secret`` column.
"""

from __future__ import annotations

import re
from datetime import datetime

from managers import crypto_manager
from managers.db_manager import db
from marshmallow import fields, post_load
from model.organization import Organization
from model.role import Role
from shared.common import TZ
from shared.schema.auth_provider import AUTH_PROVIDER_KINDS, AuthProviderSchema
from shared.schema.organization import OrganizationIdSchema
from shared.schema.role import RoleIdSchema

# A slug is a URL-safe, stable identifier used in the IdP-facing auth URLs
# (metadata/ACS/discovery, OAuth redirect) instead of the database id, so those
# URLs survive recreating a provider or moving between environments.
SLUG_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def slugify(value: str) -> str:
    """Turn a display name into a URL-safe slug (lowercase, hyphen-separated)."""
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "provider"


SINGLETON_KINDS = ("local",)
FORM_KINDS = ("local", "ldap")
# kinds that log in via a browser redirect to the IdP; oidc/oauth2 use the
# /auth/oauth/... endpoints, saml uses the /auth/saml/... endpoints
REDIRECT_KINDS = ("oidc", "oauth2", "saml")
OAUTH_KINDS = ("oidc", "oauth2")


class NewAuthProviderSchema(AuthProviderSchema):
    """Schema for creating a new authentication provider."""

    organization = fields.Nested(OrganizationIdSchema, allow_none=True, load_default=None)
    default_roles = fields.Nested(RoleIdSchema, many=True, load_default=list)

    @post_load
    def make(self, data: dict, **kwargs) -> AuthProvider:  # noqa: ANN003, ARG002
        """Create a new AuthProvider from deserialized data.

        Args:
            data (dict): Deserialized provider data.
            **kwargs: Additional keyword arguments.

        Returns:
            AuthProvider: New authentication provider object.
        """
        return AuthProvider(**data)


class AuthProvider(db.Model):
    """Authentication provider configured in the database.

    Attributes:
        id (int): Provider ID.
        name (str): Display name (unique, shown on the login page).
        slug (str): URL-safe stable identifier (unique) used in the IdP-facing
            auth URLs instead of the database id, so registering the provider at
            an IdP survives recreation and moving between environments.
        kind (str): One of local | oidc | oauth2 | saml | ldap.
        enabled (bool): Whether the provider can be used for login.
        organization_id (int): Organization assigned to auto-created users.
        provisioning_mode (str): manual (linked identities only) | approval
            (auto-create pending users) | automatic (auto-create active users).
        allowed_domains (str): Comma-separated email domains allowed to
            auto-provision; empty means all.
        require_mfa (bool): Force MFA for form-based logins (local/ldap kinds).
        config (dict): Kind-specific non-secret settings (see module docstring).
        secret (str): Fernet-encrypted secret (client secret / bind password).
        updated_by (str): User who last updated the record.
        updated_at (datetime): Timestamp of the last update.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)
    slug = db.Column(db.String(), nullable=False, unique=True)
    kind = db.Column(db.String(16), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=True)
    provisioning_mode = db.Column(db.String(16), nullable=False, default="manual", server_default="manual")
    allowed_domains = db.Column(db.String(), nullable=True)
    require_mfa = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    config = db.Column(db.JSON, nullable=False, default=dict)
    secret = db.Column(db.String(), nullable=True)
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    organization = db.relationship("Organization")
    default_roles = db.relationship("Role", secondary="auth_provider_role")

    def __init__(
        self,
        name: str,
        kind: str,
        slug: str | None = None,
        enabled: bool = True,
        organization: object | None = None,
        default_roles: list | None = None,
        provisioning_mode: str = "manual",
        allowed_domains: str | None = "",
        require_mfa: bool = False,
        config: dict | None = None,
        secret: str | None = None,
        id: int | None = None,  # noqa: A002, ARG002
    ) -> None:
        """Create a new authentication provider."""
        self.name = name
        self.slug = (slug or "").strip()
        self.kind = kind
        self.enabled = enabled
        self.organization = Organization.find(organization.id) if organization else None
        self.default_roles = [role for role in (Role.find(r.id) for r in default_roles or []) if role]
        self.provisioning_mode = provisioning_mode
        self.allowed_domains = allowed_domains or ""
        self.require_mfa = require_mfa
        self.config = config or {}
        self.secret = crypto_manager.encrypt(secret) if secret else None

    @property
    def has_secret(self) -> bool:
        """Tell whether a secret is stored for this provider."""
        return bool(self.secret)

    def get_secret_plaintext(self) -> str | None:
        """Decrypt and return the stored secret, or None when absent or undecryptable."""
        if not self.secret:
            return None
        return crypto_manager.decrypt(self.secret)

    def get_allowed_domains(self) -> list[str]:
        """Return the allowed email domains as a normalized list (empty = all)."""
        return [domain.strip().lower() for domain in (self.allowed_domains or "").split(",") if domain.strip()]

    @classmethod
    def find(cls, provider_id: int) -> AuthProvider | None:
        """Find an authentication provider by ID.

        Args:
            provider_id (int): Provider ID.

        Returns:
            AuthProvider: Provider object or None.
        """
        return db.session.get(cls, provider_id)

    @classmethod
    def find_by_slug(cls, slug: str) -> AuthProvider | None:
        """Find an authentication provider by its URL slug.

        Args:
            slug (str): Provider slug.

        Returns:
            AuthProvider: Provider object or None.
        """
        if not slug:
            return None
        return cls.query.filter_by(slug=slug).first()

    @classmethod
    def _unique_slug(cls, base: str, provider_id: int | None = None) -> str:
        """Return a unique slug derived from ``base`` (appending -2, -3, ... on collision)."""
        base = slugify(base)
        candidate = base
        suffix = 2
        while True:
            existing = cls.query.filter_by(slug=candidate).first()
            if not existing or existing.id == provider_id:
                return candidate
            candidate = f"{base}-{suffix}"
            suffix += 1

    @classmethod
    def get_all(cls) -> list[AuthProvider]:
        """Get all authentication providers ordered by id (the order they were created)."""
        return cls.query.order_by(db.asc(AuthProvider.id)).all()

    @classmethod
    def get_enabled(cls) -> list[AuthProvider]:
        """Get all enabled authentication providers ordered by id.

        This is the order the login page shows them in, so it is the admin's to
        control: renaming a provider must not reshuffle the login buttons.
        """
        return cls.query.filter_by(enabled=True).order_by(db.asc(AuthProvider.id)).all()

    @classmethod
    def get_enabled_by_kind(cls, kinds: tuple | list) -> list[AuthProvider]:
        """Get enabled providers of the given kinds ordered by id.

        Args:
            kinds (tuple | list): Provider kinds to include.
        """
        return cls.query.filter(AuthProvider.enabled.is_(True), AuthProvider.kind.in_(kinds)).order_by(db.asc(AuthProvider.id)).all()

    @classmethod
    def get(cls, search_string: str | None) -> tuple[list[AuthProvider], int]:
        """Get authentication providers filtered by a search string, ordered by id.

        Args:
            search_string (str): Search string.

        Returns:
            tuple: Providers and their count.
        """
        query = cls.query
        if search_string is not None:
            query = query.filter(AuthProvider.name.ilike(f"%{search_string}%"))
        return query.order_by(db.asc(AuthProvider.id)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict:
        """Get all authentication providers in JSON format.

        Args:
            search (str): Search string.

        Returns:
            dict: Total count and provider items (secrets are never dumped).
        """
        providers, count = cls.get(search)
        schema = AuthProviderSchema(many=True)
        items = schema.dump(providers)
        for item, provider in zip(items, providers, strict=True):
            item["linked_identity_count"] = UserAuthIdentity.count_for_provider(provider.id)
        return {"total_count": count, "items": items}

    @classmethod
    def _validate(cls, provider: AuthProvider, provider_id: int | None = None) -> None:
        """Validate provider constraints (kind values, singleton kinds, SAML certificate).

        Raises:
            ValueError: When the kind is unknown, a singleton kind already
                exists, the slug is malformed or taken, or a SAML certificate
                cannot be parsed.
        """
        if provider.kind not in AUTH_PROVIDER_KINDS:
            msg = f"Unknown authentication provider kind: {provider.kind}"
            raise ValueError(msg)
        slug = (provider.slug or "").strip()
        if not SLUG_PATTERN.match(slug):
            msg = "The slug may contain only lowercase letters, digits and hyphens, and must start and end with one"
            raise ValueError(msg)
        taken = cls.query.filter_by(slug=slug).first()
        if taken and taken.id != provider_id:
            msg = f"The slug '{slug}' is already used by another login method"
            raise ValueError(msg)
        if provider.kind in SINGLETON_KINDS:
            existing = cls.query.filter_by(kind=provider.kind).first()
            if existing and existing.id != provider_id:
                msg = f"Only one provider of kind '{provider.kind}' is allowed"
                raise ValueError(msg)
        if provider.kind == "saml":
            # a certificate or keypair that does not parse would otherwise only
            # fail at the first login, as an opaque "auth_failed"
            from auth.saml_authenticator import (  # noqa: PLC0415 - avoid an import cycle at module load
                load_idp_certificates,
                validate_sp_keypair,
            )
            from auth.saml_federation import is_federation_mode  # noqa: PLC0415

            config = provider.config or {}
            if is_federation_mode(config):
                # No single pinned IdP certificate in federation mode: the chosen
                # IdP is resolved from the federation metadata, whose signature is
                # verified against this pinned trust anchor. Both must be present
                # and the anchor must parse.
                if not config.get("federation_metadata_url"):
                    msg = "Federation mode needs a federation metadata URL"
                    raise ValueError(msg)
                if not (config.get("federation_metadata_cert") or "").strip():
                    msg = "Federation mode needs the federation metadata signing certificate (the trust anchor)"
                    raise ValueError(msg)
                load_idp_certificates(config["federation_metadata_cert"])
            else:
                load_idp_certificates(config.get("idp_certificate", ""))

            # The SP private key (in the encrypted secret column) and its certificate must
            # belong together, or the IdP encrypts to a key we cannot use. On edit an empty
            # secret means "keep the stored key", so fall back to the saved one.
            certificate = (config.get("sp_certificate") or "").strip()
            private_key = provider.get_secret_plaintext() or ""
            if not private_key and provider_id:
                existing = db.session.get(cls, provider_id)
                private_key = (existing.get_secret_plaintext() or "") if existing else ""

            if certificate or private_key:
                if not (certificate and private_key):
                    msg = "A service provider keypair needs both the private key and the certificate"
                    raise ValueError(msg)
                validate_sp_keypair(private_key, certificate)

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> AuthProvider:
        """Add a new authentication provider.

        Args:
            data (dict): Provider data (plaintext secret is encrypted here).
            user_name (str): User who is creating the provider.

        Returns:
            AuthProvider: New provider object.
        """
        schema = NewAuthProviderSchema()
        new = schema.load(data)
        # An admin-supplied slug is respected (and validated); a blank one is
        # auto-generated from the name and made unique.
        new.slug = (new.slug or "").strip() or cls._unique_slug(new.name)
        cls._validate(new)
        new.updated_by = user_name
        new.updated_at = datetime.now(TZ)
        db.session.add(new)
        db.session.commit()
        return new

    @classmethod
    def update(cls, provider_id: int, data: dict, user_name: str) -> AuthProvider:
        """Update an existing authentication provider.

        An empty/absent secret keeps the currently stored one.

        Args:
            provider_id (int): ID of the provider to update.
            data (dict): New provider data.
            user_name (str): User who is updating the provider.

        Returns:
            AuthProvider: Updated provider object.
        """
        schema = NewAuthProviderSchema()
        new = schema.load(data)
        old = db.session.get(cls, provider_id)
        new.kind = old.kind  # kind is immutable after creation
        new.slug = (new.slug or "").strip() or cls._unique_slug(new.name, provider_id)
        cls._validate(new, provider_id)
        old.name = new.name
        old.slug = new.slug
        old.enabled = new.enabled
        old.organization = new.organization
        old.default_roles = new.default_roles
        old.provisioning_mode = new.provisioning_mode
        old.allowed_domains = new.allowed_domains
        old.require_mfa = new.require_mfa
        old.config = new.config
        if new.secret:
            old.secret = new.secret
        old.updated_by = user_name
        old.updated_at = datetime.now(TZ)
        db.session.commit()
        if old.kind == "saml":
            # a changed metadata URL/cert or discovery setting must take effect now
            from auth.saml_federation import invalidate  # noqa: PLC0415 - avoid an import cycle at module load

            invalidate(provider_id)
        return old

    @classmethod
    def delete(cls, provider_id: int) -> None:
        """Delete an authentication provider (its identity links are removed too).

        Args:
            provider_id (int): Provider ID.
        """
        UserAuthIdentity.query.filter_by(auth_provider_id=provider_id).delete()
        record = db.session.get(cls, provider_id)
        db.session.delete(record)
        db.session.commit()
        from auth.saml_federation import invalidate  # noqa: PLC0415 - avoid an import cycle at module load

        invalidate(provider_id)


class AuthProviderRole(db.Model):
    """Association table between AuthProvider and its default Roles.

    Attributes:
        auth_provider_id (int): The ID of the authentication provider.
        role_id (int): The ID of the role.
    """

    auth_provider_id = db.Column(db.Integer, db.ForeignKey("auth_provider.id", ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id", ondelete="CASCADE"), primary_key=True)


class UserAuthIdentity(db.Model):
    """Link between a local user account and an identity at an authentication provider.

    One user can hold identities at many providers (and log in through any of
    them); one identity belongs to exactly one user.

    Attributes:
        id (int): Identity ID.
        user_id (int): The local user account.
        auth_provider_id (int): The authentication provider.
        external_username (str): Username at the provider (admin-enterable).
        external_id (str): Stable identifier at the provider (OIDC ``sub`` /
            LDAP DN), backfilled at first login.
        created_at (datetime): When the link was created.
        last_login_at (datetime): Last successful login through this identity.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    auth_provider_id = db.Column(db.Integer, db.ForeignKey("auth_provider.id", ondelete="CASCADE"), nullable=False)
    external_username = db.Column(db.String(), nullable=False)
    external_id = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint("auth_provider_id", "external_username", name="uq_identity_provider_username"),)

    user = db.relationship("User", back_populates="auth_identities")
    provider = db.relationship("AuthProvider")

    def __init__(self, user_id: int | None, auth_provider_id: int, external_username: str, external_id: str | None = None) -> None:
        """Create a new identity link."""
        self.user_id = user_id
        self.auth_provider_id = auth_provider_id
        self.external_username = external_username
        self.external_id = external_id
        self.created_at = datetime.now(TZ)

    @classmethod
    def find_by_external(cls, provider_id: int, external_id: str | None, external_username: str | None) -> UserAuthIdentity | None:
        """Find the identity matching an externally authenticated subject.

        Matches by (provider, external_id) first; falls back to
        (provider, external_username) only when the stored identity has no
        conflicting external_id, in which case the external_id is backfilled.

        Args:
            provider_id (int): The authentication provider ID.
            external_id (str): Stable subject identifier from the provider.
            external_username (str): Username reported by the provider.

        Returns:
            UserAuthIdentity: The matching identity or None.
        """
        if external_id:
            identity = cls.query.filter_by(auth_provider_id=provider_id, external_id=external_id).first()
            if identity:
                return identity
        if external_username:
            identity = cls.query.filter_by(auth_provider_id=provider_id, external_username=external_username).first()
            if identity and (not identity.external_id or identity.external_id == external_id):
                if external_id and not identity.external_id:
                    identity.external_id = external_id
                    db.session.commit()
                return identity
        return None

    @classmethod
    def count_for_provider(cls, provider_id: int) -> int:
        """Count identity links of a provider (for GUI delete warnings).

        Args:
            provider_id (int): Provider ID.
        """
        return cls.query.filter_by(auth_provider_id=provider_id).count()

    def touch_login(self) -> None:
        """Record a successful login through this identity."""
        self.last_login_at = datetime.now(TZ)
        db.session.commit()
