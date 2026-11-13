"""The publication time migration adds the column, fills it for published products once, and is the head."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "5c915192b607_product_published_at.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("product_published_at_migration", MIGRATION)
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
        self.calls.append(("execute", " ".join(str(statement).split())))


@pytest.fixture
def migration(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, _Op]:
    module = _load()
    op = _Op()
    monkeypatch.setattr(module, "op", op)
    return module, op


def test_the_migration_follows_the_report_order_and_is_the_head() -> None:
    module = _load()
    assert (module.revision, module.down_revision) == ("5c915192b607", "5e5fd7e294ca")
    assert _children("5e5fd7e294ca") == [MIGRATION.name]
    assert _children("5c915192b607") == []


def test_the_column_is_the_one_the_model_declares(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    from model.product import Product  # noqa: PLC0415 - after the stub config is in place

    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.upgrade()

    (_add, table, column), _backfill = op.calls
    declared = Product.__table__.c.published_at
    assert (table, column.name, column.nullable) == ("product", "published_at", declared.nullable)
    assert type(column.type) is type(declared.type)


def test_published_products_get_their_creation_time(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    from model.state import StateEnum  # noqa: PLC0415

    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.upgrade()

    _add, (kind, sql) = op.calls
    assert kind == "execute"
    assert "SET published_at = created" in sql
    # Only those in the published state, which StateDefinition.get_by_name finds by display name.
    wanted = f"WHERE published_at IS NULL AND state_id IN (SELECT id FROM state WHERE display_name = '{StateEnum.PUBLISHED.value}')"  # noqa: S608
    assert wanted in sql


def test_a_column_create_all_made_is_left_alone(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: True)
    module.upgrade()

    assert op.calls == []


def test_downgrade_drops_the_column(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: True)
    module.downgrade()

    assert op.calls == [("drop_column", "product", "published_at")]


def test_downgrade_without_the_column_does_nothing(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.downgrade()

    assert op.calls == []
