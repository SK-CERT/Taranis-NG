"""Add value description to report item attribute table

Revision ID: 90249a322ae1
Revises: 57d784d699d9
Create Date: 2024-02-25 19:00:13.825003

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "90249a322ae1"
down_revision = "57d784d699d9"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    if "value_description" not in [column["name"] for column in inspector.get_columns("report_item_attribute")]:
        op.add_column("report_item_attribute", sa.Column("value_description", sa.String(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    if "value_description" in [column["name"] for column in inspector.get_columns("report_item_attribute")]:
        op.drop_column("report_item_attribute", "value_description")
