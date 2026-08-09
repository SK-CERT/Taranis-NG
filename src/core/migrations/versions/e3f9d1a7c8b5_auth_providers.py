"""Add authentication-provider, identity, MFA, and security-settings schema.

This revision is deliberately schema-only.  Defaults and permissions are added
by the following data revision so database structure remains deterministic and
does not depend on process environment variables or files on the migrating host.

Revision ID: e3f9d1a7c8b5
Revises: 6f3a8d9c2e11
Create Date: 2026-07-13 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e3f9d1a7c8b5"
down_revision = "6f3a8d9c2e11"
branch_labels = None
depends_on = None


_UNSAFE_DOWNGRADE_CHECKS = (
    (
        "configured authentication providers",
        sa.text("SELECT EXISTS (SELECT 1 FROM auth_provider)"),
    ),
    (
        "linked external identities",
        sa.text("SELECT EXISTS (SELECT 1 FROM user_auth_identity)"),
    ),
    (
        "registered WebAuthn credentials",
        sa.text("SELECT EXISTS (SELECT 1 FROM user_webauthn_credential)"),
    ),
    (
        "user authentication data that cannot be represented by the previous schema",
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM "user"
                WHERE password IS NULL
                   OR status <> 'active'
                   OR email IS NOT NULL
                   OR require_mfa
                   OR totp_secret IS NOT NULL
                   OR totp_last_used_step IS NOT NULL
            )
            """,
        ),
    ),
    (
        "organization MFA requirements",
        sa.text("SELECT EXISTS (SELECT 1 FROM organization WHERE require_mfa)"),
    ),
    (
        "non-default site security settings",
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM security_settings
                WHERE passkey_enabled
                   OR NOT passkey_second_factor
                   OR require_mfa
                   OR auth_generation <> 1
                   OR rp_id IS NOT NULL
                   OR origins IS NOT NULL
                   OR updated_by IS NOT NULL
                   OR (rp_name IS NOT NULL AND rp_name <> 'Taranis NG')
            )
            """,
        ),
    ),
)


def _unsafe_downgrade_reasons(connection: sa.engine.Connection) -> list[str]:
    """Return auth data categories that an old schema cannot preserve."""
    return [description for description, query in _UNSAFE_DOWNGRADE_CHECKS if connection.execute(query).scalar()]


def upgrade() -> None:
    """Create authentication-provider, identity, MFA, and settings schema."""
    op.create_table(
        "auth_provider",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.Column("slug", sa.VARCHAR(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("enabled", sa.BOOLEAN(), nullable=False, server_default=sa.text("false")),
        sa.Column("organization_id", sa.INTEGER(), nullable=True),
        sa.Column("provisioning_mode", sa.VARCHAR(length=16), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("allowed_domains", sa.VARCHAR(), nullable=True),
        sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default=sa.text("false")),
        sa.Column("config", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("secret", sa.VARCHAR(), nullable=True),
        sa.Column("updated_by", sa.VARCHAR(), nullable=True),
        sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], name="auth_provider_organization_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="auth_provider_pkey"),
        sa.UniqueConstraint("name", name="auth_provider_name_key"),
        sa.UniqueConstraint("slug", name="uq_auth_provider_slug"),
    )

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

    op.create_table(
        "user_webauthn_credential",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.Column("credential_id", sa.VARCHAR(), nullable=False),
        sa.Column("public_key", sa.VARCHAR(), nullable=False),
        sa.Column("sign_count", sa.INTEGER(), nullable=False, server_default=sa.text("0")),
        sa.Column("transports", sa.VARCHAR(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_used_at", postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="user_webauthn_credential_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="user_webauthn_credential_pkey"),
        sa.UniqueConstraint("credential_id", name="user_webauthn_credential_credential_id_key"),
    )

    op.create_table(
        "security_settings",
        sa.Column("id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("passkey_enabled", sa.BOOLEAN(), nullable=False, server_default=sa.text("false")),
        sa.Column("passkey_second_factor", sa.BOOLEAN(), nullable=False, server_default=sa.text("true")),
        sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default=sa.text("false")),
        sa.Column("auth_generation", sa.INTEGER(), nullable=False, server_default=sa.text("1")),
        sa.Column("rp_id", sa.VARCHAR(), nullable=True),
        sa.Column("rp_name", sa.VARCHAR(), nullable=True),
        sa.Column("origins", sa.VARCHAR(), nullable=True),
        sa.Column("updated_by", sa.VARCHAR(), nullable=True),
        sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="security_settings_pkey"),
    )

    op.add_column("user", sa.Column("status", sa.VARCHAR(length=16), nullable=False, server_default=sa.text("'active'")))
    op.add_column("user", sa.Column("email", sa.VARCHAR(), nullable=True))
    op.add_column("user", sa.Column("totp_secret", sa.VARCHAR(), nullable=True))
    op.add_column("user", sa.Column("totp_last_used_step", sa.BIGINT(), nullable=True))
    op.add_column("user", sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default=sa.text("false")))
    op.alter_column("user", "password", existing_type=sa.VARCHAR(), nullable=True)

    op.add_column("organization", sa.Column("require_mfa", sa.BOOLEAN(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    """Remove the schema only when no authentication data would be lost."""
    connection = op.get_bind()
    unsafe_reasons = _unsafe_downgrade_reasons(connection)
    if unsafe_reasons:
        details = ", ".join(unsafe_reasons)
        message = (
            f"Refusing to downgrade authentication schema because it would discard {details}. Restore a pre-upgrade database backup instead."
        )
        raise RuntimeError(message)

    op.drop_table("security_settings")
    op.drop_table("user_webauthn_credential")
    op.drop_index("uq_identity_provider_external", table_name="user_auth_identity")
    op.drop_table("user_auth_identity")
    op.drop_table("auth_provider_role")
    op.drop_table("auth_provider")

    op.drop_column("organization", "require_mfa")

    op.alter_column("user", "password", existing_type=sa.VARCHAR(), nullable=False)
    op.drop_column("user", "require_mfa")
    op.drop_column("user", "totp_last_used_step")
    op.drop_column("user", "totp_secret")
    op.drop_column("user", "email")
    op.drop_column("user", "status")
