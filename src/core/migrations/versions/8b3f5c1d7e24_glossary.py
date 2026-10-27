"""The AI translation glossary.

- ``glossary_entry`` - terms to translate consistently, or to keep as written: the instance's
  (no report type) and each report type's own

A core started with the new models before this revision ran creates the table itself
(``db.create_all()``), so every step checks what is already there and the upgrade can run again.

Revision ID: 8b3f5c1d7e24
Revises: 6e1d4b8a2f97
Create Date: 2026-10-24 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "8b3f5c1d7e24"
down_revision = "6e1d4b8a2f97"
branch_labels = None
depends_on = None

TABLE = "glossary_entry"
INDEX = "ix_glossary_entry_report_item_type_id"


def upgrade() -> None:
    """Add the glossary table."""
    inspector = sa.inspect(op.get_bind())
    if TABLE not in set(inspector.get_table_names()):
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("report_item_type_id", sa.Integer(), nullable=True),
            sa.Column("terms", JSONB(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("keep", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("note", sa.String(500), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["report_item_type_id"], ["report_item_type.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if INDEX not in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(TABLE)}:
        op.create_index(INDEX, TABLE, ["report_item_type_id"])


def downgrade() -> None:
    """Drop the glossary table."""
    if TABLE in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table(TABLE)
