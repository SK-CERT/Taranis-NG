"""Repair historical RSS publication times using the original UTC migration's backup.

Integration cases require TARANIS_TEST_POSTGRES_URL and use a separate temporary
schema with real string news/source IDs and integer archived-version IDs.
"""

import importlib.util
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATIONS = Path(__file__).parents[1] / "migrations" / "versions"
ORIGINAL_FILE = "a61c9e42f730_utc_timestamps.py"
REPAIR_FILE = "b7e4d192a630_fix_legacy_rss_publication_utc.py"


def _migration(filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(Path(filename).stem, MIGRATIONS / filename)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rss_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[ModuleType, ModuleType, sa.Connection]]:
    url = os.environ.get("TARANIS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TARANIS_TEST_POSTGRES_URL is not set (disposable PostgreSQL integration database)")
    engine = sa.create_engine(url)
    schema = f"rss_utc_test_{uuid4().hex}"
    original = _migration(ORIGINAL_FILE)
    repair = _migration(REPAIR_FILE)
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "Europe/Bratislava")
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            connection.execute(sa.text("SET LOCAL TIME ZONE 'Europe/Bratislava'"))
            for table, columns in original.TIMESTAMP_COLUMNS.items():
                extras = ""
                id_type = "integer"
                if table == "news_item_data":
                    id_type = "varchar(64)"
                    extras = ", published text, osint_source_id varchar(64)"
                elif table == "news_item_data_version":
                    extras = ", published text, news_item_data_id varchar(64)"
                elif table == "osint_source":
                    id_type = "varchar(64)"
                    extras = ", collector_id varchar(64)"
                elif table == "report_item_attribute":
                    extras = ", value text, attribute_group_item_id integer"
                columns_sql = ", ".join(f'"{column}" timestamp' for column in columns)
                connection.execute(sa.text(f'CREATE TABLE "{table}" (id {id_type} PRIMARY KEY, {columns_sql}{extras})'))
            connection.execute(sa.text("CREATE TABLE attribute (id integer PRIMARY KEY, type text, default_value text)"))
            connection.execute(sa.text("CREATE TABLE attribute_group_item (id integer PRIMARY KEY, attribute_id integer)"))
            connection.execute(sa.text("CREATE TABLE collector (id varchar(64) PRIMARY KEY, type text)"))
            connection.execute(
                sa.text(
                    "INSERT INTO collector (id, type) VALUES ('rss', 'RSS_COLLECTOR'), "
                    "('email', 'EMAIL_COLLECTOR'), ('web', 'WEB_COLLECTOR')",
                ),
            )
            connection.execute(
                sa.text(
                    "INSERT INTO osint_source (id, collector_id) VALUES ('rss-source', 'rss'), "
                    "('email-source', 'email'), ('web-source', 'web')",
                ),
            )
            yield original, repair, connection
    finally:
        with engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def _insert_news(connection: sa.Connection, item_id: str, version_id: int, value: str, source_id: str | None = "rss-source") -> None:
    connection.execute(
        sa.text("INSERT INTO news_item_data (id, osint_source_id, published) VALUES (:id, :source, :value)"),
        {"id": item_id, "source": source_id, "value": value},
    )
    connection.execute(
        sa.text("INSERT INTO news_item_data_version (id, news_item_data_id, published) VALUES (:id, :owner, :value)"),
        {"id": version_id, "owner": item_id, "value": value},
    )


def _published(connection: sa.Connection) -> dict[str, str]:
    rows = connection.execute(
        sa.text(
            "SELECT 'news_item_data:' || id, published FROM news_item_data "
            "UNION ALL SELECT 'news_item_data_version:' || id, published FROM news_item_data_version",
        ),
    ).all()
    return {row[0]: row[1] for row in rows}


def _state(connection: sa.Connection, kind: str, item_id: str) -> sa.Row:
    return connection.execute(
        sa.text("SELECT original, normalized FROM _utc_migration_state WHERE kind = :kind AND item_id = :id"),
        {"kind": kind, "id": item_id},
    ).one()


def test_revision_follows_original_utc_migration() -> None:
    repair = _migration(REPAIR_FILE)
    assert repair.revision == "b7e4d192a630"
    assert repair.down_revision == "a61c9e42f730"


