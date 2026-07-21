"""Add authentication providers, user identities, user status/MFA, passkeys and security settings.

A second factor is required when *any* level demands it - the auth provider
(auth_provider.require_mfa), the site (security_settings.require_mfa), the user's
organization, or the user themselves. The passkey switch splits in two: sign-in
(passwordless) and second factor can be enabled independently.

The IdP-facing auth URLs (SAML metadata/ACS/discovery, OAuth redirect) embed the
provider identifier, so using the database id would make them change when a provider
is recreated or moved between environments - breaking the registration at the
identity provider. A stable, admin-controlled slug is used there instead.

Revision ID: e3f9d1a7c8b5
Revises: d2b016063dc7
Create Date: 2026-07-13 12:00:00.000000

"""

import logging
import os
import re
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "e3f9d1a7c8b5"
down_revision = "d2b016063dc7"
branch_labels = None
depends_on = None

NEW_PERMISSIONS = [
    ("CONFIG_AUTH_PROVIDER_ACCESS", "Config auth providers access", "Access to authentication providers configuration"),
    ("CONFIG_AUTH_PROVIDER_CREATE", "Config auth provider create", "Create authentication provider configuration"),
    ("CONFIG_AUTH_PROVIDER_UPDATE", "Config auth provider update", "Update authentication provider configuration"),
    ("CONFIG_AUTH_PROVIDER_DELETE", "Config auth provider delete", "Delete authentication provider configuration"),
]


def _slugify(value: str) -> str:
    """Turn a display name into a URL-safe slug (lowercase, hyphen-separated)."""
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return slug or "provider"


class PermissionAP(Base):
    """ORM helper for `permission` used by this migration."""

    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        description: str,
    ) -> None:
        """Initialize permission.

        Args:
            id (str): Permission identifier.
            name (str): Permission name.
            description (str): Permission description.
        """
        self.id = id
        self.name = name
        self.description = description

    @staticmethod
    def add(
        session: Session,
        id: str,  # noqa: A002
        name: str,
        description: str,
    ) -> None:
        """Add permission if not exists.

        Args:
            session (Session): DB session bound to migration connection.
            id (str): Permission identifier.
            name (str): Permission name.
            description (str): Permission description.
        """
        perm = session.query(PermissionAP).filter_by(id=id).first()
        if not perm:
            session.add(PermissionAP(id, name, description))

    @staticmethod
    def delete(
        session: Session,
        id: str,  # noqa: A002
    ) -> None:
        """Delete permission by id.

        Args:
            session (Session): DB session bound to migration connection.
            id (str): Permission identifier to delete.
        """
        perm = session.query(PermissionAP).filter_by(id=id).first()
        if perm:
            session.delete(perm)


class RoleAP(Base):
    """ORM helper for `role` used by this migration."""

    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(PermissionAP, secondary="role_permission")


class RolePermissionAP(Base):
    """ORM helper for `role_permission` used by this migration."""

    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


class AuthProviderAP(Base):
    """ORM helper for `auth_provider` used by this migration."""

    __tablename__ = "auth_provider"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    slug = sa.Column(sa.String(), unique=True, nullable=False)
    kind = sa.Column(sa.String(16), nullable=False)
    enabled = sa.Column(sa.Boolean, nullable=False)
    organization_id = sa.Column(sa.Integer, nullable=True)
    provisioning_mode = sa.Column(sa.String(16), nullable=False)
    allowed_domains = sa.Column(sa.String(), nullable=True)
    require_mfa = sa.Column(sa.Boolean, nullable=False)
    config = sa.Column(postgresql.JSON, nullable=False)
    secret = sa.Column(sa.String(), nullable=True)

    def __init__(self, name: str, kind: str, provisioning_mode: str, config: dict) -> None:
        """Initialize an enabled authentication provider seed row.

        Args:
            name (str): Provider display name.
            kind (str): Provider kind.
            provisioning_mode (str): Provisioning mode for auto-created users.
            config (dict): Kind-specific non-secret settings.
        """
        self.name = name
        self.slug = _slugify(name)
        self.kind = kind
        self.enabled = True
        self.provisioning_mode = provisioning_mode
        self.allowed_domains = ""
        self.require_mfa = False
        self.config = config


def _add_slug_column(conn: sa.engine.Connection) -> None:
    """Add the slug column to a pre-existing auth_provider table, backfilling it uniquely from the name."""
    op.add_column("auth_provider", sa.Column("slug", sa.String(), nullable=True))

    rows = conn.execute(sa.text("SELECT id, name FROM auth_provider ORDER BY id")).fetchall()
    used: set[str] = set()
    for row in rows:
        base = _slugify(row.name)
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used.add(candidate)
        conn.execute(sa.text("UPDATE auth_provider SET slug = :slug WHERE id = :id"), {"slug": candidate, "id": row.id})

    op.alter_column("auth_provider", "slug", existing_type=sa.String(), nullable=False)
    op.create_unique_constraint("uq_auth_provider_slug", "auth_provider", ["slug"])


