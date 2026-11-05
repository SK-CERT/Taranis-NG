"""Legacy remote timezone defaults survive deployments whose runtime already uses UTC.

Database cases require TARANIS_TEST_POSTGRES_URL and isolate their two remote tables
in a temporary PostgreSQL schema; no existing application's tables are touched.
"""

# Identifiers come only from the frozen table list and UUID-generated schemas.
# ruff: noqa: S608

import importlib.util
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4
from zoneinfo import ZoneInfoNotFoundError

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRATION_PATH = Path(__file__).parents[1] / "migrations" / "versions" / "d8f7a401c952_remote_api_versions.py"
TABLES = ("remote_access", "remote_node")
STAMP = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("remote_timezone_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def remote_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[ModuleType, sa.Connection]]:
    url = os.environ.get("TARANIS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TARANIS_TEST_POSTGRES_URL is not set (disposable PostgreSQL integration database)")
    monkeypatch.delenv("TARANIS_NG_LEGACY_TZ", raising=False)
    monkeypatch.delenv("TZ", raising=False)
    engine = sa.create_engine(url)
    schema = f"remote_tz_test_{uuid4().hex}"
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            connection.execute(sa.text("SET LOCAL TIME ZONE 'UTC'"))
            connection.execute(
                sa.text("CREATE TABLE remote_access (id integer PRIMARY KEY, marker text, last_synced_news_items timestamptz)"),
            )
            connection.execute(
                sa.text("CREATE TABLE remote_node (id varchar(64) PRIMARY KEY, marker text, last_synced_news_items timestamptz)"),
            )
            for table in TABLES:
                connection.execute(
                    sa.text(
                        f"INSERT INTO {table} (id, marker, last_synced_news_items) VALUES ('1', 'first', :stamp), ('2', 'second', :stamp)",
                    ),
                    {"stamp": STAMP},
                )
            yield _migration(), connection
    finally:
        with engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def _saved_timezone(connection: sa.Connection, zone: str | None) -> None:
    connection.execute(
        sa.text("CREATE TABLE _utc_migration_state (kind text, item_id text, original text, normalized text, PRIMARY KEY (kind, item_id))"),
    )
    if zone is not None:
        connection.execute(
            sa.text("INSERT INTO _utc_migration_state (kind, item_id, original) VALUES ('timezone', '', :zone)"),
            {"zone": zone},
        )


def _zones(connection: sa.Connection, table: str) -> list[str]:
    return list(connection.execute(sa.text(f"SELECT legacy_timezone FROM {table} ORDER BY id")).scalars())


def test_remote_timezone_revision_follows_rss_repair() -> None:
    migration = _migration()
    assert migration.revision == "d8f7a401c952"
    assert migration.down_revision == "b7e4d192a630"


def test_saved_original_timezone_overrides_utc_runtime_and_survives_downgrade(
    remote_db: tuple[ModuleType, sa.Connection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration, connection = remote_db
    _saved_timezone(connection, "Europe/Bratislava")
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "UTC")
    monkeypatch.setenv("TZ", "UTC")
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        for table in TABLES:
            assert _zones(connection, table) == ["Europe/Bratislava", "Europe/Bratislava"]
            columns = {column["name"]: column for column in sa.inspect(connection).get_columns(table)}
            assert columns["legacy_timezone"]["nullable"] is False
            zone_type = columns["legacy_timezone"]["type"]
            assert isinstance(zone_type, sa.String)
            assert zone_type.length == 128
            default = columns["legacy_timezone"]["default"]
            assert default is not None
            assert "UTC" in default
            connection.execute(sa.text(f"INSERT INTO {table} (id, marker) VALUES ('3', 'new')"))
            assert _zones(connection, table)[-1] == "UTC"
            rows = connection.execute(sa.text(f"SELECT marker, last_synced_news_items FROM {table} WHERE id IN ('1', '2') ORDER BY id")).all()
            assert rows == [("first", STAMP), ("second", STAMP)]
        migration.downgrade()
        for table in TABLES:
            assert {column["name"] for column in sa.inspect(connection).get_columns(table)} == {"id", "marker", "last_synced_news_items"}
            assert connection.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one() == 3
        saved_zone = connection.execute(sa.text("SELECT original FROM _utc_migration_state WHERE kind = 'timezone'")).scalar_one()
        assert saved_zone == "Europe/Bratislava"


@pytest.mark.parametrize(
    ("legacy_env", "tz_env", "empty_state", "expected"),
    [
        ("Europe/Bratislava", "UTC", False, "Europe/Bratislava"),
        (None, "America/New_York", False, "America/New_York"),
        (None, None, False, "UTC"),
        ("", "Europe/Bratislava", False, "Europe/Bratislava"),
        ("Europe/Bratislava", "UTC", True, "Europe/Bratislava"),
    ],
)
def test_timezone_defaults_follow_saved_legacy_then_process_then_utc_fallback(
    remote_db: tuple[ModuleType, sa.Connection],
    monkeypatch: pytest.MonkeyPatch,
    legacy_env: str | None,
    tz_env: str | None,
    empty_state: bool,
    expected: str,
) -> None:
    migration, connection = remote_db
    if empty_state:
        _saved_timezone(connection, None)
    if legacy_env is not None:
        monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", legacy_env)
    if tz_env is not None:
        monkeypatch.setenv("TZ", tz_env)
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        for table in TABLES:
            assert _zones(connection, table) == [expected, expected]


@pytest.mark.parametrize("invalid_source", ["saved", "legacy_env", "tz_env"])
def test_invalid_source_timezone_fails_before_any_schema_change(
    remote_db: tuple[ModuleType, sa.Connection],
    monkeypatch: pytest.MonkeyPatch,
    invalid_source: str,
) -> None:
    migration, connection = remote_db
    if invalid_source == "saved":
        _saved_timezone(connection, "Not/A/Timezone")
        monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "UTC")
    elif invalid_source == "legacy_env":
        monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "Not/A/Timezone")
        monkeypatch.setenv("TZ", "UTC")
    else:
        monkeypatch.setenv("TZ", "Not/A/Timezone")
    before = {table: {column["name"] for column in sa.inspect(connection).get_columns(table)} for table in TABLES}
    with Operations.context(MigrationContext.configure(connection)), pytest.raises(ZoneInfoNotFoundError):
        migration.upgrade()
    for table in TABLES:
        assert {column["name"] for column in sa.inspect(connection).get_columns(table)} == before[table]
        assert connection.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one() == 2


