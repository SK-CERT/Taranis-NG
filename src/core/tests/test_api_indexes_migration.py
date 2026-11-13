"""The index migration creates exactly the indexes the models declare, and tolerates create_all."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

from managers.db_manager import db

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "4b8e6d2a9c71_api_indexes.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("api_indexes_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _children(revision: str) -> list[str]:
    revises = re.compile(rf'^down_revision = "{revision}"$', re.MULTILINE)
    return [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]


def test_the_migration_extends_the_manual_entry_head() -> None:
    module = _load()
    assert (module.revision, module.down_revision) == ("4b8e6d2a9c71", "9c4e2a7b5d13")
    assert _children("9c4e2a7b5d13") == [MIGRATION.name]
    # The product report order came next.
    assert _children("4b8e6d2a9c71") == ["5e5fd7e294ca_product_report_order.py"]


def test_each_index_is_the_one_its_model_declares() -> None:
    import model.acl_entry  # noqa: PLC0415
    import model.news_item  # noqa: PLC0415
    import model.report_item  # noqa: PLC0415
    import model.token_blacklist  # noqa: F401, PLC0415

    declared = {
        index.name: (table.name, [column.name for column in index.columns]) for table in db.metadata.sorted_tables for index in table.indexes
    }
    for name, table, columns in _load().INDEXES:
        assert declared.get(name) == (table, columns), name


def test_existing_indexes_are_left_alone() -> None:
    # A fresh database has them from create_all() before the migration runs.
    source = MIGRATION.read_text(encoding="utf-8")
    assert "if_not_exists=True" in source
    assert "if_exists=True" in source