@pytest.mark.parametrize(
    ("zone", "legacy", "expected"),
    [
        ("UTC", "15.07.2026 - 12:00", "2026-07-15T12:00:00Z"),
        ("Europe/Bratislava", "15.01.2026 - 12:00", "2026-01-15T12:00:00Z"),
        ("Europe/Bratislava", "15.07.2026 - 12:00", "2026-07-15T12:00:00Z"),
        ("Europe/Bratislava", "25.10.2026 - 02:30", "2026-10-25T02:30:00Z"),
        ("Europe/Bratislava", "29.03.2026 - 02:30", "2026-03-29T02:30:00Z"),
    ],
)
def test_fresh_migration_chain_corrects_rss_current_and_archived_publications(
    rss_db: tuple[ModuleType, ModuleType, sa.Connection],
    monkeypatch: pytest.MonkeyPatch,
    zone: str,
    legacy: str,
    expected: str,
) -> None:
    original, repair, connection = rss_db
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", zone)
    _insert_news(connection, "rss-item", 101, legacy)
    with Operations.context(MigrationContext.configure(connection)):
        original.upgrade()
        before = _published(connection)
        repair.upgrade()
        assert _published(connection) == {"news_item_data:rss-item": expected, "news_item_data_version:101": expected}
        for kind, item_id in (("news_item_data", "rss-item"), ("news_item_data_version", "101")):
            correction = _state(connection, f"rss_utc:{kind}", item_id)
            assert correction.original == before[f"{kind}:{item_id}"]
            assert correction.normalized == expected
            assert _state(connection, kind, item_id).normalized == expected
        repair.upgrade()
        assert _published(connection) == {"news_item_data:rss-item": expected, "news_item_data_version:101": expected}
        assert connection.execute(sa.text("SELECT count(*) FROM _utc_migration_state WHERE kind LIKE 'rss_utc:%'")).scalar_one() == 2
        repair.downgrade()
        assert _published(connection) == before
        assert connection.execute(sa.text("SELECT count(*) FROM _utc_migration_state WHERE kind LIKE 'rss_utc:%'")).scalar_one() == 0
        for kind, item_id in (("news_item_data", "rss-item"), ("news_item_data_version", "101")):
            assert _state(connection, kind, item_id).normalized == before[f"{kind}:{item_id}"]
        repair.upgrade()
        assert _published(connection) == {"news_item_data:rss-item": expected, "news_item_data_version:101": expected}
        repair.downgrade()
        original.downgrade()
        assert _published(connection) == {"news_item_data:rss-item": legacy, "news_item_data_version:101": legacy}


def test_repair_of_previously_migrated_database_retains_original_downgrade_compatibility(
    rss_db: tuple[ModuleType, ModuleType, sa.Connection],
) -> None:
    original, repair, connection = rss_db
    legacy = "15.07.2026 - 12:00"
    prior = "2026-07-15T10:00:00.000000Z"
    with Operations.context(MigrationContext.configure(connection)):
        original.upgrade()
        _insert_news(connection, "rss-existing", 42, prior)
        connection.execute(
            sa.text(
                "INSERT INTO _utc_migration_state (kind, item_id, original, normalized) VALUES "
                "('news_item_data', 'rss-existing', :legacy, :prior), ('news_item_data_version', '42', :legacy, :prior)",
            ),
            {"legacy": legacy, "prior": prior},
        )
        repair.upgrade()
        assert _published(connection) == {
            "news_item_data:rss-existing": "2026-07-15T12:00:00Z",
            "news_item_data_version:42": "2026-07-15T12:00:00Z",
        }
        # The original backup must still recognize publications changed by the repair.
        original.downgrade()
        assert _published(connection) == {"news_item_data:rss-existing": legacy, "news_item_data_version:42": legacy}


def test_unrelated_new_unlinked_and_edited_values_are_unchanged(
    rss_db: tuple[ModuleType, ModuleType, sa.Connection],
) -> None:
    original, repair, connection = rss_db
    cases = [
        ("email", "15.07.2026 - 12:00", "email-source"),
        ("web", "15.07.2026 - 12:00", "web-source"),
        ("unlinked", "15.07.2026 - 12:00", None),
        ("deleted-source", "15.07.2026 - 12:00", "deleted-source"),
        ("explicit-offset", "2026-07-15T12:00:00+03:00", "rss-source"),
        ("date-only", "2026-07-15", "rss-source"),
        ("unknown", "Yesterday", "rss-source"),
        ("seconds", "15.07.2026 - 12:00:00", "rss-source"),
        ("short-date", "5.7.2026 - 12:00", "rss-source"),
        ("invalid", "31.02.2026 - 12:00", "rss-source"),
        ("edited", "15.07.2026 - 12:00", "rss-source"),
    ]
    for index, (item_id, value, source_id) in enumerate(cases, start=1):
        _insert_news(connection, item_id, index, value, source_id)
    with Operations.context(MigrationContext.configure(connection)):
        original.upgrade()
        connection.execute(sa.text("UPDATE news_item_data SET published = '2026-07-15T20:00:00Z' WHERE id = 'edited'"))
        connection.execute(sa.text("UPDATE news_item_data_version SET published = '2026-07-15T20:00:00Z' WHERE news_item_data_id = 'edited'"))
        _insert_news(connection, "new-no-backup", 100, "2026-07-15T12:00:00Z")
        _insert_news(connection, "legacy-no-backup", 101, "15.07.2026 - 12:00")
        before = _published(connection)
        repair.upgrade()
        assert _published(connection) == before
        assert connection.execute(sa.text("SELECT count(*) FROM _utc_migration_state WHERE kind LIKE 'rss_utc:%'")).scalar_one() == 0
        repair.downgrade()
        assert _published(connection) == before


