"""add updated tracking fields.

Revision ID: d1e2f3a4b5c6
Revises: c3f4a9e7d2b1
Create Date: 2026-01-25 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import column, table

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c3f4a9e7d2b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_updated and updated_by columns to product and report_item tables."""
    conn = op.get_bind()

    # Add last_updated column to product table
    op.add_column("product", sa.Column("last_updated", sa.DateTime(), nullable=True))

    # Copy created values to last_updated for existing records
    product_table = table("product", column("last_updated"), column("created"))
    conn.execute(product_table.update().where(product_table.c.last_updated.is_(None)).values(last_updated=product_table.c.created))

    # Make last_updated not nullable after copying data
    op.alter_column("product", "last_updated", nullable=False)

    # Add updated_by column to product table
    op.add_column("product", sa.Column("updated_by_id", sa.Integer(), nullable=True))
    op.create_foreign_key("product_updated_by_id_fkey", "product", "user", ["updated_by_id"], ["id"])

    # Copy user_id values to updated_by_id for existing records
    product_table = table("product", column("updated_by_id"), column("user_id"))
    conn.execute(product_table.update().where(product_table.c.updated_by_id.is_(None)).values(updated_by_id=product_table.c.user_id))

    # Add updated_by column to report_item table
    op.add_column("report_item", sa.Column("updated_by_id", sa.Integer(), nullable=True))
    op.create_foreign_key("report_item_updated_by_id_fkey", "report_item", "user", ["updated_by_id"], ["id"])

    # Copy user_id values to updated_by_id for existing records
    report_item_table = table("report_item", column("updated_by_id"), column("user_id"))
    conn.execute(
        report_item_table.update().where(report_item_table.c.updated_by_id.is_(None)).values(updated_by_id=report_item_table.c.user_id),
    )


def downgrade() -> None:
    """Remove last_updated and updated_by columns from product and report_item tables."""
    # Drop report_item columns
    op.drop_constraint("report_item_updated_by_id_fkey", "report_item", type_="foreignkey")
    op.drop_column("report_item", "updated_by_id")

    # Drop product columns
    op.drop_constraint("product_updated_by_id_fkey", "product", type_="foreignkey")
    op.drop_column("product", "updated_by_id")
    op.drop_column("product", "last_updated")
