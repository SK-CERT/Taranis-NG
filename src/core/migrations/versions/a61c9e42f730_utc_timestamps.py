"""Store instants as timezone-aware UTC timestamps.

Revision ID: a61c9e42f730
Revises: c580a8db010f

The previous deployment's TZ describes legacy wall clocks, even when its services
now run in UTC. PostgreSQL deliberately resolves DST gaps/overlaps using standard
time. Keep the source zone and changed text values for a reversible downgrade.
"""

# SQL identifiers and query fragments below are frozen in this migration; values use binds.
# ruff: noqa: S608

import os
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "a61c9e42f730"
down_revision = "c580a8db010f"
branch_labels = None
depends_on = None

STATE_TABLE = "_utc_migration_state"
TIMESTAMP_COLUMNS = {
    "token_blacklist": ("created",),
    "user": ("last_login_at",),
    "news_item_attribute": ("created",),
    "news_item_data": ("collected", "updated"),
    "news_item_data_version": ("collected", "superseded"),
    "news_item_aggregate": ("created",),
    "ai_provider": ("updated_at",),
    "auth_provider": ("updated_at",),
    "user_auth_identity": ("created_at", "last_login_at"),
    "remote_access": ("last_synced_news_items", "last_synced_report_items"),
    "remote_node": ("last_synced_news_items", "last_synced_report_items"),
    "security_settings": ("updated_at",),
    "bots_node": ("created", "last_seen"),
    "attribute_extraction_rule": ("updated_at",),
    "user_webauthn_credential": ("created_at", "last_used_at"),
    "report_item_attribute": ("created", "last_updated"),
    "report_item": ("created", "last_updated"),
    "settings_user": ("updated_at",),
    "settings": ("updated_at",),
    "public_web_node": ("created", "last_seen"),
    "osint_source": ("modified", "last_collected", "last_attempted"),
    "traefik_settings": ("updated_at",),
    "data_provider": ("updated_at",),
    "product": ("created", "updated_at"),
    "collectors_node": ("created", "last_seen"),
    "product_type": ("created",),
    "log_record": ("timestamp",),
    "api_key": ("created_at", "expires_at"),
    "state": ("updated_at",),
    "state_entity_type": ("updated_at",),
    "report_item_translation": ("last_updated",),
    "report_item_attribute_translation": ("last_updated",),
    "product_translation": ("last_updated",),
    "tag": ("updated_at",),
    "tag_entity_type": ("updated_at",),
    "report_item_tag": ("created",),
    "product_tag": ("created",),
    "glossary_entry": ("updated_at",),
}
# These upstream columns already represent instants. Reinterpreting them as local
# wall clocks would shift them twice; upgrade and downgrade leave them untouched.
PRESERVED_AWARE_COLUMNS = {
    "notification_channel": ("updated_at",),
    "notification_event": ("updated_at",),
    "notification_outbox": ("next_attempt_at", "lease_until", "created_at", "sent_at"),
}
LEGACY_FORMATS = ("%d.%m.%Y - %H:%M:%S", "%d.%m.%Y - %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M")


def _legacy_zone() -> str:
    """Validate the original deployment timezone before changing any data."""
    zone = os.environ.get("TARANIS_NG_LEGACY_TZ") or os.environ.get("TZ") or "UTC"
    ZoneInfo(zone)
    return zone


def _parse_timestamp(value: str) -> datetime | None:
    """Recognize datetimes without inventing times for calendar dates or source text."""
    if not value or not value.strip():
        return None
    candidate = value.strip()
    try:
        date.fromisoformat(candidate)
    except ValueError:
        pass
    else:
        return None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        for fmt in LEGACY_FORMATS:
            try:
                return datetime.strptime(candidate, fmt)  # noqa: DTZ007 -- interpreted by PostgreSQL in the source zone below
            except ValueError:
                continue
        return None
    else:
        return parsed


def _normalize(connection: Connection, value: str, zone: str) -> str | None:
    """Convert explicit offsets directly and naive wall clocks through PostgreSQL."""
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return connection.execute(
        sa.text(
            "SELECT to_char(CAST(:value AS timestamp) AT TIME ZONE :zone AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')",
        ),
        {"value": parsed.isoformat(), "zone": zone},
    ).scalar_one()


