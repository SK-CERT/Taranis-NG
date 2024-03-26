"""Add value description to report item attribute table

Revision ID: 90249a322ae1
Revises: f0a4860000ff
Create Date: 2024-02-25 19:00:13.825003

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = "90249a322ae1"
down_revision = "f0a4860000ff"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if "value_description" not in [column["name"] for column in inspector.get_columns("report_item_attribute")]:
        op.add_column("report_item_attribute", sa.Column("value_description", sa.String(), nullable=True))


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if "value_description" in [column["name"] for column in inspector.get_columns("report_item_attribute")]:
        op.drop_column("report_item_attribute", "value_description")
