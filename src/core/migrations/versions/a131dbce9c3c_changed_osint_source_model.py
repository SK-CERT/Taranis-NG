"""changed osint source model

Revision ID: a131dbce9c3c
Revises: 610dfbea8075
Create Date: 2021-11-08 20:37:04.320911

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a131dbce9c3c"
down_revision = "610dfbea8075"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("osint_source", "screenshot")
    op.add_column("osint_source", sa.Column("last_data", sa.JSON()))


def downgrade():
    op.drop_column("osint_source", "last_data")
    op.add_column("osint_source", sa.Column("screenshot", sa.LargeBinary()))
