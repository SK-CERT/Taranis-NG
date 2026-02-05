"""Add password field to users

Revision ID: 0889a25ac61b
Revises: 9d3527341ddf
Create Date: 2023-02-23 08:55:28.292917

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base
from werkzeug.security import generate_password_hash

# revision identifiers, used by Alembic.
revision = "0889a25ac61b"
down_revision = "9d3527341ddf"
branch_labels = None
depends_on = None

Base = declarative_base()


class User0889a25ac61b(Base):
    __tablename__ = "user"
    id = sa.Column(sa.INTEGER(), primary_key=True)
    username = sa.Column(sa.VARCHAR())
    password = sa.Column(sa.VARCHAR())


def upgrade():
    op.add_column(
        "user",
        sa.Column("password", sa.VARCHAR(), server_default=sa.text("'empty-hash'::character varying"), autoincrement=False, nullable=False),
    )

    bind = op.get_bind()
    session = orm.Session(bind=bind)
    to_update = session.query(User0889a25ac61b).filter_by(username="user").first()
    if to_update:
        to_update.password = generate_password_hash("user")
        session.add(to_update)
    to_update = session.query(User0889a25ac61b).filter_by(username="user2").first()
    if to_update:
        to_update.password = generate_password_hash("user")
        session.add(to_update)
    to_update = session.query(User0889a25ac61b).filter_by(username="admin").first()
    if to_update:
        to_update.password = generate_password_hash("admin")
        session.add(to_update)
    to_update = session.query(User0889a25ac61b).filter_by(username="customer").first()
    if to_update:
        to_update.password = generate_password_hash("customer")
        session.add(to_update)
    session.commit()


def downgrade():
    op.drop_column("user", "password")
