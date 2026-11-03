"""Exercise the UTC data migration on an explicitly configured disposable PostgreSQL DB.

Set TARANIS_TEST_POSTGRES_URL to run the integration cases. Each case creates and
removes a separate schema; an existing application's tables are never used.
"""

import ast
import importlib.util
import os
import re
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

MIGRATION_PATH = Path(__file__).parents[1] / "migrations" / "versions" / "a61c9e42f730_utc_timestamps.py"


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("utc_timestamp_migration", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def migration_db() -> Iterator[tuple[ModuleType, sa.Connection]]:
    url = os.environ.get("TARANIS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TARANIS_TEST_POSTGRES_URL is not set (disposable PostgreSQL integration database)")
    engine = sa.create_engine(url)
    schema = f"utc_test_{uuid4().hex}"
    migration = _migration()
    try:
        with engine.begin() as connection:
            connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            connection.execute(sa.text("SET LOCAL TIME ZONE 'Europe/Bratislava'"))
            for table, columns in migration.TIMESTAMP_COLUMNS.items():
                extras = ""
                if table in {"news_item_data", "news_item_data_version"}:
                    extras = ", published text"
                elif table == "report_item_attribute":
                    extras = ", value text, attribute_group_item_id integer"
                definitions = ", ".join(f'"{column}" timestamp' for column in columns)
                connection.execute(sa.text(f'CREATE TABLE "{table}" (id integer PRIMARY KEY, {definitions}{extras})'))
            for table, columns in migration.PRESERVED_AWARE_COLUMNS.items():
                definitions = ", ".join(f'"{column}" timestamptz' for column in columns)
                connection.execute(sa.text(f'CREATE TABLE "{table}" (id integer PRIMARY KEY, {definitions})'))
            connection.execute(sa.text("CREATE TABLE attribute (id integer PRIMARY KEY, type text, default_value text)"))
            connection.execute(sa.text("CREATE TABLE attribute_group_item (id integer PRIMARY KEY, attribute_id integer)"))
            yield migration, connection
    finally:
        with engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_original_timezone_setting_is_preserved_and_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    migration = _migration()
    monkeypatch.setenv("TZ", "Europe/Bratislava")
    monkeypatch.delenv("TARANIS_NG_LEGACY_TZ", raising=False)
    assert migration._legacy_zone() == "Europe/Bratislava"
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "UTC")
    assert migration._legacy_zone() == "UTC"
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "Not/A/Timezone")
    with pytest.raises(ZoneInfoNotFoundError):
        migration._legacy_zone()
    monkeypatch.delenv("TARANIS_NG_LEGACY_TZ")
    monkeypatch.delenv("TZ")
    assert migration._legacy_zone() == "UTC"


@pytest.mark.parametrize("value", [None, "", "2026-11-02", "20261102", "2026-W45-1", "date unknown", "02.11.2026"])
def test_text_parser_preserves_dates_and_source_text(value: str | None) -> None:
    assert _migration()._parse_timestamp(value) is None