@pytest.mark.parametrize("metadata_edited", [False, True])
def test_repair_downgrade_preserves_subsequent_publication_and_metadata_edits(
    rss_db: tuple[ModuleType, ModuleType, sa.Connection],
    metadata_edited: bool,
) -> None:
    original, repair, connection = rss_db
    _insert_news(connection, "rss-edit", 7, "15.07.2026 - 12:00")
    with Operations.context(MigrationContext.configure(connection)):
        original.upgrade()
        prior = _published(connection)
        repair.upgrade()
        connection.execute(sa.text("UPDATE news_item_data SET published = '2026-07-15T15:00:00Z' WHERE id = 'rss-edit'"))
        connection.execute(sa.text("UPDATE news_item_data_version SET published = '2026-07-15T15:00:00Z' WHERE id = 7"))
        if metadata_edited:
            connection.execute(
                sa.text(
                    "UPDATE _utc_migration_state SET normalized = 'externally-edited' "
                    "WHERE kind IN ('news_item_data', 'news_item_data_version')",
                ),
            )
        repair.downgrade()
        expected = {"news_item_data:rss-edit": "2026-07-15T15:00:00Z", "news_item_data_version:7": "2026-07-15T15:00:00Z"}
        assert _published(connection) == expected
        for kind, item_id in (("news_item_data", "rss-edit"), ("news_item_data_version", "7")):
            saved = _state(connection, kind, item_id)
            assert saved.normalized == ("externally-edited" if metadata_edited else prior[f"{kind}:{item_id}"])
        assert connection.execute(sa.text("SELECT count(*) FROM _utc_migration_state WHERE kind LIKE 'rss_utc:%'")).scalar_one() == 0
        original.downgrade()
        assert _published(connection) == expected


def test_current_and_archived_publications_are_checked_independently(
    rss_db: tuple[ModuleType, ModuleType, sa.Connection],
) -> None:
    original, repair, connection = rss_db
    _insert_news(connection, "current-edited", 1, "15.07.2026 - 12:00")
    _insert_news(connection, "version-edited", 2, "15.07.2026 - 12:00")
    with Operations.context(MigrationContext.configure(connection)):
        original.upgrade()
        connection.execute(sa.text("UPDATE news_item_data SET published = 'current edit' WHERE id = 'current-edited'"))
        connection.execute(sa.text("UPDATE news_item_data_version SET published = 'version edit' WHERE id = 2"))
        repair.upgrade()
        assert _published(connection) == {
            "news_item_data:current-edited": "current edit",
            "news_item_data_version:1": "2026-07-15T12:00:00Z",
            "news_item_data:version-edited": "2026-07-15T12:00:00Z",
            "news_item_data_version:2": "version edit",
        }
        corrected = datetime.fromisoformat(_published(connection)["news_item_data:version-edited"])
        assert corrected.tzinfo is UTC


def test_repair_continues_after_a_page_of_nonmatching_original_formats(
    rss_db: tuple[ModuleType, ModuleType, sa.Connection],
) -> None:
    original, repair, connection = rss_db
    prior = "2026-07-15T10:00:00Z"
    with Operations.context(MigrationContext.configure(connection)):
        original.upgrade()
        # More than one page, including an entirely unrepairable first current-item
        # page. Archived integer IDs are ordered as strings by the migration.
        records = [
            {
                "id": f"a{index:04d}" if index < 1000 else f"z{index:04d}",
                "version_id": index + 1,
                "original": "15.07.2026 - 12:00:00" if index < 1000 else "15.07.2026 - 12:00",
                "prior": prior,
            }
            for index in range(1003)
        ]
        connection.execute(
            sa.text("INSERT INTO news_item_data (id, osint_source_id, published) VALUES (:id, 'rss-source', :prior)"),
            records,
        )
        connection.execute(
            sa.text("INSERT INTO news_item_data_version (id, news_item_data_id, published) VALUES (:version_id, :id, :prior)"),
            records,
        )
        backup_rows = [
            {"kind": kind, "item_id": row["id"] if kind == "news_item_data" else str(row["version_id"]), **row}
            for row in records
            for kind in ("news_item_data", "news_item_data_version")
        ]
        connection.execute(
            sa.text("INSERT INTO _utc_migration_state (kind, item_id, original, normalized) VALUES (:kind, :item_id, :original, :prior)"),
            backup_rows,
        )
        repair.upgrade()
        published = _published(connection)
        for row in records:
            expected = prior if row["original"] == "15.07.2026 - 12:00:00" else "2026-07-15T12:00:00Z"
            assert published[f"news_item_data:{row['id']}"] == expected
            assert published[f"news_item_data_version:{row['version_id']}"] == expected
        assert connection.execute(sa.text("SELECT count(*) FROM _utc_migration_state WHERE kind LIKE 'rss_utc:%'")).scalar_one() == 6
