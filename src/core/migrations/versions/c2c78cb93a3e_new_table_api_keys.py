"""add new table api_keys

Revision ID: c2c78cb93a3e
Revises: 890041d882b4
Create Date: 2022-11-11 15:28:27.340477

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c2c78cb93a3e"
down_revision = "890041d882b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_key",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("key", sa.VARCHAR(length=40), autoincrement=False, nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), autoincrement=False, nullable=True),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="api_key_user_fkey", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="api_key_pkey"),
        sa.UniqueConstraint("name", name="api_key_name_key"),
    )


def downgrade():
    op.drop_table("api_key")
