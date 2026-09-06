"""Add the OSINT source enable switch.

``enabled`` replaces the convention of blanking ``REFRESH_INTERVAL`` to stop a source collecting.
That convention destroyed the configured interval, so switching a source back on could not restore
it. The server default keeps every existing source collecting, which is what they do today.

The rest of a source's run state -- whether it is collecting, and when it is next due -- is
deliberately not here. Both describe a collector node that is running, both are rebuilt from
scratch when a node restarts, and both have to expire when a node dies mid-run. They live in Redis,
where expiry does that on its own and no sweeper is needed.

Revision ID: c7a4e2f9b103
Revises: b8d3e6f5a417
Create Date: 2026-09-04 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7a4e2f9b103"
down_revision = "b8d3e6f5a417"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Let a source be switched off without losing its refresh interval."""
    op.add_column(
        "osint_source",
        sa.Column("enabled", sa.BOOLEAN(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    """Drop the switch; every source starts collecting again."""
    op.drop_column("osint_source", "enabled")
