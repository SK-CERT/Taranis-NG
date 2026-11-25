"""How long a sign-in may last: ``security_settings.session_max_hours``.

A session's token lasts four hours, and the GUI refreshes it before it runs out - so a session
that stayed open never ended. The token now records when its sign-in happened (``auth_time``) and
is not refreshed past ``session_max_hours`` after it; 0 means no limit.

Every installation starts at 24 hours: people sign in once a day.

The column may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh
database from the models.

Downgrade drops the column.

Revision ID: b3e8d1f5a2c7
Revises: 7a4c1e9b2d36
Create Date: 2026-11-25 23:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3e8d1f5a2c7"
down_revision = "7a4c1e9b2d36"
branch_labels = None
depends_on = None

TABLE = "security_settings"
COLUMN = "session_max_hours"


def _has_column() -> bool:
    return COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    """Add security_settings.session_max_hours, 24 hours."""
    if _has_column():
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.Integer(), nullable=False, server_default="24"))


def downgrade() -> None:
    """Drop security_settings.session_max_hours."""
    if _has_column():
        op.drop_column(TABLE, COLUMN)
