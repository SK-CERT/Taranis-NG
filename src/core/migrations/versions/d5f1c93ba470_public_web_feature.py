"""Add the public-web feature: nodes, webs, images, product mapping and routing settings.

Creates the infrastructure for hosting branded public feeds:

- ``public_web_node`` - a registered public-web instance, carrying which Traefik fronts
  its webs and the ACME resolver name that Traefik declares
- ``public_web`` - one branded feed under a node, on its own hostname, carrying that
  hostname's routing overrides (ACME resolver, HSTS, its own certificate)
- ``public_web_image`` - logo/favicon/preview assets per feed
- ``product_public_web`` - restricts a product to specific feeds
- ``traefik_settings`` - the instance-wide routing configuration core serves to
  Traefik's HTTP provider (response headers, HSTS policy, TLS floor, default
  certificate, default ACME resolver, and how Traefik verifies a node it proxies to)

One migration rather than the several this feature was developed across: the
incremental ALTERs are folded into the CREATEs, and their data fix-ups are dropped,
having only ever rewritten rows an earlier revision of this same feature wrote. None of
those revisions shipped, so only a development database can be sitting on one - stamp it
rather than re-running:

    docker compose exec core alembic stamp d5f1c93ba470

Revision ID: d5f1c93ba470
Revises: a6b7c8d9e0f1
Create Date: 2026-07-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "d5f1c93ba470"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None

# Config permissions for the public-web CRUD endpoints and the routing settings.
# They are also registered idempotently at app startup via Permission.add; created
# here so they can be granted to Admin in the same transaction.
#
# CONFIG_TRAEFIK_* is separate from CONFIG_PUBLIC_WEB_NODE_*: it covers the TLS the
# whole instance is served with, not just the feeds, so it is worth being able to
# grant one without the other.
FEATURE_PERMISSIONS = [
    ("CONFIG_PUBLIC_WEB_NODE_ACCESS", "Config public-web nodes access", "Access to public-web nodes configuration"),
    ("CONFIG_PUBLIC_WEB_NODE_CREATE", "Config public-web node create", "Create public-web node configuration"),
    ("CONFIG_PUBLIC_WEB_NODE_UPDATE", "Config public-web node update", "Update public-web node configuration"),
    ("CONFIG_PUBLIC_WEB_NODE_DELETE", "Config public-web node delete", "Delete public-web node configuration"),
    ("CONFIG_TRAEFIK_ACCESS", "Config routing and TLS access", "Access to routing and TLS configuration"),
    ("CONFIG_TRAEFIK_UPDATE", "Config routing and TLS update", "Update routing and TLS configuration"),
]

DEFAULT_HSTS_MAX_AGE = 31536000


class PermissionPW(Base):
    """Permission model for the public-web feature."""

    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())


class RolePW(Base):
    """Role model for the public-web feature."""

    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(PermissionPW, secondary="role_permission")


class RolePermissionPW(Base):
    """Role permission mapping model for the public-web feature."""

    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


def upgrade() -> None:
    """Create the public-web tables, the routing settings, and their permissions."""
    op.create_table(
        "public_web_node",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("api_key", sa.String(), nullable=False),
        sa.Column("api_url", sa.String(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        # No default: a node that has never been contacted must not look alive.
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        # See model.public_web_node.PublicWebNode for what these two decide. False and
        # empty are the safe defaults; prestart_core.sh marks the node beside core, and
        # ansible sends the resolver name its worker template declares.
        sa.Column("fronted_by_core", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cert_resolver", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "public_web",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        # Host-scoped routing: HSTS and the certificate a hostname is served with
        # are properties of that hostname, and each web is one hostname. Empty
        # inherits the node's value, then the instance-wide one.
        sa.Column("cert_resolver", sa.String(), nullable=True),
        sa.Column("hsts", sa.String(), nullable=True),
        sa.Column("tls_cert", sa.Text(), nullable=True),
        sa.Column("tls_key", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["node_id"], ["public_web_node.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

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

    op.create_table(
        "product_public_web",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("public_web_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["public_web_id"], ["public_web.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "public_web_id"),
    )

    # Single row (id 1). Not seeded here: model.traefik_settings.TraefikSettings.get()
    # creates it with the shipped defaults on first use, which keeps those defaults in
    # one place rather than duplicated into a migration that can never be updated.
    op.create_table(
        "traefik_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("security_headers", sa.JSON(), nullable=False, server_default="{}"),
        # HSTS ships off: a browser remembers it and refuses to let the user click
        # through a certificate error while it is in force.
        sa.Column("hsts_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hsts_max_age", sa.Integer(), nullable=False, server_default=str(DEFAULT_HSTS_MAX_AGE)),
        sa.Column("hsts_include_subdomains", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hsts_preload", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tls_min_version", sa.String(), nullable=True),
        sa.Column("tls_curve_preferences", sa.String(), nullable=True),
        sa.Column("cert_resolver", sa.String(), nullable=True),
        sa.Column("default_cert", sa.Text(), nullable=True),
        sa.Column("default_key", sa.Text(), nullable=True),
        # How Traefik behaves as the TLS *client* when it proxies to a node over https,
        # which only happens in a distributed deployment - a single-host node is reached
        # over the Docker network as plain http. Verification stays on by default.
        sa.Column("backend_insecure_skip_verify", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("backend_root_cas", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    session = orm.Session(bind=op.get_bind())
    added = []
    for perm_id, name, description in FEATURE_PERMISSIONS:
        if not session.query(PermissionPW).filter_by(id=perm_id).first():
            permission = PermissionPW(id=perm_id, name=name, description=description)
            session.add(permission)
            added.append(permission)
    session.commit()

    # Only the new permissions are granted, so an Admin role someone has
    # deliberately narrowed does not get everything back.
    admin_role = session.query(RolePW).filter_by(name="Admin").first()
    if admin_role and added:
        admin_role.permissions = admin_role.permissions + added
        session.add(admin_role)
        session.commit()


def downgrade() -> None:
    """Drop the public-web tables, the routing settings, and their permissions."""
    op.drop_table("traefik_settings")
    op.drop_table("product_public_web")
    op.drop_table("public_web_image")
    op.drop_table("public_web")
    op.drop_table("public_web_node")

    session = orm.Session(bind=op.get_bind())
    for perm_id, _name, _description in FEATURE_PERMISSIONS:
        session.query(RolePermissionPW).filter_by(permission_id=perm_id).delete()
        session.query(PermissionPW).filter_by(id=perm_id).delete()
    session.commit()
