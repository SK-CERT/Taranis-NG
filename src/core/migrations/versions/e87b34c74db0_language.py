"""add language setting to user profile

Revision ID: e87b34c74db0
Revises: d776f47ce040
Create Date: 2024-01-10 12:58:52.257692

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e87b34c74db0'
down_revision = 'd776f47ce040'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user_profile', sa.Column('language', sa.VARCHAR(length=2)))

def downgrade():
    op.drop_column('user_profile', 'language')
