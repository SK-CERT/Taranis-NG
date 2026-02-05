"""add cascade delete to report_item releated tables

Revision ID: 4f24c634cd22
Revises: aaf3d8b31972
Create Date: 2023-05-11 08:50:57.791722

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4f24c634cd22"
down_revision = "aaf3d8b31972"
branch_labels = None
depends_on = None


def upgrade():
    delete_previous()
    # report_item_attribute
    op.create_foreign_key(
        "report_item_attribute_report_item_id_fkey",
        "report_item_attribute",
        "report_item",
        ["report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # report_item_remote_report_item
    op.create_foreign_key(
        "report_item_remote_report_item_report_item_id_fkey",
        "report_item_remote_report_item",
        "report_item",
        ["report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "report_item_remote_report_item_remote_report_item_id_fkey",
        "report_item_remote_report_item",
        "report_item",
        ["remote_report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # asset_vulnerability
    op.create_foreign_key(
        "asset_vulnerability_report_item_id_fkey",
        "asset_vulnerability",
        "report_item",
        ["report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # product_report_item
    op.create_foreign_key(
        "product_report_item_report_item_id_fkey",
        "product_report_item",
        "report_item",
        ["report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # report_item_cpe
    op.create_foreign_key(
        "report_item_cpe_report_item_id_fkey",
        "report_item_cpe",
        "report_item",
        ["report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # report_item_news_item_aggregate
    op.create_foreign_key(
        "report_item_news_item_aggregate_report_item_id_fkey",
        "report_item_news_item_aggregate",
        "report_item",
        ["report_item_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    delete_previous()
    # report_item_attribute
    op.create_foreign_key("report_item_attribute_report_item_id_fkey", "report_item_attribute", "report_item", ["report_item_id"], ["id"])
    # report_item_remote_report_item
    op.create_foreign_key(
        "report_item_remote_report_item_report_item_id_fkey",
        "report_item_remote_report_item",
        "report_item",
        ["report_item_id"],
        ["id"],
    )
    op.create_foreign_key(
        "report_item_remote_report_item_remote_report_item_id_fkey",
        "report_item_remote_report_item",
        "report_item",
        ["remote_report_item_id"],
        ["id"],
    )
    # asset_vulnerability
    op.create_foreign_key("asset_vulnerability_report_item_id_fkey", "asset_vulnerability", "report_item", ["report_item_id"], ["id"])
    # product_report_item
    op.create_foreign_key("product_report_item_report_item_id_fkey", "product_report_item", "report_item", ["report_item_id"], ["id"])
    # report_item_cpe
    op.create_foreign_key("report_item_cpe_report_item_id_fkey", "report_item_cpe", "report_item", ["report_item_id"], ["id"])
    # report_item_news_item_aggregate
    op.create_foreign_key(
        "report_item_news_item_aggregate_report_item_id_fkey",
        "report_item_news_item_aggregate",
        "report_item",
        ["report_item_id"],
        ["id"],
    )


def delete_previous():
    print("deleting previous objects...", flush=True)
    # report_item_attribute
    op.drop_constraint("report_item_attribute_report_item_id_fkey", "report_item_attribute", type_="foreignkey")
    # report_item_remote_report_item
    op.drop_constraint("report_item_remote_report_item_report_item_id_fkey", "report_item_remote_report_item", type_="foreignkey")
    op.drop_constraint("report_item_remote_report_item_remote_report_item_id_fkey", "report_item_remote_report_item", type_="foreignkey")
    # asset_vulnerability
    op.drop_constraint("asset_vulnerability_report_item_id_fkey", "asset_vulnerability", type_="foreignkey")
    # product_report_item
    op.drop_constraint("product_report_item_report_item_id_fkey", "product_report_item", type_="foreignkey")
    # report_item_cpe
    op.drop_constraint("report_item_cpe_report_item_id_fkey", "report_item_cpe", type_="foreignkey")
    # report_item_news_item_aggregate
    op.drop_constraint("report_item_news_item_aggregate_report_item_id_fkey", "report_item_news_item_aggregate", type_="foreignkey")
