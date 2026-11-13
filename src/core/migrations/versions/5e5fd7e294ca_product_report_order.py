"""A product's reports have an order: ``product_report_item.position``.

The reports of a product used to come in whatever order the database returned their link rows,
and the public web, the presenters and the citation numbers all follow that order. Now each row
has its place in the product, from 0, which the product editor sets.

Existing rows get the order a product showed until now: by report id. Loading one product's
reports (public web, presenters, the product editor) read the link table through its primary key
index, (product_id, report_item_id), so that is the order readers saw.

The column may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh
database from the models. Then nothing is renumbered, so an order already stored stays.

Downgrade drops the column.

Revision ID: 5e5fd7e294ca
Revises: 4b8e6d2a9c71
Create Date: 2026-11-13 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5e5fd7e294ca"
down_revision = "4b8e6d2a9c71"
branch_labels = None
depends_on = None

TABLE = "product_report_item"
COLUMN = "position"

# Each product's rows numbered from 0 by report id.
BACKFILL = """
UPDATE product_report_item AS link
SET position = ordered.position
FROM (
    SELECT product_id, report_item_id, row_number() OVER (PARTITION BY product_id ORDER BY report_item_id) - 1 AS position
    FROM product_report_item
) AS ordered
WHERE link.product_id = ordered.product_id AND link.report_item_id = ordered.report_item_id
"""


def _has_column() -> bool:
    return COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    """Add product_report_item.position and number the existing rows."""
    if _has_column():
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.Integer(), nullable=False, server_default="0"))
    op.execute(sa.text(BACKFILL))


def downgrade() -> None:
    """Drop product_report_item.position."""
    if _has_column():
        op.drop_column(TABLE, COLUMN)
