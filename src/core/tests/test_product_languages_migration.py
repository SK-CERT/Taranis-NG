"""The product languages migration matches the models and can run on a database that has its table.

``4bc3bad77008`` adds constant translations, the product's language and translated titles, and
per-language templates of product types. It must not guess any language. No database needed.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

from model.attribute import AttributeEnum
from model.product import Product
from model.product_type import ProductType
from model.translation import ProductTranslation

if TYPE_CHECKING:
    from types import ModuleType

CORE_ROOT = Path(__file__).parents[1]
VERSIONS = CORE_ROOT / "migrations" / "versions"
MIGRATION = VERSIONS / "4bc3bad77008_product_languages.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("product_languages_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_extends_the_report_languages_head() -> None:
    module = _load()
    assert module.revision == "4bc3bad77008"
    assert module.down_revision == "d0ce8c7edcd9"
    revises = re.compile(r'^down_revision = "d0ce8c7edcd9"$', re.MULTILINE)
    children = [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]
    assert children == [MIGRATION.name]


def test_an_existing_table_columns_and_index_are_reused() -> None:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    functions = {node.name: ast.unparse(node) for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "if PRODUCT_TABLE not in" in functions["_create_tables"]
    assert "if PRODUCT_INDEX not in" in functions["_create_tables"]
    assert "if column.name not in present" in functions["_add_columns"]


def test_the_migration_creates_what_the_models_declare() -> None:
    module = _load()
    assert ProductTranslation.__tablename__ == module.PRODUCT_TABLE
    assert module.PRODUCT_INDEX in {index.name for index in ProductTranslation.__table__.indexes}
    models = {"attribute_enum": AttributeEnum, "product": Product, "product_type": ProductType}
    for table, columns in module._columns().items():
        model_columns = models[table].__table__.columns
        for column in columns:
            assert column.name in model_columns, f"{table}.{column.name}"
            assert column.nullable == model_columns[column.name].nullable, f"{table}.{column.name}"


def test_existing_products_get_no_guessed_language() -> None:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    upgrade = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "upgrade")
    assert "execute" not in ast.unparse(upgrade)
