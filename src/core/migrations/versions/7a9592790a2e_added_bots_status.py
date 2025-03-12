"""Added status columns to bots_node

Revision ID: 7a9592790a2e
Revises: 98fea09779b8
Create Date: 2025-03-11 11:22:44.583578

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a9592790a2e"
down_revision = "98fea09779b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bots_node", sa.Column("created", sa.DateTime()))
    op.add_column("bots_node", sa.Column("last_seen", sa.DateTime()))


def downgrade():
    op.drop_column("bots_node", "created")
    op.drop_column("bots_node", "last_seen")
