"""Configure the timezone boundary of legacy remote peers.

Revision ID: d8f7a401c952
Revises: b7e4d192a630
"""

import os
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op

revision = "d8f7a401c952"
down_revision = "b7e4d192a630"
branch_labels = None
depends_on = None

TABLES = ("remote_access", "remote_node")


def upgrade() -> None:
    """Default existing peers to the saved pre-UTC installation timezone."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    zone = None
    if inspector.has_table("_utc_migration_state"):
        zone = connection.execute(
            sa.text("SELECT original FROM _utc_migration_state WHERE kind = 'timezone' AND item_id = ''"),
        ).scalar_one_or_none()
    zone = zone or os.environ.get("TARANIS_NG_LEGACY_TZ") or os.environ.get("TZ") or "UTC"
    ZoneInfo(zone)
    for table in TABLES:
        if "legacy_timezone" in {column["name"] for column in inspector.get_columns(table)}:
            continue
        op.add_column(table, sa.Column("legacy_timezone", sa.String(128), nullable=True))
        connection.execute(sa.update(sa.table(table, sa.column("legacy_timezone"))).values(legacy_timezone=zone))
        op.alter_column(table, "legacy_timezone", nullable=False, server_default="UTC")


def downgrade() -> None:
    """Remove only the legacy boundary configuration."""
    for table in TABLES:
        op.drop_column(table, "legacy_timezone")
