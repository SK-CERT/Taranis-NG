"""Add number attribute

Revision ID: aaf3d8b31972
Revises: 0889a25ac61b
Create Date: 2023-03-24 09:56:46.885407

"""

from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base
import sqlalchemy as sa

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "aaf3d8b31972"
down_revision = "0889a25ac61b"
branch_labels = None
depends_on = None


class Attributeaaf3d8b31972(Base):
    __tablename__ = "attribute"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String())
    description = sa.Column(sa.String())
    type = sa.Column(sa.String())
    validator = sa.Column(sa.String())

    def __init__(self, name, description, type, validator):
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.validator = validator


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    session.add(Attributeaaf3d8b31972("Number", "Numeric value", "NUMBER", "NONE"))
    session.commit()


def downgrade():
    # can be complicated when already exists data joined with this record
    pass
