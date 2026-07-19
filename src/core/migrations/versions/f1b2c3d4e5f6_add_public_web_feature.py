"""Add public_web feature with nodes, webs, images, and product mapping.

Creates the public-web infrastructure for hosting branded vulnerability feeds:
- public_web_node: Registered public-web nodes (instances)
- public_web: Individual websites/feeds hosted on a node
- public_web_image: Assets (logos, icons) for each website
- product_public_web: Many-to-many mapping to restrict products to specific websites

Revision ID: f1b2c3d4e5f6
Revises: e3f9d1a7c8b5
Create Date: 2026-07-07 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "f1b2c3d4e5f6"
down_revision = "e3f9d1a7c8b5"
branch_labels = None
depends_on = None

# The config permissions used by the public-web node/web CRUD endpoints. They are
# also (idempotently) registered at app startup via Permission.add; created here
# so they can be assigned to the Admin role in the same transaction.
PUBLIC_WEB_PERMISSIONS = [
    ("CONFIG_PUBLIC_WEB_NODE_ACCESS", "Config public-web nodes access", "Access to public-web nodes configuration"),
    ("CONFIG_PUBLIC_WEB_NODE_CREATE", "Config public-web node create", "Create public-web node configuration"),
    ("CONFIG_PUBLIC_WEB_NODE_UPDATE", "Config public-web node update", "Update public-web node configuration"),
    ("CONFIG_PUBLIC_WEB_NODE_DELETE", "Config public-web node delete", "Delete public-web node configuration"),
]


class PermissionPW(Base):
    """Permission model for public-web feature."""

    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())


class RolePW(Base):
    """Role model for public-web feature."""

    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(PermissionPW, secondary="role_permission")


class RolePermissionPW(Base):
    """Role permission mapping model for public-web feature."""

    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


def upgrade() -> None:
    """Create all public-web related tables and permissions."""
    # Create public_web_node table
    op.create_table(
        "public_web_node",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("api_key", sa.String(), nullable=False),
        sa.Column("api_url", sa.String(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create public_web table with enabled column
    op.create_table(
        "public_web",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["node_id"], ["public_web_node.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create public_web_image table
    op.create_table(
        "public_web_image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("web_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=True),
        sa.ForeignKeyConstraint(["web_id"], ["public_web.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create product_public_web many-to-many mapping table
    op.create_table(
        "product_public_web",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("public_web_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["public_web_id"], ["public_web.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "public_web_id"),
    )

    # Register the public-web config permissions and grant them to the Admin role
    session = orm.Session(bind=op.get_bind())
    for perm_id, name, description in PUBLIC_WEB_PERMISSIONS:
        if not session.query(PermissionPW).filter_by(id=perm_id).first():
            session.add(PermissionPW(id=perm_id, name=name, description=description))
    session.commit()
    admin_role = session.query(RolePW).filter_by(name="Admin").first()
    if admin_role:
        admin_role.permissions = session.query(PermissionPW).all()
        session.add(admin_role)
        session.commit()


def downgrade() -> None:
    """Drop all public-web related tables."""
    op.drop_table("product_public_web")
    op.drop_table("public_web_image")
    op.drop_table("public_web")
    op.drop_table("public_web_node")
