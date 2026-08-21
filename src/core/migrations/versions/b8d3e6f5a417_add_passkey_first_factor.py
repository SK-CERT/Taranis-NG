"""Add the passkey first-factor switch.

This revision is intentionally separate from the authentication schema and seed
revisions: installations may already have applied ``e3f9d1a7c8b5`` and
``4c8e1f7a2b90``, so neither of them may claim ownership of this column. The
server default keeps passwordless sign-in available on existing installations,
which is what they do today with only ``passkey_enabled`` to go on.

Revision ID: b8d3e6f5a417
Revises: d5f1c93ba470
Create Date: 2026-08-21 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8d3e6f5a417"
down_revision = "d5f1c93ba470"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Let administrators keep passkeys as a second factor only."""
    op.add_column(
        "security_settings",
        sa.Column("passkey_first_factor", sa.BOOLEAN(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    """Drop the switch, which returns passkey sign-in to always-on."""
    op.drop_column("security_settings", "passkey_first_factor")