def _seed_providers(session: Session) -> None:
    """Seed the local provider and, when configured via env, the legacy LDAP provider."""
    if not session.query(AuthProviderAP).filter_by(kind="local").first():
        session.add(AuthProviderAP("Local accounts", "local", "manual", {}))

    seed_ldap = os.getenv("TARANIS_NG_AUTHENTICATOR", "").lower() == "ldap" and os.getenv("LDAP_SERVER")
    if seed_ldap and not session.query(AuthProviderAP).filter_by(kind="ldap").first():
        ca_cert = ""
        ca_cert_path = Path(os.getenv("LDAP_CA_CERT_PATH", "auth/ldap_ca.pem"))
        if ca_cert_path.is_file():
            ca_cert = ca_cert_path.read_text()
        config = {
            "server_url": os.getenv("LDAP_SERVER"),
            "use_tls": True,
            "ca_cert": ca_cert,
            "user_dn_template": "uid={username}," + os.getenv("LDAP_BASE_DN", ""),
        }
        # matches the previous env-based behavior: users must already exist locally
        session.add(AuthProviderAP("LDAP", "ldap", "manual", config))
        logger.info("Seeded LDAP auth provider from TARANIS_NG_AUTHENTICATOR environment configuration")


def upgrade() -> None:
    """Create auth provider tables, user identity/MFA columns and seed defaults."""
    conn = op.get_bind()
    session = orm.Session(bind=conn)
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "auth_provider" not in tables:
        op.create_table(
            "auth_provider",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("name", sa.VARCHAR(), nullable=False),
            sa.Column("slug", sa.VARCHAR(), nullable=False),
            sa.Column("kind", sa.VARCHAR(length=16), nullable=False),
            sa.Column("enabled", sa.BOOLEAN(), nullable=False, server_default="true"),
            sa.Column("organization_id", sa.INTEGER(), nullable=True),
            sa.Column("provisioning_mode", sa.VARCHAR(length=16), nullable=False, server_default="manual"),
            sa.Column("allowed_domains", sa.VARCHAR(), nullable=True),
            sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default="false"),
            sa.Column("config", postgresql.JSON(), nullable=False, server_default="{}"),
            sa.Column("secret", sa.VARCHAR(), nullable=True),
            sa.Column("updated_by", sa.VARCHAR(), nullable=True),
            sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], name="auth_provider_organization_id_fkey"),
            sa.PrimaryKeyConstraint("id", name="auth_provider_pkey"),
            sa.UniqueConstraint("name", name="auth_provider_name_key"),
            sa.UniqueConstraint("slug", name="uq_auth_provider_slug"),
        )
    else:
        auth_provider_columns = [column["name"] for column in inspector.get_columns("auth_provider")]
        if "slug" not in auth_provider_columns:
            _add_slug_column(conn)

    if "auth_provider_role" not in tables:
        op.create_table(
            "auth_provider_role",
            sa.Column("auth_provider_id", sa.INTEGER(), nullable=False),
            sa.Column("role_id", sa.INTEGER(), nullable=False),
            sa.ForeignKeyConstraint(
                ["auth_provider_id"],
                ["auth_provider.id"],
                name="auth_provider_role_auth_provider_id_fkey",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["role_id"], ["role.id"], name="auth_provider_role_role_id_fkey", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("auth_provider_id", "role_id", name="auth_provider_role_pkey"),
        )

    if "user_auth_identity" not in tables:
        op.create_table(
            "user_auth_identity",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.INTEGER(), nullable=False),
            sa.Column("auth_provider_id", sa.INTEGER(), nullable=False),
            sa.Column("external_username", sa.VARCHAR(), nullable=False),
            sa.Column("external_id", sa.VARCHAR(), nullable=True),
            sa.Column("created_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_login_at", postgresql.TIMESTAMP(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="user_auth_identity_user_id_fkey", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["auth_provider_id"],
                ["auth_provider.id"],
                name="user_auth_identity_auth_provider_id_fkey",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="user_auth_identity_pkey"),
            sa.UniqueConstraint("auth_provider_id", "external_username", name="uq_identity_provider_username"),
        )
        op.create_index(
            "uq_identity_provider_external",
            "user_auth_identity",
            ["auth_provider_id", "external_id"],
            unique=True,
            postgresql_where=sa.text("external_id IS NOT NULL"),
        )

    if "user_webauthn_credential" not in tables:
        op.create_table(
            "user_webauthn_credential",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.INTEGER(), nullable=False),
            sa.Column("name", sa.VARCHAR(), nullable=False),
            sa.Column("credential_id", sa.VARCHAR(), nullable=False),
            sa.Column("public_key", sa.VARCHAR(), nullable=False),
            sa.Column("sign_count", sa.INTEGER(), nullable=False, server_default="0"),
            sa.Column("transports", sa.VARCHAR(), nullable=True),
            sa.Column("created_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_used_at", postgresql.TIMESTAMP(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="user_webauthn_credential_user_id_fkey", ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name="user_webauthn_credential_pkey"),
            sa.UniqueConstraint("credential_id", name="user_webauthn_credential_credential_id_key"),
        )

    # Site-wide security settings: the WebAuthn relying party that passkey sign-in
    # needs, plus site-wide MFA enforcement. Passkeys are credentials owned by users,
    # not an identity provider, so this is a setting rather than an auth_provider row.
    # passkey_second_factor is enabled by default: a user who has registered a passkey
    # could already use it as a second factor before this switch existed, and turning
    # it off here would silently take that away.
    if "security_settings" not in tables:
        op.create_table(
            "security_settings",
            sa.Column("id", sa.INTEGER(), autoincrement=False, nullable=False),
            sa.Column("passkey_enabled", sa.BOOLEAN(), nullable=False, server_default="false"),
            sa.Column("passkey_second_factor", sa.BOOLEAN(), nullable=False, server_default="true"),
            sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default="false"),
            sa.Column("rp_id", sa.VARCHAR(), nullable=True),
            sa.Column("rp_name", sa.VARCHAR(), nullable=True),
            sa.Column("origins", sa.VARCHAR(), nullable=True),
            sa.Column("updated_by", sa.VARCHAR(), nullable=True),
            sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id", name="security_settings_pkey"),
        )
        op.execute("INSERT INTO security_settings (id, passkey_enabled, rp_name) VALUES (1, false, 'Taranis NG')")
    else:
        security_columns = [column["name"] for column in inspector.get_columns("security_settings")]
        if "require_mfa" not in security_columns:
            op.add_column("security_settings", sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default="false"))
        if "passkey_second_factor" not in security_columns:
            op.add_column("security_settings", sa.Column("passkey_second_factor", sa.BOOLEAN(), nullable=False, server_default="true"))

    inspector = inspect(conn)
    user_columns = [column["name"] for column in inspector.get_columns("user")]
    if "status" not in user_columns:
        op.add_column("user", sa.Column("status", sa.VARCHAR(length=16), nullable=False, server_default="active"))
    if "email" not in user_columns:
        op.add_column("user", sa.Column("email", sa.VARCHAR(), nullable=True))
    if "totp_secret" not in user_columns:
        op.add_column("user", sa.Column("totp_secret", sa.VARCHAR(), nullable=True))
    if "totp_last_used_step" not in user_columns:
        op.add_column("user", sa.Column("totp_last_used_step", sa.BIGINT(), nullable=True))
    if "require_mfa" not in user_columns:
        op.add_column("user", sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default="false"))
    op.alter_column("user", "password", existing_type=sa.VARCHAR(), nullable=True)

    organization_columns = [column["name"] for column in inspector.get_columns("organization")]
    if "require_mfa" not in organization_columns:
        op.add_column("organization", sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default="false"))

    for permission_id, name, description in NEW_PERMISSIONS:
        PermissionAP.add(session, permission_id, name, description)
    session.commit()

    role = session.query(RoleAP).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(PermissionAP).all()
        session.add(role)
        session.commit()

    _seed_providers(session)
    session.commit()


def downgrade() -> None:
    """Remove auth provider tables, user identity/MFA columns and seeded permissions."""
    conn = op.get_bind()
    session = orm.Session(bind=conn)

    op.drop_table("security_settings")
    op.drop_table("user_webauthn_credential")
    op.drop_index("uq_identity_provider_external", table_name="user_auth_identity")
    op.drop_table("user_auth_identity")
    op.drop_table("auth_provider_role")
    op.drop_table("auth_provider")

    op.drop_column("organization", "require_mfa")

    # password was NOT NULL before this revision; externally provisioned users have none
    conn.execute(sa.text("UPDATE \"user\" SET password = '' WHERE password IS NULL"))
    op.alter_column("user", "password", existing_type=sa.VARCHAR(), nullable=False)
    op.drop_column("user", "require_mfa")
    op.drop_column("user", "totp_last_used_step")
    op.drop_column("user", "totp_secret")
    op.drop_column("user", "email")
    op.drop_column("user", "status")

    for permission_id, _, _ in NEW_PERMISSIONS:
        PermissionAP.delete(session, permission_id)
    session.commit()
