"""Stop deleting report type fields when their attribute is deleted.

``attribute_group_item.attribute_id`` was created ``ON DELETE CASCADE`` by
``1c4eed243364``, which makes an attribute look composed of the report type fields
built on it. It is the other way round: the field *references* the attribute. The
cascade meant deleting an attribute silently stripped those fields - and every
report item value stored under them - from every report type using it, or, once
``report_item_attribute`` held rows, failed the whole request with a raw foreign
key violation from a table the admin never named.

The application now refuses to delete an attribute a report type still uses, so
this revision aligns the constraint with that rule: no cascade, and the database
enforces it even for a delete that does not go through the application.

``attribute_enum.attribute_id`` keeps its cascade on purpose - an attribute really
does own its constants.

The constraint name is read from the catalog rather than assumed: this database
has been reshaped by several revisions, and a deployment may carry the name
Postgres generated rather than the one the migrations pass.

Revision ID: b8e5d17c3f90
Revises: c7a1b4e9d203
Create Date: 2026-09-05 15:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

# revision identifiers, used by Alembic.
revision = "b8e5d17c3f90"
down_revision = "c7a1b4e9d203"
branch_labels = None
depends_on = None

TABLE = "attribute_group_item"
COLUMN = "attribute_id"
REFERENCED = "attribute"
FALLBACK_NAME = "attribute_group_item_attribute_id_fkey"


def _foreign_key(connection: Connection) -> tuple[str, str] | None:
    """Return the (name, delete rule) of the constraint under change, or None if it is gone.

    Args:
        connection (Connection): Open database connection.

    Returns:
        tuple[str, str] | None: Constraint name and its confdeltype ("a" = no action, "c" = cascade).
    """
    return connection.execute(
        sa.text(
            """
            SELECT con.conname, con.confdeltype
            FROM pg_constraint con
            JOIN pg_class child ON child.oid = con.conrelid
            JOIN pg_class parent ON parent.oid = con.confrelid
            JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = con.conkey[1]
            WHERE con.contype = 'f'
              AND child.relname = :table
              AND parent.relname = :referenced
              AND att.attname = :column
              AND array_length(con.conkey, 1) = 1
            """,
        ),
        {"table": TABLE, "referenced": REFERENCED, "column": COLUMN},
    ).first()


def _recreate(connection: Connection, *, cascade: bool) -> None:
    """Rebuild the foreign key with or without ON DELETE CASCADE, skipping a no-op.

    Args:
        connection (Connection): Open database connection.
        cascade (bool): Whether the rebuilt constraint should cascade on delete.
    """
    existing = _foreign_key(connection)
    wanted = "c" if cascade else "a"
    if existing is not None:
        name, delete_rule = existing
        if delete_rule == wanted:
            return
        op.drop_constraint(name, TABLE, type_="foreignkey")
    else:
        name = FALLBACK_NAME

    op.create_foreign_key(
        name,
        TABLE,
        REFERENCED,
        [COLUMN],
        ["id"],
        ondelete="CASCADE" if cascade else None,
    )


def upgrade() -> None:
    """Replace the cascading foreign key with a restricting one."""
    _recreate(op.get_bind(), cascade=False)


def downgrade() -> None:
    """Restore the cascading foreign key."""
    _recreate(op.get_bind(), cascade=True)
