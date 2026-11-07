"""Static checks of the migration that brings product formats, publishing channels and presets.

``72f1a157e289`` renames product types and publisher presets, creates product presets from the
product types, and adds what came with them: delivery languages, icons, keeping a product off the
public web, and the index on attribute constants. Like the other migration tests here, these
need no database: the revision chain is read from the migration's source, and what it makes is
compared with the models. The migration itself was run against Postgres 16 on a copy of a
production database (upgrade, downgrade, upgrade again) and its schema compared with create_all's.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from model.attribute import AttributeEnum
from model.product import Product, ProductPublicWeb
from model.product_format import ProductFormat, ProductFormatParameterValue
from model.product_preset import ProductPreset, ProductPresetDelivery, ProductPresetPublicWeb
from model.publishing_channel import PublishingChannel, PublishingChannelParameterValue
from model.report_item_type import ReportItemType
from shared.schema.acl_entry import ItemType

if TYPE_CHECKING:
    from types import ModuleType

CORE_ROOT = Path(__file__).parents[1]
VERSIONS = CORE_ROOT / "migrations" / "versions"
MIGRATION = VERSIONS / "72f1a157e289_products.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("products_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _function(name: str) -> ast.FunctionDef:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"), filename=str(MIGRATION))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    message = f"{name} is not defined"
    raise AssertionError(message)


def _source(name: str) -> str:
    return ast.unparse(_function(name))


def test_the_migration_extends_the_parameter_translate_head() -> None:
    module = _load()
    assert (module.revision, module.down_revision) == ("72f1a157e289", "c580a8db010f")
    revises = re.compile(r'^down_revision = "c580a8db010f"$', re.MULTILINE)
    children = [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]
    assert children == [MIGRATION.name]


def test_the_enum_label_is_committed_before_anything_uses_it() -> None:
    source = _source("upgrade")
    assert source.index("autocommit_block") < source.index("_drop_premature_tables")
    assert source.index("autocommit_block") < source.index("_move_acl_entries")
    assert "ADD VALUE IF NOT EXISTS" in source


def test_the_acl_label_is_the_item_type() -> None:
    module = _load()
    assert ItemType[module.PRODUCT_PRESET_ITEM].name == module.PRODUCT_PRESET_ITEM
    assert not hasattr(ItemType, module.PRODUCT_TYPE_ITEM)


def test_the_renamed_tables_and_columns_are_the_models() -> None:
    module = _load()
    words = module._words(upgrade=True)
    models = (ProductFormat, ProductFormatParameterValue, PublishingChannel, PublishingChannelParameterValue)
    tables = {model.__table__.name: model.__table__ for model in models}
    assert {module._rename(table, words) for table in module._renamed_tables(upgrade=True)} == set(tables)
    assert module._rename("product_type_id", words) in tables["product_format_parameter_value"].c
    assert module._rename("publisher_preset_id", words) in tables["publishing_channel_parameter_value"].c


def test_constraints_get_the_names_postgres_gives_the_new_tables() -> None:
    module = _load()
    words, back = module._words(upgrade=True), module._words(upgrade=False)
    assert (
        module._rename("product_type_parameter_value_product_type_id_fkey", words) == "product_format_parameter_value_product_format_id_fkey"
    )
    for name in ("publisher_preset_parameter_value_publisher_preset_id_fkey", "product_type_id_seq", "publisher_preset_pkey"):
        assert module._rename(module._rename(name, words), back) == name


def test_tables_made_by_create_all_are_dropped_before_anything_is_made() -> None:
    module = _load()
    source = _source("upgrade")
    assert source.index("_drop_premature_tables") < source.index("_rename_schema") < source.index("_create_preset_tables")
    assert "count(*)" in _source("_drop_premature_tables")
    assert {model.__table__.name for model in (ProductPreset, ProductPresetDelivery, ProductPresetPublicWeb)} == set(module.PRESET_TABLES)


class _Recorder:
    """Stands in for ``op``: keeps the tables a function creates and the columns it adds."""

    def __init__(self) -> None:
        self.tables: dict[str, sa.Table] = {}
        self.columns: dict[tuple[str, str], sa.Column] = {}
        self.indexes: dict[str, tuple[str, list[str]]] = {}

    def create_table(self, name: str, *elements: object) -> None:
        self.tables[name] = sa.Table(name, sa.MetaData(), *elements)

    def add_column(self, table: str, column: sa.Column) -> None:
        self.columns[table, column.name] = column

    def create_index(self, name: str, table: str, columns: list[str]) -> None:
        self.indexes[name] = (table, columns)


def _shape(table: sa.Table) -> dict:
    """What a table is, as far as the models and a migration must agree."""
    columns = {
        column.name: (type(column.type).__name__, getattr(column.type, "length", None), column.nullable, column.primary_key)
        for column in table.columns
    }
    keys = {
        (
            tuple(key.parent.name for key in constraint.elements),
            tuple(key.target_fullname for key in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
    }
    unique = {
        (constraint.name, tuple(column.name for column in constraint.columns), constraint.dialect_options["postgresql"]["nulls_not_distinct"])
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint) and constraint.name
    }
    return {"columns": columns, "keys": keys, "unique": unique}


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, _Recorder]:
    module = _load()
    recorder = _Recorder()
    monkeypatch.setattr(module, "op", recorder)
    return module, recorder


def test_the_product_preset_tables_are_the_models(recorded: tuple[ModuleType, _Recorder]) -> None:
    module, recorder = recorded
    module._create_preset_tables()

    for model in (ProductPreset, ProductPresetDelivery, ProductPresetPublicWeb):
        assert _shape(recorder.tables[model.__table__.name]) == _shape(model.__table__), model.__name__


def test_the_columns_and_index_of_their_own_are_the_models(recorded: tuple[ModuleType, _Recorder], monkeypatch: pytest.MonkeyPatch) -> None:
    module, recorder = recorded
    monkeypatch.setattr(module, "_tables", lambda _connection: set())
    monkeypatch.setattr(module, "_columns", lambda _connection, _table: set())
    monkeypatch.setattr(module.sa, "inspect", lambda _connection: type("Inspector", (), {"get_indexes": lambda _self, _table: []})())

    module._ensure_product_public_web(None)
    module._index_attribute_enums(None)

    assert _shape(recorder.tables["product_public_web"]) == _shape(ProductPublicWeb.__table__)
    (index,) = AttributeEnum.__table__.indexes
    assert recorder.indexes == {index.name: ("attribute_enum", [column.name for column in index.columns])}
    upgrade = _source("upgrade")
    assert "sa.Column('public_web_enabled', sa.Boolean(), nullable=False, server_default=sa.true())" in upgrade
    assert "sa.Column('icon', sa.String(length=ICON_LENGTH), nullable=True)" in upgrade
    assert ReportItemType.__table__.c.icon.type.length == module.ICON_LENGTH == ProductPreset.__table__.c.icon.type.length


def test_columns_and_indexes_create_all_made_are_kept() -> None:
    assert "if column.name not in _columns(connection, table)" in _source("_add_column")
    assert "if ENUM_INDEX not in" in _source("_index_attribute_enums")
    assert "if 'product_public_web' not in _tables(connection)" in _source("_ensure_product_public_web")


def test_products_get_a_product_preset_before_their_product_type_goes() -> None:
    source = _source("_point_products_at_presets")
    assert source.index("alter_column") < source.index("drop_column")
    assert "product_type_id" not in Product.__table__.c
    assert not Product.__table__.c.product_preset_id.nullable


def test_the_permissions_are_the_ones_core_adds() -> None:
    module = _load()
    api_source = (CORE_ROOT / "api" / "config.py").read_text(encoding="utf-8")
    renamed = [(new, new_words) for _old, new, _tables, (_old_words, new_words) in module.RENAMES]
    for target, words in [*renamed, ("product_preset", "product preset")]:
        for action in module.ACTIONS:
            name, description = module._permission_names(action, words)
            assert f'Permission.add("CONFIG_{target.upper()}_{action}", "{name}", "{description}")' in api_source
    for old, _new, _tables, _words in module.RENAMES:
        assert f"CONFIG_{old.upper()}_" not in api_source
    # The product preset permissions go to whoever may configure the formats they are made of.
    assert "CONFIG_PRODUCT_FORMAT_" in _source("upgrade").split("_rename_permissions")[1]


def test_the_downgrade_undoes_the_upgrade() -> None:
    downgrade = _source("downgrade")
    # Before the renames are undone, nothing may still point at the product presets.
    assert downgrade.index("drop_constraint") < downgrade.index("drop_table") < downgrade.index("_rename_schema")
    assert downgrade.index("_move_acl_entries") < downgrade.index("_rename_permissions")
    for dropped in ("ENUM_INDEX", "'icon'", "'public_web_enabled'", "'product_preset_id'"):
        assert dropped in downgrade