@pytest.mark.parametrize(
    ("zone", "wall_clock", "expected"),
    [
        ("Europe/Bratislava", "2026-01-15 12:00:00", "2026-01-15T11:00:00+00:00"),
        ("Europe/Bratislava", "2026-07-15 12:00:00", "2026-07-15T10:00:00+00:00"),
        ("Europe/Bratislava", "2026-10-25 02:30:00", "2026-10-25T01:30:00+00:00"),
        ("Europe/Bratislava", "2026-03-29 02:30:00", "2026-03-29T01:30:00+00:00"),
        ("UTC", "2026-07-15 12:00:00", "2026-07-15T12:00:00+00:00"),
    ],
)
def test_upgrade_and_downgrade_preserve_instants_and_original_text(
    migration_db: tuple[ModuleType, sa.Connection],
    monkeypatch: pytest.MonkeyPatch,
    zone: str,
    wall_clock: str,
    expected: str,
) -> None:
    migration, connection = migration_db
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", zone)
    monkeypatch.setenv("TZ", "UTC")
    naive = datetime.fromisoformat(wall_clock)
    connection.execute(sa.text('INSERT INTO "product" (id, created) VALUES (1, :value), (2, NULL)'), {"value": naive})
    connection.execute(
        sa.text(
            "INSERT INTO news_item_data (id, published) VALUES (1, :value), (2, '2026-07-15'), (3, 'Unknown'), "
            "(4, '2026-07-15T12:00:00+03:00')",
        ),
        {"value": wall_clock},
    )
    connection.execute(
        sa.text("INSERT INTO news_item_data_version (id, published, collected, superseded) VALUES (1, :value, :stamp, :stamp)"),
        {"value": wall_clock, "stamp": naive},
    )
    connection.execute(sa.text("INSERT INTO notification_outbox (id, created_at) VALUES (1, '2026-07-15T12:00:00+03:00')"))
    connection.execute(
        sa.text("INSERT INTO attribute (id, type, default_value) VALUES (1, 'DATE_TIME', :value), (2, 'DATE', '2026-07-15')"),
        {"value": wall_clock},
    )
    connection.execute(sa.text("INSERT INTO attribute_group_item (id, attribute_id) VALUES (1, 1), (2, 2)"))
    connection.execute(
        sa.text("INSERT INTO report_item_attribute (id, value, attribute_group_item_id) VALUES (1, :value, 1), (2, '2026-07-15', 2)"),
        {"value": wall_clock},
    )
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        created = connection.execute(sa.text("SELECT created FROM product WHERE id = 1")).scalar_one()
        assert created.astimezone(UTC).isoformat() == expected
        assert connection.execute(sa.text("SELECT created FROM product WHERE id = 2")).scalar_one() is None
        published = dict(connection.execute(sa.text("SELECT id, published FROM news_item_data")).all())
        assert datetime.fromisoformat(published[1]).isoformat() == expected
        assert published[1].endswith("Z")
        assert published[2] == "2026-07-15"
        assert published[3] == "Unknown"
        assert published[4] == "2026-07-15T09:00:00Z"
        version = connection.execute(sa.text("SELECT published, collected, superseded FROM news_item_data_version WHERE id = 1")).one()
        assert version.published == published[1]
        assert version.collected.astimezone(UTC).isoformat() == expected
        assert version.superseded.astimezone(UTC).isoformat() == expected
        notification = connection.execute(sa.text("SELECT created_at FROM notification_outbox WHERE id = 1")).scalar_one()
        assert notification.astimezone(UTC).isoformat() == "2026-07-15T09:00:00+00:00"
        values = dict(connection.execute(sa.text("SELECT id, value FROM report_item_attribute")).all())
        assert values[1] == published[1]
        assert values[2] == "2026-07-15"
        defaults = dict(connection.execute(sa.text("SELECT id, default_value FROM attribute")).all())
        assert defaults[1] == published[1]
        assert defaults[2] == "2026-07-15"
        column_types = connection.execute(
            sa.text("SELECT data_type FROM information_schema.columns WHERE table_schema = current_schema() AND column_name = 'created'"),
        )
        assert all(row.data_type == "timestamp with time zone" for row in column_types)
        # A later user edit must survive downgrade rather than being overwritten by the backup.
        connection.execute(sa.text("UPDATE news_item_data SET published = 'edited' WHERE id = 4"))
        monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "Pacific/Auckland")
        migration.downgrade()
        restored = connection.execute(sa.text("SELECT created FROM product WHERE id = 1")).scalar_one()
        # A nonexistent wall time normalizes to the real clock time PostgreSQL selected.
        expected_wall = "2026-03-29 03:30:00" if wall_clock == "2026-03-29 02:30:00" else wall_clock
        assert restored == datetime.fromisoformat(expected_wall)
        assert connection.execute(sa.text("SELECT published FROM news_item_data WHERE id = 1")).scalar_one() == wall_clock
        assert connection.execute(sa.text("SELECT published FROM news_item_data WHERE id = 4")).scalar_one() == "edited"
        assert connection.execute(sa.text("SELECT value FROM report_item_attribute WHERE id = 1")).scalar_one() == wall_clock
        assert connection.execute(sa.text("SELECT default_value FROM attribute WHERE id = 1")).scalar_one() == wall_clock
        assert connection.execute(sa.text("SELECT published FROM news_item_data_version WHERE id = 1")).scalar_one() == wall_clock
        restored_notification = connection.execute(sa.text("SELECT created_at FROM notification_outbox WHERE id = 1")).scalar_one()
        assert restored_notification == notification


def test_migration_covers_every_active_model_timestamp_column() -> None:
    models = {}
    expected = {}
    for path in (MIGRATION_PATH.parents[2] / "model").glob("*.py"):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef):
                models[node.name] = node
            elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "db.Table":
                table = ast.literal_eval(node.value.args[0])
                columns = [
                    ast.literal_eval(column.args[0])
                    for column in node.value.args[1:]
                    if isinstance(column, ast.Call)
                    and ast.unparse(column.func) == "db.Column"
                    and len(column.args) > 1
                    and ast.unparse(column.args[1]).startswith("db.DateTime")
                ]
                if columns:
                    expected[table] = tuple(columns)

    def timestamp_columns(node: ast.ClassDef) -> list[str]:
        columns = []
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in models:
                columns.extend(timestamp_columns(models[base.id]))
        for assignment in node.body:
            if not isinstance(assignment, ast.Assign):
                continue
            for target in assignment.targets:
                value = assignment.value
                if (
                    isinstance(target, ast.Name)
                    and isinstance(value, ast.Call)
                    and ast.unparse(value.func) == "db.Column"
                    and any(ast.unparse(argument).startswith("db.DateTime") for argument in value.args)
                ):
                    columns.append(target.id)
        return columns

    for node in models.values():
        if not any(ast.unparse(base) == "db.Model" for base in node.bases):
            continue
        table = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", node.name)
        table = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", table).lower()
        for assignment in node.body:
            if isinstance(assignment, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__tablename__" for target in assignment.targets
            ):
                table = ast.literal_eval(assignment.value)
        columns = timestamp_columns(node)
        if columns:
            expected[table] = tuple(columns)
    # This orphaned model is not imported by core and has no creating migration.
    # The UTC migration deliberately excludes it after the startup failure it caused.
    expected.pop("audit_record", None)
    migration = _migration()
    assert expected == migration.TIMESTAMP_COLUMNS | migration.PRESERVED_AWARE_COLUMNS
