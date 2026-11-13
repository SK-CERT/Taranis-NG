"""The product report order migration adds the position, numbers existing rows once and is the head."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "5e5fd7e294ca_product_report_order.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("product_report_order_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _children(revision: str) -> list[str]:
    revises = re.compile(rf'^down_revision = "{revision}"$', re.MULTILINE)
    return [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]


class _Op:
    """Records what the migration asks alembic to do."""

    def __init__(self) -> None:
        self.calls: list = []

    def add_column(self, table: str, column: object) -> None:
        self.calls.append(("add_column", table, column))

    def drop_column(self, table: str, column: str) -> None:
        self.calls.append(("drop_column", table, column))

    def execute(self, statement: object) -> None:
        self.calls.append(("execute", str(statement)))


@pytest.fixture
def migration(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, _Op]:
    module = _load()
    op = _Op()
    monkeypatch.setattr(module, "op", op)
    return module, op


def test_the_migration_extends_the_api_indexes_and_is_the_head() -> None:
    module = _load()
    assert (module.revision, module.down_revision) == ("5e5fd7e294ca", "4b8e6d2a9c71")
    assert _children("4b8e6d2a9c71") == [MIGRATION.name]
    assert _children("5e5fd7e294ca") == []


def test_the_column_is_the_one_the_model_declares(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    from model.product import ProductReportItem  # noqa: PLC0415 - after the stub config is in place

    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.upgrade()

    (_add, table, column), _backfill = op.calls
    declared = ProductReportItem.__table__.c.position
    assert (table, column.name) == ("product_report_item", "position")
    assert (column.nullable, column.server_default.arg) == (declared.nullable, declared.server_default.arg)
    assert type(column.type) is type(declared.type)


def test_existing_rows_are_numbered_per_product_by_report_id(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.upgrade()

    _add, (kind, statement) = op.calls
    assert kind == "execute"
    sql = " ".join(statement.split())
    # The order loading a product returned until now: its primary key index, by report id.
    assert "row_number() OVER (PARTITION BY product_id ORDER BY report_item_id) - 1" in sql
    assert "link.product_id = ordered.product_id AND link.report_item_id = ordered.report_item_id" in sql


def test_a_column_create_all_made_is_left_alone(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh database has it from create_all() before the migration runs; nothing is renumbered.
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: True)
    module.upgrade()

    assert op.calls == []


def test_downgrade_drops_the_column(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: True)
    module.downgrade()

    assert op.calls == [("drop_column", "product_report_item", "position")]


def test_downgrade_without_the_column_does_nothing(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.downgrade()

    assert op.calls == []
