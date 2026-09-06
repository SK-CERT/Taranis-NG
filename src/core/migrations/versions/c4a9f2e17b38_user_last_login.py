"""Record when an account last signed in.

``user_auth_identity`` already stamps ``last_login_at``, but only for external providers: a
local password sign-in writes no identity row, so most accounts looked as if they had never
logged in. This adds the same stamp to the account itself, written wherever a sign-in
completes, so the administration list can show one column that is true for every login method.

Nullable with no backfill on purpose - the column means "the last login this deployment
observed", and nothing before this revision was observed. An account that has not signed in
since the upgrade reads as blank rather than as a fabricated date.

Revision ID: c4a9f2e17b38
Revises: b8e5d17c3f90
Create Date: 2026-09-05 17:20:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "c4a9f2e17b38"
down_revision = "b8e5d17c3f90"
branch_labels = None
depends_on = None

TABLE = "user"
COLUMN = "last_login_at"


def _has_column(connection: Connection) -> bool:
    """Whether the column is already present, so the revision can be re-run safely."""
    return bool(
        connection.execute(
            sa.text(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
                """,
            ),
            {"table": TABLE, "column": COLUMN},
        ).first(),
    )


def upgrade() -> None:
    """Add the last-login stamp."""
    connection = op.get_bind()
    if not _has_column(connection):
        op.add_column(TABLE, sa.Column(COLUMN, sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Drop the last-login stamp."""
    connection = op.get_bind()
    if _has_column(connection):
        op.drop_column(TABLE, COLUMN)
