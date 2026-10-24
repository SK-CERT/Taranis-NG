"""Tags for reports and products, with the built-in translation status tags.

- ``tag`` - tags admins define, and the built-in ones (``system_key`` set)
- ``tag_entity_type`` - which tags reports and products use, in which order (Tag Workflow)
- ``report_item_tag`` / ``product_tag`` - the admin tags people put on an item

The built-in tags show an item's translation status per language and whether its language is
set. Taranis works them out when an item is shown, so they are never stored on an item. This
revision adds them, linked to reports and products and active; their names are keys the GUI
translates.

A core started with the new models before this revision ran creates the tables itself
(``db.create_all()``), so every step checks what is already there and the upgrade can run again.

Revision ID: 6e1d4b8a2f97
Revises: 4bc3bad77008
Create Date: 2026-10-24 12:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e1d4b8a2f97"
down_revision = "4bc3bad77008"
branch_labels = None
depends_on = None

ENTITY_TYPES = ("report_item", "product")

# The built-in tags: key, colour, icon. The key is also the name the GUI translates.
SYSTEM_TAGS = (
    ("translation_missing", "#9E9E9E", "mdi-translate-off"),
    ("translation_partial", "#1E88E5", "mdi-circle-half-full"),
    ("translation_outdated", "#FB8C00", "mdi-alert-circle-outline"),
    ("translation_ai", "#8E24AA", "mdi-robot-outline"),
    ("translation_done", "#2E7D32", "mdi-check-circle-outline"),
    ("language_not_set", "#757575", "mdi-help-circle-outline"),
)
# After the admin tags, which start at 0.
SYSTEM_SORT_ORDER = 100


def _assignment_table(name: str, item_table: str, item_column: str) -> None:
    op.create_table(
        name,
        sa.Column(item_column, sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint([item_column], [f"{item_table}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint(item_column, "tag_id"),
    )


def _create_tables() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "tag" not in tables:
        op.create_table(
            "tag",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("display_name", sa.String(100), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("color", sa.String(7), nullable=True),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("system_key", sa.String(50), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("system_key"),
        )
    if "tag_entity_type" not in tables:
        op.create_table(
            "tag_entity_type",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.Column("entity_type", sa.String(20), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tag_id", "entity_type", name="uq_tag_entity_type"),
        )
    if "report_item_tag" not in tables:
        _assignment_table("report_item_tag", "report_item", "report_item_id")
    if "product_tag" not in tables:
        _assignment_table("product_tag", "product", "product_id")


def _seed_system_tags() -> None:
    """Add the built-in tags that are missing, each linked to reports and products."""
    bind = op.get_bind()
    tag = sa.table(
        "tag",
        sa.column("id", sa.Integer),
        sa.column("display_name", sa.String),
        sa.column("color", sa.String),
        sa.column("icon", sa.String),
        sa.column("system_key", sa.String),
        sa.column("updated_by", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    link = sa.table(
        "tag_entity_type",
        sa.column("tag_id", sa.Integer),
        sa.column("entity_type", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("updated_by", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now()  # noqa: DTZ005 - the other workflow tables store naive local times
    for order, (key, color, icon) in enumerate(SYSTEM_TAGS):
        tag_id = bind.execute(sa.select(tag.c.id).where(tag.c.system_key == key)).scalar()
        if tag_id is None:
            tag_id = bind.execute(
                tag.insert()
                .values(display_name=key, color=color, icon=icon, system_key=key, updated_by="system-migration", updated_at=now)
                .returning(tag.c.id),
            ).scalar_one()
        for entity_type in ENTITY_TYPES:
            existing = sa.select(sa.func.count()).select_from(link).where(link.c.tag_id == tag_id, link.c.entity_type == entity_type)
            linked = bind.execute(existing).scalar()
            if not linked:
                bind.execute(
                    link.insert().values(
                        tag_id=tag_id,
                        entity_type=entity_type,
                        is_active=True,
                        sort_order=SYSTEM_SORT_ORDER + order,
                        updated_by="system-migration",
                        updated_at=now,
                    ),
                )


def upgrade() -> None:
    """Add the tag tables and the built-in tags."""
    _create_tables()
    _seed_system_tags()


def downgrade() -> None:
    """Drop the tag tables."""
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("product_tag", "report_item_tag", "tag_entity_type", "tag"):
        if table in tables:
            op.drop_table(table)
