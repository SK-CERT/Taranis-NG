"""Add the global authentication-generation counter.

This revision is intentionally separate from the authentication schema and
seed revisions because installations may already have applied those revisions.
The server default initializes both the existing singleton row and any future
row to generation one.

Revision ID: a6b7c8d9e0f1
Revises: 4c8e1f7a2b90
Create Date: 2026-08-09 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a6b7c8d9e0f1"
down_revision = "4c8e1f7a2b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a positive, generation-one counter to existing security settings."""
    op.add_column(
        "security_settings",
        sa.Column("auth_generation", sa.INTEGER(), nullable=False, server_default=sa.text("1")),
    )
    op.create_check_constraint(
        "ck_security_settings_auth_generation_positive",
        "security_settings",
        "auth_generation > 0",
    )


def downgrade() -> None:
    """Remove only an unused generation-one counter.

    Once the counter has advanced, removing it would make previously revoked
    tokens valid again on older application code.  Require a backup-based
    rollback instead of silently weakening that security boundary.
    """
    connection = op.get_bind()
    generation_has_advanced = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM security_settings WHERE auth_generation <> 1)"),
    ).scalar()
    if generation_has_advanced:
        message = "Refusing to remove auth_generation after it has advanced; restore a pre-revision database backup instead"
        raise RuntimeError(message)

    op.drop_constraint(
        "ck_security_settings_auth_generation_positive",
        "security_settings",
        type_="check",
    )
    op.drop_column("security_settings", "auth_generation")
