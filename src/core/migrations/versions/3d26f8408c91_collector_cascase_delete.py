"""Collector cascade delete.

Revision ID: 3d26f8408c91
Revises: fdc6bba17c9b
Create Date: 2025-11-10 10:45:32.337618

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "3d26f8408c91"
down_revision = "fdc6bba17c9b"
branch_labels = None
depends_on = None


def cascade_delete(enable: bool) -> None:
    """Enable or disable cascade delete on foreign key constraints.

    Args:
        enable (bool): Whether to enable or disable cascade delete.
    """
    cascade_str = "CASCADE" if enable else None
    # collector_node -> collector
    create_constraint(
        "collector_node_id_fkey",
        "collector",
        "collectors_node",
        ["node_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # collector -> osint_source (osint_source_collector_id_fkey) keep on user to delete manually (sensitive data)
    # bots_node -> bot
    create_constraint(
        "bot_node_id_fkey",
        "bot",
        "bots_node",
        ["node_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # bot -> bot_preset
    create_constraint(
        "bot_preset_bot_id_fkey",
        "bot_preset",
        "bot",
        ["bot_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # presenter_node -> presenter
    create_constraint(
        "presenter_node_id_fkey",
        "presenter",
        "presenters_node",
        ["node_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # presenter -> product_type
    create_constraint(
        "product_type_presenter_id_fkey",
        "product_type",
        "presenter",
        ["presenter_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # publisher_node -> publisher
    create_constraint(
        "publisher_node_id_fkey",
        "publisher",
        "publishers_node",
        ["node_id"],
        ["id"],
        ondelete=cascade_str,
    )
    # publisher -> publisher_preset
    create_constraint(
        "publisher_preset_publisher_id_fkey",
        "publisher_preset",
        "publisher",
        ["publisher_id"],
        ["id"],
        ondelete=cascade_str,
    )


def create_constraint(
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    ondelete: str,
) -> None:
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


def upgrade() -> None:
    """Perform upgrade."""
    cascade_delete(enable=True)


def downgrade() -> None:
    """Perform downgrade."""
    cascade_delete(enable=False)
