"""Restore the UTC meaning of legacy RSS publication timestamps.

Revision ID: b7e4d192a630
Revises: a61c9e42f730

Feedparser returned UTC tuples, but the old RSS collector formatted them without
an offset. The UTC migration treated these strings as server-local wall clocks.
Use its original-value backups to repair only identifiable, unchanged RSS values.
"""

# Query fragments and identifiers come exclusively from the frozen table list.
# ruff: noqa: S608

import re
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "b7e4d192a630"
down_revision = "a61c9e42f730"
branch_labels = None
depends_on = None

STATE_TABLE = "_utc_migration_state"
TABLES = ("news_item_data", "news_item_data_version")
LEGACY_RSS_FORMAT = "%d.%m.%Y - %H:%M"
LEGACY_RSS_PATTERN = re.compile(r"\d{2}\.\d{2}\.\d{4} - \d{2}:\d{2}")


def _corrected_timestamp(original: str) -> str | None:
    """Recognize precisely the timezone-free format written from feedparser tuples."""
    if not LEGACY_RSS_PATTERN.fullmatch(original):
        return None
    try:
        parsed = datetime.strptime(original, LEGACY_RSS_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def _repair_table(connection: Connection, table: str) -> None:
    """Repair backed-up RSS values that still equal their migration output."""
    owner_join = "" if table == "news_item_data" else "JOIN news_item_data owner ON owner.id = target.news_item_data_id "
    owner = "target" if table == "news_item_data" else "owner"
    last_id = ""
    while True:
        rows = connection.execute(
            sa.text(
                f"SELECT state.item_id, state.original, state.normalized FROM {STATE_TABLE} state "
                f'JOIN "{table}" target ON CAST(target.id AS text) = state.item_id '
                f"{owner_join}"
                f"JOIN osint_source source ON source.id = {owner}.osint_source_id "
                "JOIN collector ON collector.id = source.collector_id "
                "WHERE state.kind = :table AND state.item_id > :last_id "
                "AND collector.type = 'RSS_COLLECTOR' AND target.published = state.normalized "
                f"AND NOT EXISTS (SELECT 1 FROM {STATE_TABLE} repaired "
                "WHERE repaired.kind = :repair_kind AND repaired.item_id = state.item_id) "
                "ORDER BY state.item_id LIMIT 1000",
            ),
            {"table": table, "repair_kind": f"rss_utc:{table}", "last_id": last_id},
        ).all()
        if not rows:
            return
        for row in rows:
            corrected = _corrected_timestamp(row.original)
            if corrected is None or corrected == row.normalized:
                continue
            connection.execute(
                sa.text(f"INSERT INTO {STATE_TABLE} (kind, item_id, original, normalized) VALUES (:kind, :id, :before, :after)"),
                {"kind": f"rss_utc:{table}", "id": row.item_id, "before": row.normalized, "after": corrected},
            )
            connection.execute(
                sa.text(f'UPDATE "{table}" SET published = :after WHERE CAST(id AS text) = :id AND published = :before'),
                {"id": row.item_id, "before": row.normalized, "after": corrected},
            )
            # Keep the original UTC migration's downgrade conditional valid.
            connection.execute(
                sa.text(f"UPDATE {STATE_TABLE} SET normalized = :after WHERE kind = :table AND item_id = :id"),
                {"table": table, "id": row.item_id, "after": corrected},
            )
        last_id = rows[-1].item_id


def upgrade() -> None:
    """Correct identifiable legacy RSS instants without changing later edits or new data."""
    connection = op.get_bind()
    for table in TABLES:
        _repair_table(connection, table)


def downgrade() -> None:
    """Undo corrections when unchanged, preserving edits made after the repair."""
    connection = op.get_bind()
    for table in TABLES:
        parameters = {"kind": f"rss_utc:{table}", "table": table}
        connection.execute(
            sa.text(
                f'UPDATE "{table}" target SET published = repair.original FROM {STATE_TABLE} repair '
                "WHERE repair.kind = :kind AND CAST(target.id AS text) = repair.item_id AND target.published = repair.normalized",
            ),
            parameters,
        )
        connection.execute(
            sa.text(
                f"UPDATE {STATE_TABLE} state SET normalized = repair.original FROM {STATE_TABLE} repair "
                "WHERE repair.kind = :kind AND state.kind = :table AND state.item_id = repair.item_id "
                "AND state.normalized = repair.normalized",
            ),
            parameters,
        )
        connection.execute(sa.text(f"DELETE FROM {STATE_TABLE} WHERE kind = :kind"), parameters)