def _convert_text(connection: Connection, table: str, column: str, query: str, zone: str) -> None:
    """Normalize recognized text timestamps, retaining originals for downgrade."""
    # Keyset pagination bounds memory without retaining a cursor across updates.
    last_id = None
    while True:
        condition = " WHERE id > :last_id" if last_id is not None else ""
        rows = connection.execute(
            sa.text(f"SELECT id, value FROM ({query}) AS timestamps{condition} ORDER BY id LIMIT 1000"),
            {"last_id": last_id} if last_id is not None else {},
        ).all()
        if not rows:
            return
        for row in rows:
            normalized = _normalize(connection, row.value, zone)
            if normalized is None or normalized == row.value:
                continue
            connection.execute(
                sa.text(f"INSERT INTO {STATE_TABLE} (kind, item_id, original, normalized) VALUES (:kind, :id, :original, :normalized)"),
                {"kind": table, "id": str(row.id), "original": row.value, "normalized": normalized},
            )
            connection.execute(
                sa.text(f'UPDATE "{table}" SET "{column}" = :value WHERE CAST(id AS text) = :id'),
                {"value": normalized, "id": str(row.id)},
            )
        last_id = rows[-1].id


def _convert_columns(zone: str, *, upgrade: bool) -> None:
    """Convert the frozen schema inventory using explicitly named timezone rules."""
    connection = op.get_bind()
    connection.execute(sa.text("SELECT set_config('taranis.utc_migration_timezone', :zone, true)"), {"zone": zone})
    for table, columns in TIMESTAMP_COLUMNS.items():
        for column in columns:
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=not upgrade),
                type_=sa.DateTime(timezone=upgrade),
                postgresql_using=f"\"{column}\" AT TIME ZONE current_setting('taranis.utc_migration_timezone')",
            )


def upgrade() -> None:
    """Convert historical wall clocks and text instants once, in the Alembic transaction."""
    zone = _legacy_zone()
    connection = op.get_bind()
    op.create_table(
        STATE_TABLE,
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column("item_id", sa.Text(), primary_key=True),
        sa.Column("original", sa.Text(), nullable=False),
        sa.Column("normalized", sa.Text()),
    )
    connection.execute(
        sa.text(f"INSERT INTO {STATE_TABLE} (kind, item_id, original) VALUES ('timezone', '', :zone)"),
        {"zone": zone},
    )
    _convert_columns(zone, upgrade=True)
    for table in ("news_item_data", "news_item_data_version"):
        _convert_text(connection, table, "published", f"SELECT id, published AS value FROM {table}", zone)
    _convert_text(
        connection,
        "attribute",
        "default_value",
        "SELECT id, default_value AS value FROM attribute WHERE type = 'DATE_TIME'",
        zone,
    )
    _convert_text(
        connection,
        "report_item_attribute",
        "value",
        "SELECT r.id, r.value FROM report_item_attribute r "
        "JOIN attribute_group_item g ON g.id = r.attribute_group_item_id "
        "JOIN attribute a ON a.id = g.attribute_id WHERE a.type = 'DATE_TIME'",
        zone,
    )


def downgrade() -> None:
    """Restore the original timezone and unchanged normalized text values."""
    connection = op.get_bind()
    zone = connection.execute(sa.text(f"SELECT original FROM {STATE_TABLE} WHERE kind = 'timezone' AND item_id = ''")).scalar_one()
    _convert_columns(zone, upgrade=False)
    for table, column in (
        ("news_item_data", "published"),
        ("news_item_data_version", "published"),
        ("report_item_attribute", "value"),
        ("attribute", "default_value"),
    ):
        connection.execute(
            sa.text(
                f'UPDATE "{table}" AS target SET "{column}" = state.original FROM {STATE_TABLE} AS state '
                f'WHERE state.kind = :kind AND CAST(target.id AS text) = state.item_id AND target."{column}" = state.normalized',
            ),
            {"kind": table},
        )
    op.drop_table(STATE_TABLE)
