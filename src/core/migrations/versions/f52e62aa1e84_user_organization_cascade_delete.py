"""cascade_delete: User, User_profile, Word_list, Organization

Revision ID: f52e62aa1e84
Revises: 28cccb4efc5f
Create Date: 2025-04-04 16:42:57.473267

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f52e62aa1e84"
down_revision = "28cccb4efc5f"
branch_labels = None
depends_on = None


def cascade_delete(enable):
    cascade_str = "CASCADE" if enable else None
    setnull_str = "SET NULL" if enable else None
    # organization
    create_constraint(
        "asset_group_organization_organization_id_fkey",
        "asset_group_organization",
        "organization",
        ["organization_id"],
        ["id"],
        ondelete=cascade_str,
    )
    create_constraint(
        "notification_template_organization_organization_id_fkey",
        "notification_template_organization",
        "organization",
        ["organization_id"],
        ["id"],
        ondelete=cascade_str,
    )
    create_constraint(
        "user_organization_organization_id_fkey", "user_organization", "organization", ["organization_id"], ["id"], ondelete=cascade_str
    )
    # address
    create_constraint("organization_address_id_fkey", "organization", "address", ["address_id"], ["id"], ondelete=setnull_str)  # keep
    # user
    create_constraint("acl_entry_user_user_id_fkey", "acl_entry_user", "user", ["user_id"], ["id"], ondelete=cascade_str)
    create_constraint("asset_group_user_user_id_fkey", "asset_group_user", "user", ["user_id"], ["id"], ondelete=cascade_str)
    create_constraint("news_item_vote_user_id_fkey", "news_item_vote", "user", ["user_id"], ["id"], ondelete=cascade_str)
    create_constraint("product_user_id_fkey", "product", "user", ["user_id"], ["id"], ondelete=setnull_str)  # keep
    create_constraint(
        "report_item_attribute_user_id_fkey", "report_item_attribute", "user", ["user_id"], ["id"], ondelete=setnull_str  # keep
    )
    create_constraint("report_item_user_id_fkey", "report_item", "user", ["user_id"], ["id"], ondelete=setnull_str)  # keep
    create_constraint("user_organization_user_id_fkey", "user_organization", "user", ["user_id"], ["id"], ondelete=cascade_str)
    create_constraint("user_permission_user_id_fkey", "user_permission", "user", ["user_id"], ["id"], ondelete=cascade_str)
    create_constraint("user_role_user_id_fkey", "user_role", "user", ["user_id"], ["id"], ondelete=cascade_str)
    # user_profile
    create_constraint(
        "user_profile_word_list_user_profile_id_fkey",
        "user_profile_word_list",
        "user_profile",
        ["user_profile_id"],
        ["id"],
        ondelete=cascade_str,
    )
    create_constraint("hotkey_user_profile_id_fkey", "hotkey", "user_profile", ["user_profile_id"], ["id"], ondelete=cascade_str)
    create_constraint("user_profile_id_fkey", "user", "user_profile", ["profile_id"], ["id"], ondelete=setnull_str)  # keep
    # word_list
    create_constraint(
        "user_profile_word_list_word_list_id_fkey", "user_profile_word_list", "word_list", ["word_list_id"], ["id"], ondelete=cascade_str
    )
    create_constraint(
        "osint_source_word_list_word_list_id_fkey", "osint_source_word_list", "word_list", ["word_list_id"], ["id"], ondelete=cascade_str
    )
    create_constraint(
        "word_list_category_word_list_id_fkey", "word_list_category", "word_list", ["word_list_id"], ["id"], ondelete=cascade_str
    )
    # word_list_category
    create_constraint(
        "word_list_entry_word_list_category_id_fkey",
        "word_list_entry",
        "word_list_category",
        ["word_list_category_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # role
    create_constraint("user_role_role_id_fkey", "user_role", "role", ["role_id"], ["id"], ondelete=cascade_str)
    # acl_entry
    create_constraint("acl_entry_user_acl_entry_id_fkey", "acl_entry_user", "acl_entry", ["acl_entry_id"], ["id"], ondelete=cascade_str)


def create_constraint(
    constraint_name: str, source_table: str, referent_table: str, local_cols: list[str], remote_cols: list[str], ondelete: str
):
    """Create a foreign key constraint.
    Args:
        constraint_name (str): The name of the constraint.
        source_table (str): The name of the source table.
        referent_table (str): The name of the referent table.
        local_cols (List[str]): The local columns.
        remote_cols (List[str]): The remote columns.
        ondelete (str): The ondelete action.
    """
    op.drop_constraint(constraint_name, source_table, type_="foreignkey")
    op.create_foreign_key(constraint_name, source_table, referent_table, local_cols, remote_cols, ondelete=ondelete)


def upgrade():
    cascade_delete(True)


def downgrade():
    cascade_delete(False)
