"""add cascade delete to Parameter, Presenter, Collector, Bot and Publisher tables

Revision ID: 7a45ba122177
Revises: 4cd4c4758a81
Create Date: 2025-02-21 15:20:44.659875

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "7a45ba122177"
down_revision = "4cd4c4758a81"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    delete_previous()
    # parameter -> collector_parameter, bot_parameter, publisher_parameter
    op.create_foreign_key(
        "collector_parameter_parameter_id_fkey",
        "collector_parameter",
        "parameter",
        ["parameter_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key("bot_parameter_parameter_id_fkey", "bot_parameter", "parameter", ["parameter_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(
        "publisher_parameter_parameter_id_fkey",
        "publisher_parameter",
        "parameter",
        ["parameter_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # parameter_value -> osint_source_parameter_value, bot_preset_parameter_value, publisher_preset_parameter_value
    op.create_foreign_key(
        "osint_source_parameter_value_parameter_value_id_fkey",
        "osint_source_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "bot_preset_parameter_value_parameter_value_id_fkey",
        "bot_preset_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "publisher_preset_parameter_value_parameter_value_id_fkey",
        "publisher_preset_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # presenter -> presenter_parameter
    op.create_foreign_key(
        "presenter_parameter_presenter_id_fkey",
        "presenter_parameter",
        "presenter",
        ["presenter_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # collector -> collector_parameter
    op.create_foreign_key(
        "collector_parameter_collector_id_fkey",
        "collector_parameter",
        "collector",
        ["collector_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # bot -> bot_parameter
    op.create_foreign_key("bot_parameter_bot_id_fkey", "bot_parameter", "bot", ["bot_id"], ["id"], ondelete="CASCADE")
    # publisher -> publisher_parameter
    op.create_foreign_key(
        "publisher_parameter_publisher_id_fkey",
        "publisher_parameter",
        "publisher",
        ["publisher_id"],
        ["id"],
        ondelete="CASCADE",
    )

    inspector = inspect(conn)
    columns = [column["name"] for column in inspector.get_columns("parameter")]
    if "default_value" not in columns:
        op.add_column("parameter", sa.Column("default_value", sa.String(), nullable=True))


def downgrade():
    delete_previous()
    # parameter -> collector_parameter, bot_parameter, publisher_parameter
    op.create_foreign_key("collector_parameter_parameter_id_fkey", "collector_parameter", "parameter", ["parameter_id"], ["id"])
    op.create_foreign_key("bot_parameter_parameter_id_fkey", "bot_parameter", "parameter", ["parameter_id"], ["id"])
    op.create_foreign_key("publisher_parameter_parameter_id_fkey", "publisher_parameter", "parameter", ["parameter_id"], ["id"])
    # parameter_value -> osint_source_parameter_value, bot_preset_parameter_value, publisher_preset_parameter_value
    op.create_foreign_key(
        "osint_source_parameter_value_parameter_value_id_fkey",
        "osint_source_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
    )
    op.create_foreign_key(
        "bot_preset_parameter_value_parameter_value_id_fkey",
        "bot_preset_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
    )
    op.create_foreign_key(
        "publisher_preset_parameter_value_parameter_value_id_fkey",
        "publisher_preset_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
    )
    # presenter -> presenter_parameter
    op.create_foreign_key("presenter_parameter_presenter_id_fkey", "presenter_parameter", "presenter", ["presenter_id"], ["id"])
    # collector -> collector_parameter
    op.create_foreign_key("collector_parameter_collector_id_fkey", "collector_parameter", "collector", ["collector_id"], ["id"])
    # bot -> bot_parameter
    op.create_foreign_key("bot_parameter_bot_id_fkey", "bot_parameter", "bot", ["bot_id"], ["id"])
    # publisher -> publisher_parameter
    op.create_foreign_key("publisher_parameter_publisher_id_fkey", "publisher_parameter", "publisher", ["publisher_id"], ["id"])


def delete_previous():
    print("Deleting previous constraints...", flush=True)
    op.drop_constraint("collector_parameter_parameter_id_fkey", "collector_parameter", type_="foreignkey")
    op.drop_constraint("bot_parameter_parameter_id_fkey", "bot_parameter", type_="foreignkey")
    op.drop_constraint("publisher_parameter_parameter_id_fkey", "publisher_parameter", type_="foreignkey")

    op.drop_constraint("osint_source_parameter_value_parameter_value_id_fkey", "osint_source_parameter_value", type_="foreignkey")
    op.drop_constraint("bot_preset_parameter_value_parameter_value_id_fkey", "bot_preset_parameter_value", type_="foreignkey")
    op.drop_constraint("publisher_preset_parameter_value_parameter_value_id_fkey", "publisher_preset_parameter_value", type_="foreignkey")

    op.drop_constraint("presenter_parameter_presenter_id_fkey", "presenter_parameter", type_="foreignkey")
    op.drop_constraint("collector_parameter_collector_id_fkey", "collector_parameter", type_="foreignkey")
    op.drop_constraint("bot_parameter_bot_id_fkey", "bot_parameter", type_="foreignkey")
    op.drop_constraint("publisher_parameter_publisher_id_fkey", "publisher_parameter", type_="foreignkey")
    print("Adding new constraints...", flush=True)
