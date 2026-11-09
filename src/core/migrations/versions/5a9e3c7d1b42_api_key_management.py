"""API key management: hashed keys, scopes, IP allowlists, policy and permissions.

- ``api_key``:
  - ``key`` (plaintext) becomes ``key_hash``, the hex SHA-256, computed in place, so existing
    keys keep working. ``key_prefix`` keeps the first 8 characters to recognise a key by.
  - New columns: ``description``, ``created_by``, ``enabled``, ``restricted``, ``allowed_ips``,
    ``last_used_at``, ``last_used_ip`` and ``expiry_notified_at`` (when the owner was told the key
    expired). Keys that have expired already count as reported: nobody is sent a message about
    something long past.
  - ``created_at`` and ``expires_at`` become ``timestamptz``. Postgres reads the stored values
    in the server's time zone, which the compose file sets to ``TZ``, the zone core wrote them in.
  - The name is unique per owner instead of across all users.
- ``api_key_permission``: the permissions a restricted key is limited to.
- ``security_settings``: the API key policy (``api_key_require_expiry``, ``api_key_max_days``,
  ``api_key_require_allowlist``) and the site-wide allowlist (``api_key_allowed_ips``).
- ``CONFIG_API_KEY_ACCESS/CREATE/UPDATE/DELETE`` (every user's keys, Access Management) and
  ``MY_API_KEYS_MANAGE`` (one's own keys, user settings), granted to Admin.

A core started on the new models before this revision ran has created ``api_key_permission``
itself (``db.create_all()``), so every step checks what is already there.

The downgrade cannot recover a key from its hash: it deletes every API key, which then has to
be created again.

Revision ID: 5a9e3c7d1b42
Revises: 72f1a157e289
Create Date: 2026-11-07 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5a9e3c7d1b42"
down_revision = "72f1a157e289"
branch_labels = None
depends_on = None

TABLE = "api_key"
PERMISSION_TABLE = "api_key_permission"
SETTINGS_TABLE = "security_settings"
OLD_NAME_UNIQUE = "api_key_name_key"
NAME_UNIQUE = "api_key_user_id_name_key"
HASH_UNIQUE = "api_key_key_hash_key"

PERMISSIONS = (
    ("CONFIG_API_KEY_ACCESS", "Config API keys access", "Access to the API keys of all users"),
    ("CONFIG_API_KEY_CREATE", "Config API key create", "Create API keys for any user"),
    ("CONFIG_API_KEY_UPDATE", "Config API key update", "Rename, enable, disable and limit API keys of any user"),
    ("CONFIG_API_KEY_DELETE", "Config API key delete", "Delete API keys of any user"),
    ("MY_API_KEYS_MANAGE", "Own API keys", "Create and manage own API keys"),
)

NEW_KEY_COLUMNS = (
    ("description", lambda: sa.Column("description", sa.String(), nullable=True)),
    ("created_by", lambda: sa.Column("created_by", sa.String(), nullable=True)),
    ("enabled", lambda: sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true")),
    ("restricted", lambda: sa.Column("restricted", sa.Boolean(), nullable=False, server_default="false")),
    ("allowed_ips", lambda: sa.Column("allowed_ips", sa.Text(), nullable=True)),
    ("last_used_at", lambda: sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True)),
    ("last_used_ip", lambda: sa.Column("last_used_ip", sa.String(), nullable=True)),
    ("expiry_notified_at", lambda: sa.Column("expiry_notified_at", sa.DateTime(timezone=True), nullable=True)),
)

SETTINGS_COLUMNS = (
    ("api_key_require_expiry", lambda: sa.Column("api_key_require_expiry", sa.Boolean(), nullable=False, server_default="false")),
    ("api_key_max_days", lambda: sa.Column("api_key_max_days", sa.Integer(), nullable=True)),
    ("api_key_require_allowlist", lambda: sa.Column("api_key_require_allowlist", sa.Boolean(), nullable=False, server_default="false")),
    ("api_key_allowed_ips", lambda: sa.Column("api_key_allowed_ips", sa.Text(), nullable=True)),
)


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _unique_constraints(table: str) -> set[str]:
    return {constraint["name"] for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _hash_keys() -> None:
    """Replace the plaintext ``key`` with its SHA-256 (``key_hash``) and a short ``key_prefix``."""
    columns = _columns(TABLE)
    if "key" not in columns:
        return
    if "key_hash" not in columns:
        op.add_column(TABLE, sa.Column("key_hash", sa.String(64), nullable=True))
    if "key_prefix" not in columns:
        op.add_column(TABLE, sa.Column("key_prefix", sa.String(16), nullable=True))
    op.execute(
        sa.text(
            f"UPDATE {TABLE} SET key_hash = encode(sha256(convert_to(key, 'UTF8')), 'hex'), key_prefix = left(key, 8)",  # noqa: S608
        ),
    )
    op.alter_column(TABLE, "key_hash", nullable=False)
    op.alter_column(TABLE, "key_prefix", nullable=False)
    op.drop_column(TABLE, "key")


def _upgrade_api_key() -> None:
    _hash_keys()
    if HASH_UNIQUE not in _unique_constraints(TABLE):
        op.create_unique_constraint(HASH_UNIQUE, TABLE, ["key_hash"])

    columns = _columns(TABLE)
    for name, column in NEW_KEY_COLUMNS:
        if name not in columns:
            op.add_column(TABLE, column())
    for name in ("created_at", "expires_at"):
        op.alter_column(TABLE, name, type_=sa.DateTime(timezone=True), existing_type=sa.DateTime(), postgresql_using=f"{name}::timestamptz")
    op.execute(sa.text(f"UPDATE {TABLE} SET expiry_notified_at = expires_at WHERE expires_at <= now() AND expiry_notified_at IS NULL"))  # noqa: S608

    constraints = _unique_constraints(TABLE)
    if OLD_NAME_UNIQUE in constraints:
        op.drop_constraint(OLD_NAME_UNIQUE, TABLE, type_="unique")
    if NAME_UNIQUE not in constraints:
        op.create_unique_constraint(NAME_UNIQUE, TABLE, ["user_id", "name"])


def _create_permission_table() -> None:
    if PERMISSION_TABLE in _tables():
        return
    op.create_table(
        PERMISSION_TABLE,
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_key.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("api_key_id", "permission_id"),
    )


def _add_policy_columns() -> None:
    columns = _columns(SETTINGS_TABLE)
    for name, column in SETTINGS_COLUMNS:
        if name not in columns:
            op.add_column(SETTINGS_TABLE, column())


def _grant_permissions() -> None:
    """Create the permissions and give them to Admin.

    Core also registers them at startup (``Permission.add``), so one may already exist; Admin
    gets whichever it lacks, these permissions being new with this feature.
    """
    connection = op.get_bind()
    for permission_id, name, description in PERMISSIONS:
        connection.execute(
            sa.text(
                "INSERT INTO permission (id, name, description) VALUES (:id, :name, :description) ON CONFLICT (id) DO NOTHING",
            ),
            {"id": permission_id, "name": name, "description": description},
        )
        connection.execute(
            sa.text(
                # Typed once: Postgres infers a parameter used in two places separately.
                "INSERT INTO role_permission (role_id, permission_id) "
                "SELECT role.id, CAST(:id AS VARCHAR) FROM role WHERE role.name = 'Admin' "
                "AND NOT EXISTS (SELECT 1 FROM role_permission rp WHERE rp.role_id = role.id AND rp.permission_id = CAST(:id AS VARCHAR))",
            ),
            {"id": permission_id},
        )


def upgrade() -> None:
    """Hash the keys, add the scope, allowlist and policy columns, and the permissions."""
    _upgrade_api_key()
    _create_permission_table()
    _add_policy_columns()
    _grant_permissions()


def downgrade() -> None:
    """Remove the permissions, the policy and the scopes; delete every key (hashes cannot be undone)."""
    connection = op.get_bind()
    tables = _tables()
    for permission_id, _name, _description in PERMISSIONS:
        for table in ("role_permission", "user_permission", PERMISSION_TABLE):
            if table in tables:
                connection.execute(sa.text(f"DELETE FROM {table} WHERE permission_id = :id"), {"id": permission_id})  # noqa: S608
        connection.execute(sa.text("DELETE FROM permission WHERE id = :id"), {"id": permission_id})

    columns = _columns(SETTINGS_TABLE)
    for name, _column in SETTINGS_COLUMNS:
        if name in columns:
            op.drop_column(SETTINGS_TABLE, name)

    if PERMISSION_TABLE in tables:
        op.drop_table(PERMISSION_TABLE)

    # A key cannot be recovered from its hash.
    op.execute(sa.text(f"DELETE FROM {TABLE}"))  # noqa: S608
    constraints = _unique_constraints(TABLE)
    if NAME_UNIQUE in constraints:
        op.drop_constraint(NAME_UNIQUE, TABLE, type_="unique")
    if HASH_UNIQUE in constraints:
        op.drop_constraint(HASH_UNIQUE, TABLE, type_="unique")
    columns = _columns(TABLE)
    for name in ("key_hash", "key_prefix", *(name for name, _column in NEW_KEY_COLUMNS)):
        if name in columns:
            op.drop_column(TABLE, name)
    if "key" not in columns:
        op.add_column(TABLE, sa.Column("key", sa.VARCHAR(length=40), nullable=False))
    for name in ("created_at", "expires_at"):
        op.alter_column(TABLE, name, type_=sa.DateTime(), existing_type=sa.DateTime(timezone=True), postgresql_using=f"{name}::timestamp")
    if OLD_NAME_UNIQUE not in _unique_constraints(TABLE):
        op.create_unique_constraint(OLD_NAME_UNIQUE, TABLE, ["name"])
