"""add cascade delete to osint_source releated tables

Revision ID: 890041d882b4
Revises: ac311a84207a
Create Date: 2022-11-03 08:54:54.131627

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "890041d882b4"
down_revision = "ac311a84207a"
branch_labels = None
depends_on = None


def upgrade():
    delete_previous()
    # osint_source_group_osint_source
    op.create_foreign_key(
        "osint_source_group_osint_source_osint_source_id_fkey",
        "osint_source_group_osint_source",
        "osint_source",
        ["osint_source_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # news_item_data
    op.create_foreign_key(
        "news_item_data_osint_source_id_fkey", "news_item_data", "osint_source", ["osint_source_id"], ["id"], ondelete="SET NULL"
    )
    # osint_source_parameter_value
    op.create_foreign_key(
        "osint_source_parameter_value_osint_source_id_fkey",
        "osint_source_parameter_value",
        "osint_source",
        ["osint_source_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # remote_access_osint_source
    op.create_foreign_key(
        "remote_access_osint_source_osint_source_id_fkey",
        "remote_access_osint_source",
        "osint_source",
        ["osint_source_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # osint_source_word_list
    op.create_foreign_key(
        "osint_source_word_list_osint_source_id_fkey",
        "osint_source_word_list",
        "osint_source",
        ["osint_source_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    delete_previous()
    op.create_foreign_key(
        "osint_source_group_osint_source_osint_source_id_fkey", "osint_source_group_osint_source", "osint_source", ["osint_source_id"], ["id"]
    )
    op.create_foreign_key("news_item_data_osint_source_id_fkey", "news_item_data", "osint_source", ["osint_source_id"], ["id"])
    op.create_foreign_key(
        "osint_source_parameter_value_osint_source_id_fkey", "osint_source_parameter_value", "osint_source", ["osint_source_id"], ["id"]
    )
    op.create_foreign_key(
        "remote_access_osint_source_osint_source_id_fkey", "remote_access_osint_source", "osint_source", ["osint_source_id"], ["id"]
    )
    op.create_foreign_key(
        "osint_source_word_list_osint_source_id_fkey", "osint_source_word_list", "osint_source", ["osint_source_id"], ["id"]
    )


def delete_previous():
    print("deleting previous objects...", flush=True)
    op.drop_constraint("osint_source_group_osint_source_osint_source_id_fkey", "osint_source_group_osint_source", type_="foreignkey")
    op.drop_constraint("news_item_data_osint_source_id_fkey", "news_item_data", type_="foreignkey")
    op.drop_constraint("osint_source_parameter_value_osint_source_id_fkey", "osint_source_parameter_value", type_="foreignkey")
    op.drop_constraint("remote_access_osint_source_osint_source_id_fkey", "remote_access_osint_source", type_="foreignkey")
    op.drop_constraint("osint_source_word_list_osint_source_id_fkey", "osint_source_word_list", type_="foreignkey")
