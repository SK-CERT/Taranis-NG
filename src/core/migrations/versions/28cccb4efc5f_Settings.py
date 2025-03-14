"""add Settings functionality

Revision ID: 28cccb4efc5f
Revises: 7a9592790a2e
Create Date: 2025-02-21 13:04:59.332013

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "28cccb4efc5f"
down_revision = "7a9592790a2e"
branch_labels = None
depends_on = None


class Permission_S1(Base):
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
        perm = session.query(Permission_S1).filter_by(id=id).first()
        if not perm:
            session.add(Permission_S1(id, name, description))

    @staticmethod
    def delete(session, id):
        perm = session.query(Permission_S1).filter_by(id=id).first()
        if perm:
            session.delete(perm)
            print(f"Permission {perm.id} deleted...", flush=True)


class Role_S1(Base):
    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(Permission_S1, secondary="role_permission")


class RolePermission_S1(Base):
    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


class Setting_S1(Base):
    __tablename__ = "settings"
    id = sa.Column(sa.Integer, primary_key=True)
    key = sa.Column(sa.String(40), unique=True, nullable=False)
    type = sa.Column(sa.String(1), unique=True, nullable=False)
    value = sa.Column(sa.String(), nullable=False)
    default_val = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)

    def __init__(self, key, type, value, description):
        self.id = None
        self.key = key
        self.type = type
        self.value = value
        self.default_val = value
        self.description = description

    @staticmethod
    def add(session, key, type, value, description):
        setting = session.query(Setting_S1).filter_by(key=key).first()
        if not setting:
            session.add(Setting_S1(key, type, value, description))


def upgrade():
    conn = op.get_bind()
    session = orm.Session(bind=conn)

    inspector = inspect(conn)
    if "settings" in inspector.get_table_names():
        return

    op.create_table(
        "settings",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("key", sa.VARCHAR(length=40), autoincrement=False, nullable=False),
        sa.Column("value", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("type", sa.VARCHAR(length=1), autoincrement=False, nullable=False),
        sa.Column("default_val", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("updated_by", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="settings_pkey"),
        sa.UniqueConstraint("key", name="settings_key_key"),
    )
    Permission_S1.add(session, "CONFIG_SETTINGS_ACCESS", "Config settings access", "Access to settings configuration")
    Permission_S1.add(session, "CONFIG_SETTINGS_CREATE", "Config setting create", "Create setting configuration")
    Permission_S1.add(session, "CONFIG_SETTINGS_UPDATE", "Config setting update", "Update setting configuration")
    Permission_S1.add(session, "CONFIG_SETTINGS_DELETE", "Config setting delete", "Delete setting configuration")
    Setting_S1.add(session, "DATE_FORMAT", "S", "dd.MM.yyyy", "Date format")
    Setting_S1.add(session, "TIME_FORMAT", "S", "HH:mm", "Time format")
    Setting_S1.add(session, "REPORT_SELECTOR_READ_ONLY", "B", "true", "Open the Report Item selector in Read-Only mode")
    session.commit()

    role = session.query(Role_S1).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(Permission_S1).all()
        session.add(role)
        session.commit()

    delete_previous()
    # role_permission
    op.create_foreign_key(
        "role_permission_permission_id_fkey", "role_permission", "permission", ["permission_id"], ["id"], ondelete="CASCADE"
    )
    # user_permission
    op.create_foreign_key(
        "user_permission_permission_id_fkey", "user_permission", "permission", ["permission_id"], ["id"], ondelete="CASCADE"
    )


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    print("deleting table 'settings'...", flush=True)
    op.drop_table("settings")

    print("deleting 'settings' permissions...", flush=True)
    # this delete also role_permission, user_permission records
    Permission_S1.delete(session, "CONFIG_SETTINGS_ACCESS")
    Permission_S1.delete(session, "CONFIG_SETTINGS_CREATE")
    Permission_S1.delete(session, "CONFIG_SETTINGS_UPDATE")
    Permission_S1.delete(session, "CONFIG_SETTINGS_DELETE")
    session.commit()

    delete_previous()
    print("creating old reference rules...", flush=True)
    # role_permission
    op.create_foreign_key("role_permission_permission_id_fkey", "role_permission", "permission", ["permission_id"], ["id"])
    # user_permission
    op.create_foreign_key("user_permission_permission_id_fkey", "user_permission", "permission", ["permission_id"], ["id"])


def delete_previous():
    print("deleting previous reference rules...", flush=True)
    # role_permission
    op.drop_constraint("role_permission_permission_id_fkey", "role_permission", type_="foreignkey")
    # user_permission
    op.drop_constraint("user_permission_permission_id_fkey", "user_permission", type_="foreignkey")
