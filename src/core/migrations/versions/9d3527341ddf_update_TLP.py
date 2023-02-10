"""TLC WHITE to CLEAR

Revision ID: 9d3527341ddf
Revises: c2c78cb93a3e
Create Date: 2023-02-10 11:01:49.783544

"""
from alembic import op
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = '9d3527341ddf'
down_revision = 'c2c78cb93a3e'
branch_labels = None
depends_on = None


class ReportItemAttribute9d3527341ddf(Base):
    __tablename__ = 'report_item_attribute'
    id = sa.Column(sa.String(64), primary_key=True)
    value = sa.Column(sa.String())


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    to_update = session.query(ReportItemAttribute9d3527341ddf).filter_by(value="WHITE").all()
    for rec in to_update:
        rec.value = "CLEAR"
        session.add(rec)
    session.commit()


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    to_update = session.query(ReportItemAttribute9d3527341ddf).filter_by(value="CLEAR").all()
    for rec in to_update:
        rec.value = "WHITE"
        session.add(rec)
    session.commit()
