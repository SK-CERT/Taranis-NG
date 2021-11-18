"""fix created field being null

Revision ID: 7607d7d98f71
Revises: 74e214f93e88
Create Date: 2021-11-18 13:17:43.606541

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import JSON

Base = declarative_base()

class CollectorsNodeRev7607d7d98f71(Base):
    __tablename__ = 'collectors_node'
    id = sa.Column(sa.String(64), primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())
    api_url = sa.Column(sa.String(), nullable=False)
    api_key = sa.Column(sa.String(), nullable=False)
    created = sa.Column(sa.DateTime, default=datetime.now)
    last_seen = sa.Column(sa.DateTime, default=datetime.now)

class OSINTSourceRev7607d7d98f71(Base):
    __tablename__ = 'osint_source'
    id = sa.Column(sa.String(64), primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String())
    collector_id = sa.Column(sa.String, sa.ForeignKey('collector.id'))
    modified = sa.Column(sa.DateTime, default=datetime.now)
    last_collected = sa.Column(sa.DateTime, default=None)
    last_attempted = sa.Column(sa.DateTime, default=None)
    state = sa.Column(sa.SmallInteger, default=0)
    last_error_message = sa.Column(sa.String, default=None)
    last_data = sa.Column(JSON, default=None)

# revision identifiers, used by Alembic.
revision = '7607d7d98f71'
down_revision = '74e214f93e88'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    to_update = session.query(CollectorsNodeRev7607d7d98f71).filter_by(created=None).all()
    for node in to_update:
        node.created = datetime.now()
        node.last_seen = datetime.now()
        session.add(node)
    session.commit()

    to_update = session.query(OSINTSourceRev7607d7d98f71).filter_by(modified=None).all()
    for source in to_update:
        source.modified = datetime.now()
        session.add(source)
    session.commit()


def downgrade():
    pass
