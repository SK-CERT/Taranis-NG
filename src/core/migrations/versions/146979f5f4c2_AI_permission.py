"""AI permission

Revision ID: 146979f5f4c2
Revises: ba4956806c68
Create Date: 2025-07-22 17:04:29.412888

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "146979f5f4c2"
down_revision = "ba4956806c68"
branch_labels = None
depends_on = None


class Permission_AI(Base):
    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description

    @staticmethod
    def add(session, id, name, description):
        perm = session.query(Permission_AI).filter_by(id=id).first()
        if not perm:
            session.add(Permission_AI(id, name, description))

    @staticmethod
    def delete(session, id):
        perm = session.query(Permission_AI).filter_by(id=id).first()
        if perm:
            session.delete(perm)
            print(f"Permission {perm.id} deleted...", flush=True)


class Role_AI(Base):
    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(Permission_AI, secondary="role_permission")


class RolePermission_AI(Base):
    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


def upgrade():
    conn = op.get_bind()
    session = orm.Session(bind=conn)

    Permission_AI.add(session, "CONFIG_AI_ACCESS", "Config AI access", "Access to AI configuration")
    Permission_AI.add(session, "CONFIG_AI_CREATE", "Config AI create", "Create AI configuration")
    Permission_AI.add(session, "CONFIG_AI_UPDATE", "Config AI update", "Update AI configuration")
    Permission_AI.add(session, "CONFIG_AI_DELETE", "Config AI delete", "Delete AI configuration")
    session.commit()

    role = session.query(Role_AI).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(Permission_AI).all()
        session.add(role)
        session.commit()


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    print("deleting 'AI' permissions...", flush=True)
    # this delete also role_permission, user_permission records
    Permission_AI.delete(session, "CONFIG_AI_ACCESS")
    Permission_AI.delete(session, "CONFIG_AI_CREATE")
    Permission_AI.delete(session, "CONFIG_AI_UPDATE")
    Permission_AI.delete(session, "CONFIG_AI_DELETE")
    session.commit()
