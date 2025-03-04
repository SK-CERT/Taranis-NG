"""replace ACCESS_KEY with API_KEY

Revision ID: eac704e8dea8
Revises: 92bdc4caa54c
Create Date: 2025-02-27 19:22:30.624931

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "eac704e8dea8"
down_revision = "92bdc4caa54c"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("remote_access", "access_key", new_column_name="api_key")
    op.alter_column("remote_node", "access_key", new_column_name="api_key")


def downgrade():
    op.alter_column("remote_access", "api_key", new_column_name="access_key")
    op.alter_column("remote_node", "api_key", new_column_name="access_key")