@pytest.mark.parametrize("preexisting_tables", [("remote_access",), ("remote_node",), TABLES])
def test_preexisting_create_all_configuration_is_preserved_on_repeated_upgrade(
    remote_db: tuple[ModuleType, sa.Connection],
    preexisting_tables: tuple[str, ...],
) -> None:
    migration, connection = remote_db
    _saved_timezone(connection, "Europe/Bratislava")
    for table in preexisting_tables:
        connection.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN legacy_timezone varchar(128) NOT NULL DEFAULT 'UTC'"))
        connection.execute(sa.text(f"UPDATE {table} SET legacy_timezone = CASE WHEN id = '1' THEN 'America/New_York' ELSE 'Asia/Tokyo' END"))
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        for table in TABLES:
            expected = ["America/New_York", "Asia/Tokyo"] if table in preexisting_tables else ["Europe/Bratislava", "Europe/Bratislava"]
            assert _zones(connection, table) == expected
        migration.upgrade()
        for table in TABLES:
            expected = ["America/New_York", "Asia/Tokyo"] if table in preexisting_tables else ["Europe/Bratislava", "Europe/Bratislava"]
            assert _zones(connection, table) == expected


def test_valid_saved_timezone_ignores_obsolete_invalid_environment_override(
    remote_db: tuple[ModuleType, sa.Connection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration, connection = remote_db
    _saved_timezone(connection, "UTC")
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "Not/A/Timezone")
    monkeypatch.setenv("TZ", "Not/A/Timezone")
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        for table in TABLES:
            assert _zones(connection, table) == ["UTC", "UTC"]
