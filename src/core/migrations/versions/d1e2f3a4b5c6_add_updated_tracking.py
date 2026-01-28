"""add updated tracking fields.

Revision ID: d1e2f3a4b5c6
Revises: c3f4a9e7d2b1
Create Date: 2026-01-25 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c3f4a9e7d2b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add updated_at and updated_by columns to product and report_item tables."""
    conn = op.get_bind()

    # Add product.updated_at
    op.add_column("product", sa.Column("updated_at", postgresql.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")))
    product_table = table("product", column("updated_at"), column("created"))
    conn.execute(product_table.update().values(updated_at=product_table.c.created))
    op.alter_column("product", "updated_at", nullable=False)

    # Add product.updated_by
    op.add_column("product", sa.Column("updated_by", sa.String(), nullable=True))
    product_table = table("product", column("updated_by"), column("user_id"))
    user_table = table("user", column("id"), column("name"))
    conn.execute(
        product_table.update().where(product_table.c.user_id == user_table.c.id).values(updated_by=user_table.c.name),
    )

    # Add report_item.updated_by
    op.add_column("report_item", sa.Column("updated_by", sa.String(), nullable=True))
    report_item_table = table("report_item", column("updated_by"), column("user_id"))
    user_table = table("user", column("id"), column("name"))
    conn.execute(
        report_item_table.update().where(report_item_table.c.user_id == user_table.c.id).values(updated_by=user_table.c.name),
    )


def downgrade() -> None:
    """Remove updated_at and updated_by columns from product and report_item tables."""
    op.drop_column("report_item", "updated_by")
    op.drop_column("product", "updated_by")
    op.drop_column("product", "updated_at")
