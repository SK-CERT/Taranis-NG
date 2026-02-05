"""drop hotkey.key_code column

Revision ID: 98fea09779b8
Revises: eac704e8dea8
Create Date: 2025-03-07 15:22:58.958900

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "98fea09779b8"
down_revision = "eac704e8dea8"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("hotkey", "key_code")


def downgrade():
    op.add_column("hotkey", sa.Column("key_code", sa.Integer(), nullable=True))
