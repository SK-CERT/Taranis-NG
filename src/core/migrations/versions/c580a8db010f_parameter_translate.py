"""Add translate column to parameter table.

Revision ID: c580a8db010f
Revises: 8b3f5c1d7e24
Create Date: 2026-10-30 12:35:56.923549

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c580a8db010f"
down_revision = "8b3f5c1d7e24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the translate column to parameter table."""
    op.add_column(
        "parameter",
        sa.Column("translate", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Drop the translate column from parameter table."""
    op.drop_column("parameter", "translate")
