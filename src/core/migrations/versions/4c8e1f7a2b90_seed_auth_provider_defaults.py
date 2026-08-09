"""Seed local authentication and auth-provider administration permissions.

The lightweight tables below are frozen migration-local snapshots.  This
revision must not import application ORM models, which can change over time.

Revision ID: 4c8e1f7a2b90
Revises: e3f9d1a7c8b5
Create Date: 2026-08-09 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4c8e1f7a2b90"
down_revision = "e3f9d1a7c8b5"
branch_labels = None
depends_on = None


PERMISSIONS = (
    {
        "id": "CONFIG_AUTH_PROVIDER_ACCESS",
        "name": "Config auth providers access",
        "description": "Access to authentication providers configuration",
    },
    {
        "id": "CONFIG_AUTH_PROVIDER_CREATE",
        "name": "Config auth provider create",
        "description": "Create authentication provider configuration",
    },
    {
        "id": "CONFIG_AUTH_PROVIDER_UPDATE",
        "name": "Config auth provider update",
        "description": "Update authentication provider configuration",
    },
    {
        "id": "CONFIG_AUTH_PROVIDER_DELETE",
        "name": "Config auth provider delete",
        "description": "Delete authentication provider configuration",
    },
)

LOCAL_PROVIDER = {
    "name": "Local accounts",
    "slug": "local",
    "kind": "local",
    "enabled": True,
    "organization_id": None,
    "provisioning_mode": "manual",
    "allowed_domains": "",
    "require_mfa": False,
    "config": {},
    "secret": None,
    "updated_by": None,
}

permission = sa.table(
    "permission",
    sa.column("id", sa.String()),
    sa.column("name", sa.String()),
    sa.column("description", sa.String()),
)
role = sa.table("role", sa.column("id", sa.Integer()), sa.column("name", sa.String()))
role_permission = sa.table(
    "role_permission",
    sa.column("role_id", sa.Integer()),
    sa.column("permission_id", sa.String()),
)
user_permission = sa.table(
    "user_permission",
    sa.column("user_id", sa.Integer()),
    sa.column("permission_id", sa.String()),
)
auth_provider = sa.table(
    "auth_provider",
    sa.column("id", sa.Integer()),
    sa.column("name", sa.String()),
    sa.column("slug", sa.String()),
    sa.column("kind", sa.String()),
    sa.column("enabled", sa.Boolean()),
    sa.column("organization_id", sa.Integer()),
    sa.column("provisioning_mode", sa.String()),
    sa.column("allowed_domains", sa.String()),
    sa.column("require_mfa", sa.Boolean()),
    sa.column("config", postgresql.JSON()),
    sa.column("secret", sa.String()),
    sa.column("updated_by", sa.String()),
)
auth_provider_role = sa.table(
    "auth_provider_role",
    sa.column("auth_provider_id", sa.Integer()),
    sa.column("role_id", sa.Integer()),
)
user_auth_identity = sa.table("user_auth_identity", sa.column("auth_provider_id", sa.Integer()))


def upgrade() -> None:
    """Add the four permissions, exact Admin links, and local provider."""
    connection = op.get_bind()
    admin_role_id = connection.execute(sa.select(role.c.id).where(role.c.name == "Admin")).scalar_one_or_none()
    if admin_role_id is None:
        message = "Cannot seed authentication-provider permissions: the Admin role does not exist"
        raise RuntimeError(message)

    op.bulk_insert(permission, list(PERMISSIONS))
    connection.execute(
        sa.insert(role_permission),
        [{"role_id": admin_role_id, "permission_id": item["id"]} for item in PERMISSIONS],
    )
    op.bulk_insert(auth_provider, [LOCAL_PROVIDER])


def _assert_safe_downgrade(
    connection: sa.engine.Connection,
    admin_role_id: int | None,
    local_provider_row: dict[str, object] | None,
) -> None:
    """Refuse to remove migration-owned rows after authentication use or reassignment."""
    permission_ids = tuple(item["id"] for item in PERMISSIONS)

    for permission_id in permission_ids:
        other_role_link = connection.execute(
            sa.select(sa.literal(1))
            .select_from(role_permission.join(role, role_permission.c.role_id == role.c.id))
            .where(role_permission.c.permission_id == permission_id)
            .where(role.c.name != "Admin")
            .limit(1),
        ).scalar()
        direct_user_link = connection.execute(
            sa.select(sa.literal(1)).select_from(user_permission).where(user_permission.c.permission_id == permission_id).limit(1),
        ).scalar()
        if other_role_link or direct_user_link:
            message = f"Refusing to remove authentication permission {permission_id}: it has assignments outside the Admin role"
            raise RuntimeError(message)

    if local_provider_row is None:
        message = "Refusing to remove local authentication seed: the migration-owned provider is missing"
        raise RuntimeError(message)

    local_provider_id = local_provider_row["id"]
    local_provider_values = {key: value for key, value in local_provider_row.items() if key != "id"}
    if local_provider_values != LOCAL_PROVIDER:
        message = "Refusing to remove local authentication seed because its configuration has been changed"
        raise RuntimeError(message)

    other_provider = connection.execute(
        sa.select(sa.literal(1)).select_from(auth_provider).where(auth_provider.c.id != local_provider_id).limit(1),
    ).scalar()
    if other_provider:
        message = "Refusing to remove authentication defaults while other authentication providers are configured"
        raise RuntimeError(message)

    linked_identity = connection.execute(
        sa.select(sa.literal(1)).select_from(user_auth_identity).where(user_auth_identity.c.auth_provider_id == local_provider_id).limit(1),
    ).scalar()
    linked_role = connection.execute(
        sa.select(sa.literal(1)).select_from(auth_provider_role).where(auth_provider_role.c.auth_provider_id == local_provider_id).limit(1),
    ).scalar()
    if linked_identity or linked_role:
        message = "Refusing to remove local authentication seed because it has linked identities or default roles"
        raise RuntimeError(message)

    if admin_role_id is None:
        message = "Refusing to remove authentication permissions: the Admin role is missing"
        raise RuntimeError(message)


def downgrade() -> None:
    """Remove exactly the rows owned by this revision when still safe."""
    connection = op.get_bind()
    admin_role_id = connection.execute(sa.select(role.c.id).where(role.c.name == "Admin")).scalar_one_or_none()
    local_provider_row = (
        connection.execute(
            sa.select(
                auth_provider.c.id,
                auth_provider.c.name,
                auth_provider.c.slug,
                auth_provider.c.kind,
                auth_provider.c.enabled,
                auth_provider.c.organization_id,
                auth_provider.c.provisioning_mode,
                auth_provider.c.allowed_domains,
                auth_provider.c.require_mfa,
                auth_provider.c.config,
                auth_provider.c.secret,
                auth_provider.c.updated_by,
            )
            .where(auth_provider.c.slug == LOCAL_PROVIDER["slug"])
            .where(auth_provider.c.kind == LOCAL_PROVIDER["kind"]),
        )
        .mappings()
        .one_or_none()
    )
    local_provider_row = dict(local_provider_row) if local_provider_row is not None else None

    _assert_safe_downgrade(connection, admin_role_id, local_provider_row)
    local_provider_id = local_provider_row["id"]

    permission_ids = tuple(item["id"] for item in PERMISSIONS)
    connection.execute(
        sa.delete(role_permission)
        .where(role_permission.c.role_id == admin_role_id)
        .where(role_permission.c.permission_id.in_(permission_ids)),
    )
    connection.execute(sa.delete(auth_provider).where(auth_provider.c.id == local_provider_id))
    connection.execute(sa.delete(permission).where(permission.c.id.in_(permission_ids)))
