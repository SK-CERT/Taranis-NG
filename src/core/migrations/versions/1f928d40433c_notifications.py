"""User notifications: delivery channels, the outbox, and their permissions.

- ``notification_channel`` - one row per way of reaching users (e-mail for now), with its
  settings and its Fernet-encrypted secret
- ``notification_event`` - which events users are notified of; an event without a row is on
- ``notification_outbox`` - notifications rendered for one recipient, kept until delivered
  and retried while delivery fails
- ``CONFIG_NOTIFICATIONS_ACCESS`` / ``CONFIG_NOTIFICATIONS_UPDATE`` - who may see and change
  them; granted to Admin, since the channels hold credentials

A core started with the new model before this revision ran creates both tables itself
(``db.create_all()``), so every step checks what is already there and the upgrade can run
again.

Revision ID: 1f928d40433c
Revises: 2c2e10005e77
Create Date: 2026-10-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1f928d40433c"
down_revision = "2c2e10005e77"
branch_labels = None
depends_on = None

CHANNEL_TABLE = "notification_channel"
EVENT_TABLE = "notification_event"
OUTBOX_TABLE = "notification_outbox"
OUTBOX_INDEX = "ix_notification_outbox_status_next_attempt_at"

PERMISSIONS = (
    ("CONFIG_NOTIFICATIONS_ACCESS", "Config notifications access", "Access to notification channels and their delivery log"),
    ("CONFIG_NOTIFICATIONS_UPDATE", "Config notifications update", "Update notification channels and retry deliveries"),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _create_tables() -> None:
    tables = _tables()
    if CHANNEL_TABLE not in tables:
        op.create_table(
            CHANNEL_TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("secret", sa.String(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("kind"),
        )
    if EVENT_TABLE not in tables:
        op.create_table(
            EVENT_TABLE,
            sa.Column("event", sa.String(64), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("event"),
        )
    if OUTBOX_TABLE not in tables:
        op.create_table(
            OUTBOX_TABLE,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("channel_kind", sa.String(32), nullable=False),
            sa.Column("recipient", sa.String(), nullable=False),
            sa.Column("event", sa.String(64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("subject", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(OUTBOX_TABLE)}
    if OUTBOX_INDEX not in indexes:
        op.create_index(OUTBOX_INDEX, OUTBOX_TABLE, ["status", "next_attempt_at"])


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
    """Create the channel, event and outbox tables and the notification permissions."""
    _create_tables()
    _grant_permissions()


def downgrade() -> None:
    """Drop the notification permissions and the tables."""
    connection = op.get_bind()
    for permission_id, _name, _description in PERMISSIONS:
        for table in ("role_permission", "user_permission"):
            if table in _tables():
                connection.execute(sa.text(f"DELETE FROM {table} WHERE permission_id = :id"), {"id": permission_id})  # noqa: S608
        connection.execute(sa.text("DELETE FROM permission WHERE id = :id"), {"id": permission_id})
    tables = _tables()
    if OUTBOX_TABLE in tables:
        op.drop_table(OUTBOX_TABLE)
    if EVENT_TABLE in tables:
        op.drop_table(EVENT_TABLE)
    if CHANNEL_TABLE in tables:
        op.drop_table(CHANNEL_TABLE)
