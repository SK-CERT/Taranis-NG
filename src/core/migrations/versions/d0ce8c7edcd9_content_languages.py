"""Report content languages: variants per report type, translations, and an AI provider TLP limit.

- ``report_item_type.languages`` - the languages its reports are translated into
- ``report_item_type.translation_ai_provider_id`` - the AI provider that translates them
- ``report_item_type.label_language`` and ``translations`` on the type, its groups and items -
  the language the labels are written in, and their variants
- ``attribute_group_item.translate`` - reports translate this field (text types only)
- ``report_item.language`` - the language a report is written in
- ``report_item_translation`` / ``report_item_attribute_translation`` - translated names and values
- ``ai_provider.max_tlp`` - the highest TLP of a report whose text may go to the provider

Existing reports get no language: nothing reliable tells which one they are written in, so it
stays "not set" until somebody chooses it, and they render exactly as before. Settings are not
touched.

A core started with the new models before this revision ran creates the two new tables itself
(``db.create_all()``), so every step checks what is already there and the upgrade can run again.

Revision ID: d0ce8c7edcd9
Revises: 1f928d40433c
Create Date: 2026-10-23 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "d0ce8c7edcd9"
down_revision = "1f928d40433c"
branch_labels = None
depends_on = None

TITLE_TABLE = "report_item_translation"
ATTRIBUTE_TABLE = "report_item_attribute_translation"
TITLE_INDEX = "ix_report_item_translation_report_item_id"
ATTRIBUTE_INDEX = "ix_report_item_attribute_translation_report_item_attribute_id"
PROVIDER_FK = "fk_report_item_type_translation_ai_provider_id"


def _columns() -> dict[str, list[sa.Column]]:
    """The columns this revision adds, per existing table."""
    return {
        "report_item_type": [
            sa.Column("languages", JSONB(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("translation_ai_provider_id", sa.Integer(), nullable=True),
            sa.Column("label_language", sa.String(8), nullable=True),
            sa.Column("translations", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        ],
        "attribute_group": [
            sa.Column("translations", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        ],
        "attribute_group_item": [
            sa.Column("translate", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("translations", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        ],
        "report_item": [
            sa.Column("language", sa.String(8), nullable=True),
        ],
        "ai_provider": [
            sa.Column("max_tlp", sa.String(16), nullable=True),
        ],
    }


def _translation_columns() -> list[sa.Column]:
    """The columns both translation tables share (model.translation.TranslationMixin)."""
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("origin", sa.String(8), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    ]


def _add_columns() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, columns in _columns().items():
        present = {column["name"] for column in inspector.get_columns(table)}
        for column in columns:
            if column.name not in present:
                op.add_column(table, column)
    foreign_keys = {key["name"] for key in inspector.get_foreign_keys("report_item_type")}
    if PROVIDER_FK not in foreign_keys:
        op.create_foreign_key(PROVIDER_FK, "report_item_type", "ai_provider", ["translation_ai_provider_id"], ["id"], ondelete="SET NULL")


def _create_tables() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if TITLE_TABLE not in tables:
        op.create_table(
            TITLE_TABLE,
            *_translation_columns(),
            sa.Column("report_item_id", sa.Integer(), nullable=False),
            sa.Column("field", sa.String(16), nullable=False),
            sa.ForeignKeyConstraint(["report_item_id"], ["report_item.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("report_item_id", "language", "field", name="uq_report_item_translation"),
        )
    if ATTRIBUTE_TABLE not in tables:
        op.create_table(
            ATTRIBUTE_TABLE,
            *_translation_columns(),
            sa.Column("report_item_attribute_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["report_item_attribute_id"], ["report_item_attribute.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("report_item_attribute_id", "language", name="uq_report_item_attribute_translation"),
        )
    inspector = sa.inspect(op.get_bind())
    if TITLE_INDEX not in {index["name"] for index in inspector.get_indexes(TITLE_TABLE)}:
        op.create_index(TITLE_INDEX, TITLE_TABLE, ["report_item_id"])
    if ATTRIBUTE_INDEX not in {index["name"] for index in inspector.get_indexes(ATTRIBUTE_TABLE)}:
        op.create_index(ATTRIBUTE_INDEX, ATTRIBUTE_TABLE, ["report_item_attribute_id"])


def upgrade() -> None:
    """Add the language columns and the translation tables."""
    _add_columns()
    _create_tables()


def downgrade() -> None:
    """Drop the translation tables and the language columns."""
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table in (ATTRIBUTE_TABLE, TITLE_TABLE):
        if table in tables:
            op.drop_table(table)
    if PROVIDER_FK in {key["name"] for key in inspector.get_foreign_keys("report_item_type")}:
        op.drop_constraint(PROVIDER_FK, "report_item_type", type_="foreignkey")
    for table, columns in _columns().items():
        present = {column["name"] for column in inspector.get_columns(table)}
        for column in columns:
            if column.name in present:
                op.drop_column(table, column.name)
