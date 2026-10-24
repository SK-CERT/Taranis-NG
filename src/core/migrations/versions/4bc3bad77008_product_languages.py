"""Content languages for constants, products and product types.

- ``attribute_enum.translations`` - language variants of choice constants
- ``product.language`` - the language a product is written in
- ``product_translation`` - its title in other languages
- ``product_type.language`` / ``language_templates`` - the language of the default templates,
  and template paths per language

Existing products and product types get no language: nothing reliable tells which one they are
in, so it stays "not set" until somebody chooses it, and they render exactly as before.

A core started with the new models before this revision ran creates the new table itself
(``db.create_all()``), so every step checks what is already there and the upgrade can run again.

Revision ID: 4bc3bad77008
Revises: d0ce8c7edcd9
Create Date: 2026-10-23 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "4bc3bad77008"
down_revision = "d0ce8c7edcd9"
branch_labels = None
depends_on = None

PRODUCT_TABLE = "product_translation"
PRODUCT_INDEX = "ix_product_translation_product_id"


def _columns() -> dict[str, list[sa.Column]]:
    """The columns this revision adds, per existing table."""
    return {
        "attribute_enum": [
            sa.Column("translations", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        ],
        "product": [
            sa.Column("language", sa.String(8), nullable=True),
        ],
        "product_type": [
            sa.Column("language", sa.String(8), nullable=True),
            sa.Column("language_templates", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        ],
    }


def _add_columns() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, columns in _columns().items():
        present = {column["name"] for column in inspector.get_columns(table)}
        for column in columns:
            if column.name not in present:
                op.add_column(table, column)


def _create_tables() -> None:
    if PRODUCT_TABLE not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table(
            PRODUCT_TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("language", sa.String(8), nullable=False),
            sa.Column("value", sa.String(), nullable=False),
            sa.Column("source_hash", sa.String(64), nullable=False),
            sa.Column("origin", sa.String(8), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("last_updated", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("field", sa.String(16), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("product_id", "language", "field", name="uq_product_translation"),
        )
    if PRODUCT_INDEX not in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(PRODUCT_TABLE)}:
        op.create_index(PRODUCT_INDEX, PRODUCT_TABLE, ["product_id"])


def upgrade() -> None:
    """Add the language columns and the product translation table."""
    _add_columns()
    _create_tables()


def downgrade() -> None:
    """Drop the product translation table and the language columns."""
    inspector = sa.inspect(op.get_bind())
    if PRODUCT_TABLE in set(inspector.get_table_names()):
        op.drop_table(PRODUCT_TABLE)
    for table, columns in _columns().items():
        present = {column["name"] for column in inspector.get_columns(table)}
        for column in columns:
            if column.name in present:
                op.drop_column(table, column.name)
