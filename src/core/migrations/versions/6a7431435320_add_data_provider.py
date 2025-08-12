"""add new data_provider table

Revision ID: 6a7431435320
Revises: 146979f5f4c2
Create Date: 2025-08-06 13:41:18.166310

"""

from alembic import op
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import inspect, orm
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "6a7431435320"
down_revision = "146979f5f4c2"
branch_labels = None
depends_on = None


Base = orm.declarative_base()

default_user_agent = "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"
default_updated_by = "system-migration"


class DataProvider(Base):
    __tablename__ = "data_provider"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    api_type = sa.Column(sa.String(), nullable=False)
    api_url = sa.Column(sa.String(), nullable=False)
    api_key = sa.Column(sa.String())
    user_agent = sa.Column(sa.String())
    updated_by = sa.Column(sa.String())
    updated_at = sa.Column(sa.DateTime())


class Permission_DataProvider(Base):
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
        perm = session.query(Permission_DataProvider).filter_by(id=id).first()
        if not perm:
            session.add(Permission_DataProvider(id, name, description))

    @staticmethod
    def delete(session, id):
        perm = session.query(Permission_DataProvider).filter_by(id=id).first()
        if perm:
            session.delete(perm)
            print(f"Permission {perm.id} deleted...", flush=True)


class Role_DataProvider(Base):
    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(Permission_DataProvider, secondary="role_permission")


class RolePermission_DataProvider(Base):
    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


def upgrade():
    """Create data_provider, attr_euvd, attr_cve, and attr_cpe tables with constraints."""
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
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )
        session.add(
            DataProvider(
                name="NVD CVE",
                api_type="CVE",
                api_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )
        session.add(
            DataProvider(
                name="NVD CPE",
                api_type="CPE",
                api_url="https://services.nvd.nist.gov/rest/json/cpes/2.0",
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )
        session.add(
            DataProvider(
                name="MITRE CWE",
                api_type="CWE",
                api_url="https://cwe-api.mitre.org/api/v1/",
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )
        session.add(
            DataProvider(
                name="Google OSV",
                api_type="OSV",
                api_url="https://api.osv.dev/v1/vulns/",
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )
        session.add(
            DataProvider(
                name="FIRST EPSS",
                api_type="EPSS",
                api_url="https://api.first.org/data/v1/epss",
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )
        session.add(
            DataProvider(
                name="pyxyp VULDB",
                api_type="VULDB",
                api_url="https://vuldb.com/?api",
                user_agent=default_user_agent,
                updated_at=datetime.now(),
                updated_by=default_updated_by,
            )
        )

        session.commit()

    Permission_DataProvider.add(
        session, "CONFIG_DATA_PROVIDER_ACCESS", "Config data provider access", "Access to data provider configuration"
    )
    Permission_DataProvider.add(session, "CONFIG_DATA_PROVIDER_CREATE", "Config data provider create", "Create data provider configuration")
    Permission_DataProvider.add(session, "CONFIG_DATA_PROVIDER_UPDATE", "Config data provider update", "Update data provider configuration")
    Permission_DataProvider.add(session, "CONFIG_DATA_PROVIDER_DELETE", "Config data provider delete", "Delete data provider configuration")
    session.commit()

    role = session.query(Role_DataProvider).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(Permission_DataProvider).all()
        session.add(role)
        session.commit()

    for table_name, pk_name in [
        ("attr_euvd", "euvd_pkey"),
        ("attr_cve", "cve_pkey"),
        ("attr_cpe", "cpe_pkey"),
        ("attr_cwe", "cwe_pkey"),
        ("attr_osv", "osv_pkey"),
        ("attr_epss", "epss_pkey"),
    ]:
        if table_name not in inspector.get_table_names():
            op.create_table(
                table_name,
                sa.Column("id", sa.String(), nullable=False, primary_key=True),
                sa.Column("data", JSONB()),
                sa.PrimaryKeyConstraint("id", name=pk_name),
            )


def downgrade():
    """Drop all created tables and permissions."""
    print("deleting table 'data_provider'...", flush=True)
    op.drop_table("data_provider")

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    print("deleting 'AI' permissions...", flush=True)
    # this delete also role_permission, user_permission records
    Permission_DataProvider.delete(session, "CONFIG_DATA_PROVIDER_ACCESS")
    Permission_DataProvider.delete(session, "CONFIG_DATA_PROVIDER_CREATE")
    Permission_DataProvider.delete(session, "CONFIG_DATA_PROVIDER_UPDATE")
    Permission_DataProvider.delete(session, "CONFIG_DATA_PROVIDER_DELETE")
    session.commit()

    for table_name in ["attr_euvd", "attr_cve", "attr_cpe"]:
        print(f"deleting table '{table_name}'...", flush=True)
        op.drop_table(table_name)
