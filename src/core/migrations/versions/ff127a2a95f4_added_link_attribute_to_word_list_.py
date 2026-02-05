"""added link attribute to word list category

Revision ID: ff127a2a95f4
Revises: e46b55f712f9
Create Date: 2022-07-01 23:33:11.395700

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ff127a2a95f4"
down_revision = "e46b55f712f9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("word_list_category", sa.Column("link", sa.String(), server_default=None, nullable=True))


def downgrade():
    op.drop_column("word_list_category", "link")
