"""regenerate parameters of bots, collectors, presenters, publishers

Revision ID: 92bdc4caa54c
Revises: 7a45ba122177
Create Date: 2025-02-26 15:09:18.757913

"""

from alembic import op
from sqlalchemy import orm
from migrations.regenerate_params import RegenerateParameters


# revision identifiers, used by Alembic.
revision = "92bdc4caa54c"
down_revision = "7a45ba122177"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    session = orm.Session(bind=conn)
    RegenerateParameters("bots", session)
    RegenerateParameters("collectors", session)
    RegenerateParameters("presenters", session)
    RegenerateParameters("publishers", session)


def downgrade():
    pass
