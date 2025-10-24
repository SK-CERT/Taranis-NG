"""Add new ai_provider table.

Revision ID: ba4956806c68
Revises: 59b25424216f
Create Date: 2025-06-09 15:45:17.303274

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, orm
from sqlalchemy.dialects import postgresql

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "ba4956806c68"
down_revision = "59b25424216f"
branch_labels = None
depends_on = None

Base = orm.declarative_base()


def upgrade() -> None:
    """Add ai_provider table and modify attribute_group_item table."""
    conn = op.get_bind()
    session = orm.Session(bind=conn)

    inspector = inspect(conn)
    if "ai_provider" not in inspector.get_table_names():
        op.create_table(
            "ai_provider",
            sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
            sa.Column("name", sa.VARCHAR(), nullable=False),
            sa.Column("api_type", sa.VARCHAR(), nullable=False, server_default="openai"),
            sa.Column("api_url", sa.VARCHAR(), nullable=False),
            sa.Column("api_key", sa.VARCHAR()),
            sa.Column("model", sa.VARCHAR(), nullable=False),
            sa.Column("updated_by", sa.VARCHAR()),
            sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id", name="ai_provider_pkey"),
            sa.UniqueConstraint("name", name="ai_provider_name_key"),
        )

    inspector = inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("attribute_group_item")]
    if "ai_provider_id" not in columns:
        op.add_column("attribute_group_item", sa.Column("ai_provider_id", sa.INTEGER()))
        op.create_foreign_key(
            "attribute_group_ai_provider_id_fkey",
            "attribute_group_item",
            "ai_provider",
            ["ai_provider_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.add_column("attribute_group_item", sa.Column("ai_prompt", sa.String()))

    session.commit()


def downgrade() -> None:
    """Remove ai_provider table and revert modifications to attribute_group_item table."""
    logger.info("deleting table 'ai_provider'...")
    op.drop_constraint("attribute_group_ai_provider_id_fkey", "attribute_group_item", type_="foreignkey")
    op.drop_column("attribute_group_item", "ai_provider_id")
    op.drop_column("attribute_group_item", "ai_prompt")
    op.drop_table("ai_provider")
