"""Add new data_provider table.

Revision ID: 6a7431435320
Revises: a07f4e5b5943
Create Date: 2025-08-06 13:41:18.166310

"""

import logging
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, orm

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision = "6a7431435320"
down_revision = "a07f4e5b5943"
branch_labels = None
depends_on = None

Base = orm.declarative_base()

default_user_agent = ""
default_updated_by = "system-migration"


class DataProvider(Base):
    """Data provider table."""

    __tablename__ = "data_provider"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    api_type = sa.Column(sa.String(), nullable=False)
    api_url = sa.Column(sa.String(), nullable=False)
    api_key = sa.Column(sa.String())
    user_agent = sa.Column(sa.String())
    web_url = sa.Column(sa.String())
    updated_by = sa.Column(sa.String())
    updated_at = sa.Column(sa.DateTime())


class PermissionDataProvider(Base):
    """Permission table for data providers."""

    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(
        self,
        id: str,  # noqa: A002
        name: str,
        description: str,
    ) -> None:
        """Initialize permission."""
        self.id = id
        self.name = name
        self.description = description

    @staticmethod
    def add(session: orm.Session, permission_id: str, name: str, description: str) -> None:
        """Add permission if does not exists."""
        perm = session.query(PermissionDataProvider).filter_by(id=permission_id).first()
        if not perm:
            session.add(PermissionDataProvider(permission_id, name, description))

    @staticmethod
    def delete(session: orm.Session, permission_id: str) -> None:
        """Delete permission by id."""
        perm = session.query(PermissionDataProvider).filter_by(id=permission_id).first()
        if perm:
            session.delete(perm)
            logger.info(f"Permission {perm.id} deleted...")


class RoleDataProvider(Base):
    """Role table for data providers."""

    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(PermissionDataProvider, secondary="role_permission")


class RolePermissionDataProvider(Base):
    """Association table between role and permission for data providers."""

    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


def upgrade() -> None:
    """Create data_provider with constraints."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if "data_provider" not in inspector.get_table_names():
        op.create_table(
            "data_provider",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("api_type", sa.String(), nullable=False, unique=True),
            sa.Column("api_url", sa.String(), nullable=False),
            sa.Column("api_key", sa.String()),
            sa.Column("user_agent", sa.String(), server_default=default_user_agent),
            sa.Column("web_url", sa.String()),
            sa.Column("updated_by", sa.String()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id", name="data_provider_pkey"),
        )

    session = orm.Session(bind=bind)

    if not session.query(DataProvider).all():
        session.add(
            DataProvider(
                name="ENISA EUVD",
                api_type="EUVD",
                api_url="https://euvdservices.enisa.europa.eu/api/",
                api_key="",
                user_agent=default_user_agent,
                updated_at=datetime.now(tz=UTC),
                updated_by=default_updated_by,
                web_url="https://euvd.enisa.europa.eu/vulnerability/",
            ),
        )
        session.add(
            DataProvider(
                name="NVD CVE",
                api_type="CVE",
                api_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
                api_key="",
                user_agent=default_user_agent,
                updated_at=datetime.now(tz=UTC),
                updated_by=default_updated_by,
                web_url="https://nvd.nist.gov/vuln/detail/",
            ),
        )
        session.add(
            DataProvider(
                name="NVD CPE",
                api_type="CPE",
                api_url="https://services.nvd.nist.gov/rest/json/cpes/2.0",
                api_key="",
                user_agent=default_user_agent,
                updated_at=datetime.now(tz=UTC),
                updated_by=default_updated_by,
                web_url="https://nvd.nist.gov/products/cpe/detail/",
            ),
        )
        session.add(
            DataProvider(
                name="MITRE CWE",
                api_type="CWE",
                api_url="https://cwe-api.mitre.org/api/v1/",
                api_key="",
                user_agent=default_user_agent,
                updated_at=datetime.now(tz=UTC),
                updated_by=default_updated_by,
                web_url="https://cwe.mitre.org/data/definitions/",
            ),
        )
        session.add(
            DataProvider(
                name="FIRST EPSS",
                api_type="EPSS",
                api_url="https://api.first.org/data/v1/epss",
                api_key="",
                user_agent=default_user_agent,
                updated_at=datetime.now(tz=UTC),
                updated_by=default_updated_by,
                web_url="",
            ),
        )

        session.commit()

    PermissionDataProvider.add(session, "CONFIG_DATA_PROVIDER_ACCESS", "Config data provider access", "Access to data provider configuration")
    PermissionDataProvider.add(session, "CONFIG_DATA_PROVIDER_CREATE", "Config data provider create", "Create data provider configuration")
    PermissionDataProvider.add(session, "CONFIG_DATA_PROVIDER_UPDATE", "Config data provider update", "Update data provider configuration")
    PermissionDataProvider.add(session, "CONFIG_DATA_PROVIDER_DELETE", "Config data provider delete", "Delete data provider configuration")
    session.commit()

    role = session.query(RoleDataProvider).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(PermissionDataProvider).all()
        session.add(role)
        session.commit()


def downgrade() -> None:
    """Drop all created tables and permissions."""
    logger.info("deleting table 'data_provider'...")
    op.drop_table("data_provider")

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    logger.info("deleting 'Data Provider' permissions...")
    # this delete also role_permission, user_permission records
    PermissionDataProvider.delete(session, "CONFIG_DATA_PROVIDER_ACCESS")
    PermissionDataProvider.delete(session, "CONFIG_DATA_PROVIDER_CREATE")
    PermissionDataProvider.delete(session, "CONFIG_DATA_PROVIDER_UPDATE")
    PermissionDataProvider.delete(session, "CONFIG_DATA_PROVIDER_DELETE")
    session.commit()
