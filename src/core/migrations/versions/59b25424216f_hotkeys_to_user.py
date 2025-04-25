"""remapping hotkeys to user table

Revision ID: 59b25424216f
Revises: f52e62aa1e84
Create Date: 2025-04-22 10:15:21.508666

"""

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "59b25424216f"
down_revision = "f52e62aa1e84"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("hotkey")]
    if "user_id" in columns:
        return

    op.add_column("hotkey", sa.Column("user_id", sa.Integer(), nullable=True))  # Add new column
    conn.execute(
        sa.text(
            """
            UPDATE hotkey
            SET user_id = (
                SELECT "user".id FROM "user"
                JOIN user_profile ON user_profile.id = "user".profile_id
                WHERE user_profile.id = hotkey.user_profile_id)
            """
        )
    )  # Remap
    op.drop_constraint("hotkey_user_profile_id_fkey", "hotkey", type_="foreignkey")  # Drop old constraint
    op.drop_column("hotkey", "user_profile_id")  # Drop old column
    op.create_foreign_key("hotkey_user_id_fkey", "hotkey", "user", ["user_id"], ["id"], ondelete="CASCADE")  # Add new constraint
    op.alter_column("hotkey", "user_id", nullable=False)  # Make NOT NULL


def downgrade():
    pass
