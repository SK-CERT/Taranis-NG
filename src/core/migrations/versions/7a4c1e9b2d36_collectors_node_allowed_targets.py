"""Internal targets a collectors node may fetch: ``collectors_node.allowed_private_targets``.

Collectors fetch sources from public addresses only, so that a source cannot be aimed at an
internal service (the cloud metadata address, core, the database) and read back as news items.
Sources that do live on an internal network are named per collectors node, in its dialog under
Configuration: host names, domains, addresses and networks. Core hands the list to the node with
its sources.

Every node starts with an empty list: nothing internal is fetched until somebody allows it.

The column may exist already: ``create_app()`` runs ``db.create_all()``, which builds a fresh
database from the models.

Downgrade drops the column.

Revision ID: 7a4c1e9b2d36
Revises: 5c915192b607
Create Date: 2026-11-19 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a4c1e9b2d36"
down_revision = "5c915192b607"
branch_labels = None
depends_on = None

TABLE = "collectors_node"
COLUMN = "allowed_private_targets"


def _has_column() -> bool:
    return COLUMN in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    """Add collectors_node.allowed_private_targets, empty for every node."""
    if _has_column():
        return
    op.add_column(TABLE, sa.Column(COLUMN, sa.String(), nullable=False, server_default=""))


def downgrade() -> None:
    """Drop collectors_node.allowed_private_targets."""
    if _has_column():
        op.drop_column(TABLE, COLUMN)
