"""Add the MULTI_CHOICE attribute type.

Report item attributes gain a type whose constants are rendered as checkboxes, so
an analyst can tick zero, one or several of them. The ticked values live in the
existing ``value`` column, newline-joined, which is why no table changes here.

Two details make this revision less trivial than it looks. First, the Postgres
enum backing ``attribute.type`` is not reliably called ``attributetype``:
``35855286ef98`` created it under that name, but ``f0a4860000ff`` replaced it with
a type literally named ``new_enum``, so the real name has to be read from the
catalog. Second, Postgres refuses to *use* a freshly added enum label in the same
transaction that added it, so the label is committed in an autocommit block before
the example attribute is seeded. Both steps are idempotent, because that early
commit lands before this revision is stamped.

Revision ID: c7a1b4e9d203
Revises: c7a4e2f9b103
Create Date: 2026-09-05 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "c7a1b4e9d203"
down_revision = "c7a4e2f9b103"
branch_labels = None
depends_on = None

ATTRIBUTE_TYPE = "MULTI_CHOICE"
ATTRIBUTE_NAME = "Multiple Choice Example"
ATTRIBUTE_DESCRIPTION = "Example multiple choice attribute; tick zero, one or more options."
CONSTANTS = ("Option A", "Option B", "Option C")


def _enum_type_name(connection: Connection, table: str, column: str) -> str:
    """Read the Postgres enum type actually backing a column, which is not always the model's name."""
    return connection.execute(
        sa.text(
            "SELECT t.typname FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_type t ON t.oid = a.atttypid "
            "WHERE c.relname = :table AND a.attname = :column AND a.attnum > 0 AND NOT a.attisdropped",
        ),
        {"table": table, "column": column},
    ).scalar_one()


def upgrade() -> None:
    """Offer MULTI_CHOICE as an attribute type, with one example attribute to try it on."""
    type_name = _enum_type_name(op.get_bind(), "attribute", "type")

    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE \"{type_name}\" ADD VALUE IF NOT EXISTS '{ATTRIBUTE_TYPE}'")

    # A new transaction starts here, so the committed label may now be used.
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT id FROM attribute WHERE name = :name"), {"name": ATTRIBUTE_NAME}).scalar() is not None:
        return

    validator_type = _enum_type_name(connection, "attribute", "validator")
    # The interpolated names come from pg_catalog, not from user input; enum type names
    # cannot be bound as parameters.
    attribute_id = connection.execute(
        sa.text(
            "INSERT INTO attribute (name, description, type, default_value, validator, validator_parameter) "  # noqa: S608
            f'VALUES (:name, :description, CAST(:type AS "{type_name}"), NULL, CAST(:validator AS "{validator_type}"), NULL) '
            "RETURNING id",
        ),
        {
            "name": ATTRIBUTE_NAME,
            "description": ATTRIBUTE_DESCRIPTION,
            "type": ATTRIBUTE_TYPE,
            "validator": "NONE",
        },
    ).scalar_one()

    for index, value in enumerate(CONSTANTS):
        connection.execute(
            sa.text(
                'INSERT INTO attribute_enum ("index", value, description, imported, attribute_id) '
                "VALUES (:index, :value, :description, false, :attribute_id)",
            ),
            {"index": index, "value": value, "description": "", "attribute_id": attribute_id},
        )


def downgrade() -> None:
    """Remove the example attribute; Postgres cannot drop the MULTI_CHOICE label itself."""
    connection = op.get_bind()
    attribute_id = connection.execute(sa.text("SELECT id FROM attribute WHERE name = :name"), {"name": ATTRIBUTE_NAME}).scalar()
    if attribute_id is None:
        return

    # Leave the attribute alone once an installation has wired it into a report type,
    # rather than breaking the foreign key that points at it.
    in_use = connection.execute(
        sa.text("SELECT 1 FROM attribute_group_item WHERE attribute_id = :id LIMIT 1"),
        {"id": attribute_id},
    ).scalar()
    if in_use is not None:
        return

    connection.execute(sa.text("DELETE FROM attribute_enum WHERE attribute_id = :id"), {"id": attribute_id})
    connection.execute(sa.text("DELETE FROM attribute WHERE id = :id"), {"id": attribute_id})
