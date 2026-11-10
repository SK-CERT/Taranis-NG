"""The manual entry migration matches the model, tolerates create_all and deletes in a safe order.

``9c4e2a7b5d13`` adds who entered an item by hand to ``news_item_data`` and removes the manual
OSINT sources and collectors. Like the other migration tests, these need no database.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

from model.news_item import NewsItemData

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "9c4e2a7b5d13_manual_entry_without_sources.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("manual_entry_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _children(revision: str) -> list[str]:
    revises = re.compile(rf'^down_revision = "{revision}"$', re.MULTILINE)
    return [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]


def _upgrade_source() -> str:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    return ast.unparse(next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "upgrade"))


def test_the_migration_extends_the_public_web_templates_head() -> None:
    module = _load()
    assert module.revision == "9c4e2a7b5d13"
    assert module.down_revision == "7d3b9e5f1a2c"
    assert _children("7d3b9e5f1a2c") == [MIGRATION.name]
    # Followed only by the index revision (test_api_indexes_migration.py).
    assert _children("9c4e2a7b5d13") == ["4b8e6d2a9c71_api_indexes.py"]


def test_it_adds_what_the_model_declares_and_tolerates_create_all() -> None:
    module = _load()
    table = NewsItemData.__table__
    assert table.name == module.TABLE
    source = MIGRATION.read_text(encoding="utf-8")
    for name in ("entered_by", "entered_by_user_id", "source_label"):
        assert table.c[name].nullable is True
        # A fresh database has the column from create_all(); it must not be added twice.
        assert f'if "{name}" not in columns:' in source
    (fk,) = table.c["entered_by_user_id"].foreign_keys
    assert (fk.column.table.name, fk.column.name, fk.ondelete) == ("user", "id", "SET NULL")


def test_it_deletes_children_before_their_parents() -> None:
    body = _upgrade_source()
    order = [
        "UPDATE news_item_data SET osint_source_id = NULL",
        "DELETE FROM acl_entry_role",
        "DELETE FROM acl_entry_user",
        "DELETE FROM acl_entry WHERE",
        "DELETE FROM parameter_value",
        "DELETE FROM osint_source WHERE",
        "DELETE FROM parameter WHERE",
        "DELETE FROM collector WHERE",
    ]
    positions = [body.index(statement) for statement in order]
    assert positions == sorted(positions)


def test_only_the_manual_collector_type_is_touched() -> None:
    module = _load()
    assert module.MANUAL_COLLECTORS == "SELECT id FROM collector WHERE type = 'MANUAL_COLLECTOR'"
    assert module.MANUAL_SOURCES.startswith("SELECT id FROM osint_source WHERE collector_id IN (")
    assert module.MANUAL_SOURCES.endswith(f"({module.MANUAL_COLLECTORS})")
