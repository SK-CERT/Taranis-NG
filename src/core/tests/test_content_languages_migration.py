"""The content languages migration matches the models and can run on a database that has its tables.

``d0ce8c7edcd9`` adds the language columns, the two translation tables and the AI provider TLP
limit. A core started with the new models creates the tables itself (``db.create_all()``), so the
migration checks before creating anything; and what it creates must be what the models declare.
It must not guess the language of existing reports. Like the other migration tests, these need
no database.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import sqlalchemy as sa
from model.ai_provider import AiProvider
from model.report_item import ReportItem
from model.report_item_type import AttributeGroup, AttributeGroupItem, ReportItemType
from model.translation import ReportItemAttributeTranslation, ReportItemTranslation

if TYPE_CHECKING:
    from types import ModuleType

CORE_ROOT = Path(__file__).parents[1]
VERSIONS = CORE_ROOT / "migrations" / "versions"
MIGRATION = VERSIONS / "d0ce8c7edcd9_content_languages.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("content_languages_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_extends_the_notifications_head() -> None:
    module = _load()
    assert module.revision == "d0ce8c7edcd9"
    assert module.down_revision == "1f928d40433c"
    revises = re.compile(r'^down_revision = "1f928d40433c"$', re.MULTILINE)
    children = [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]
    assert children == [MIGRATION.name]


def test_existing_tables_columns_and_indexes_are_reused() -> None:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    functions = {node.name: ast.unparse(node) for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "if TITLE_TABLE not in tables" in functions["_create_tables"]
    assert "if ATTRIBUTE_TABLE not in tables" in functions["_create_tables"]
    assert "if TITLE_INDEX not in" in functions["_create_tables"]
    assert "if ATTRIBUTE_INDEX not in" in functions["_create_tables"]
    assert "if column.name not in present" in functions["_add_columns"]
    assert "if PROVIDER_FK not in foreign_keys" in functions["_add_columns"]


def test_the_migration_creates_what_the_models_declare() -> None:
    module = _load()
    assert ReportItemTranslation.__tablename__ == module.TITLE_TABLE
    assert ReportItemAttributeTranslation.__tablename__ == module.ATTRIBUTE_TABLE
    assert module.TITLE_INDEX in {index.name for index in ReportItemTranslation.__table__.indexes}
    assert module.ATTRIBUTE_INDEX in {index.name for index in ReportItemAttributeTranslation.__table__.indexes}
    assert module.PROVIDER_FK in {key.name for key in ReportItemType.__table__.foreign_keys}

    models = {
        "report_item_type": ReportItemType,
        "attribute_group": AttributeGroup,
        "attribute_group_item": AttributeGroupItem,
        "report_item": ReportItem,
        "ai_provider": AiProvider,
    }
    for table, columns in module._columns().items():
        model_columns = models[table].__table__.columns
        for column in columns:
            assert column.name in model_columns, f"{table}.{column.name}"
            assert column.nullable == model_columns[column.name].nullable, f"{table}.{column.name}"

    shared = {column.name for column in module._translation_columns() if isinstance(column, sa.Column)}
    for model in (ReportItemTranslation, ReportItemAttributeTranslation):
        assert shared <= {column.name for column in model.__table__.columns}


def test_existing_reports_get_no_guessed_language() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    upgrade = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "upgrade")
    # Only schema changes: no statement fills report_item.language or touches settings.
    assert "execute" not in ast.unparse(upgrade)
    assert "sa.text(" not in source.replace("sa.text(\"'[]'\")", "").replace("sa.text(\"'{}'\")", "")
