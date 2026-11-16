"""When a product was first published: ``product.published_at``.

A product had only its creation time and the time of its last save; the public web showed the
creation as the day it was published, and its RSS feed gave no date at all. Now core records the
moment a product first enters the published state. The public web shows it, orders by it, and
gives it as the RSS ``pubDate`` and the Atom ``published``.

Products published before this revision get their creation time, the date their page has shown
so far. Other products get theirs when they are published.

The column may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh
database from the models. Then nothing is filled in, so a time already recorded stays.

Downgrade drops the column.

Revision ID: 5c915192b607
Revises: 5e5fd7e294ca
Create Date: 2026-11-13 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5c915192b607"
down_revision = "5e5fd7e294ca"
branch_labels = None
depends_on = None

TABLE = "product"
COLUMN = "published_at"

# The products published now; "published" is StateEnum.PUBLISHED, the state's display name.
BACKFILL = """
UPDATE product
SET published_at = created
WHERE published_at IS NULL AND state_id IN (SELECT id FROM state WHERE display_name = 'published')
"""


def _has_column() -> bool:
    return COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    """Add product.published_at and give the published products their creation time."""
    if _has_column():
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.DateTime(), nullable=True))
    op.execute(sa.text(BACKFILL))


def downgrade() -> None:
    """Drop product.published_at."""
    if _has_column():
        op.drop_column(TABLE, COLUMN)
