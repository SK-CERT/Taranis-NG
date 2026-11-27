"""The GCVE revision: the chain, its seeds equal to shared.gcve, and its tables equal to the models.

Like the other migration tests here, no database is needed: the migration's functions run against
a recorder standing in for ``op``. The revision itself was run against Postgres 16 on a copy of the
e2e database: upgrade, downgrade, upgrade again, and the downgrade refusing once an identifier
existed.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import sqlalchemy as sa
from model.gcve_assignment import GcveAssignment, GcveCounter
from model.organization_gna import OrganizationGna
from model.product_preset import ProductPreset
from model.report_item import ReportItem
from model.report_item_type import ReportItemType

from shared import gcve

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "6d1f0a9c3e25_gcve_numbering_authority.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gcve_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source(name: str) -> str:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    return next(ast.unparse(node) for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _children(revision: str) -> list[str]:
    revises = re.compile(rf'^down_revision = "{revision}"$', re.MULTILINE)
    return [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]


class _Recorder:
    """Stands in for ``op``: keeps the tables and columns a function makes."""

    def __init__(self) -> None:
        self.tables: dict[str, sa.Table] = {}
        self.columns: dict[tuple[str, str], sa.Column] = {}
        self.uniques: dict[str, tuple[str, list[str]]] = {}
        self.foreign_keys: dict[str, tuple[str, str, list[str], str]] = {}
        self.indexes: dict[str, tuple[str, list[str]]] = {}

    def create_table(self, name: str, *elements: object) -> None:
        self.tables[name] = sa.Table(name, sa.MetaData(), *elements)

    def add_column(self, table: str, column: sa.Column) -> None:
        self.columns[table, column.name] = column

    def create_unique_constraint(self, name: str, table: str, columns: list[str]) -> None:
        self.uniques[name] = (table, columns)

    def create_foreign_key(self, name: str, table: str, target: str, columns: list[str], _target_columns: list[str], ondelete: str) -> None:
        self.foreign_keys[name] = (table, target, columns, ondelete)

    def create_index(self, name: str, table: str, columns: list[str]) -> None:
        self.indexes[name] = (table, columns)


def _columns(table: sa.Table) -> dict:
    return {
        column.name: (type(column.type).__name__, getattr(column.type, "length", None), column.nullable, column.primary_key)
        for column in table.columns
    }


def _keys(table: sa.Table) -> set:
    return {
        (
            tuple(key.parent.name for key in constraint.elements),
            tuple(key.target_fullname for key in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
    }


def _uniques(table: sa.Table) -> set:
    found = {
        tuple(sorted(column.name for column in constraint.columns))
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    }
    found |= {(column.name,) for column in table.columns if column.unique}
    return found


def _checks(table: sa.Table) -> set:
    return {str(constraint.sqltext) for constraint in table.constraints if isinstance(constraint, sa.CheckConstraint)}


def test_the_revision_follows_the_collectors_node_one_and_the_cna_one_follows_it() -> None:
    module = _load()
    assert (module.revision, module.down_revision) == ("6d1f0a9c3e25", "7a4c1e9b2d36")
    assert _children("6d1f0a9c3e25") == ["9e4b2d7c1a38_cve_numbering_authority.py"]


def test_the_seeds_are_shared_gcve() -> None:
    module = _load()
    # The description this revision seeded; the CNA revision (9e4b2d7c1a38) rewrites it to shared.gcve's.
    assert (module.CVD_TYPE_KEY, module.CVD_TYPE_TITLE, module.CVD_TYPE_DESCRIPTION) == (
        gcve.CVD_TYPE_KEY,
        gcve.CVD_TYPE_TITLE,
        "Coordinated Vulnerability Disclosure, published as a GCVE record",
    )
    assert (module.GCVE_PRESET_KEY, module.GCVE_PRESET_NAME, module.GCVE_PRESET_DESCRIPTION) == (
        gcve.GCVE_PRESET_KEY,
        gcve.GCVE_PRESET_NAME,
        gcve.GCVE_PRESET_DESCRIPTION,
    )
    assert [tuple(attribute) for attribute in gcve.CVD_ATTRIBUTES] == [tuple(attribute) for attribute in module.ATTRIBUTES]
    assert [(group.title, [tuple(field) for field in group.fields]) for group in gcve.CVD_GROUPS] == [
        (title, [tuple(field) for field in fields]) for title, fields in module.GROUPS
    ]
    # Text, rich text, dates, CVSS, CVE and CWE use the generic attribute of the type, the one
    # other report types use too; only choices and structured values have CVD attributes.
    assert tuple(module.GENERIC_ATTRIBUTES) == gcve.GENERIC_ATTRIBUTE_TYPES
    names = {attribute.name for attribute in gcve.CVD_ATTRIBUTES}
    assert {field.attribute for group in gcve.CVD_GROUPS for field in group.fields} <= names | set(gcve.GENERIC_ATTRIBUTE_TYPES)
    assert not {attribute.type for attribute in gcve.CVD_ATTRIBUTES} & set(gcve.GENERIC_ATTRIBUTE_TYPES)
    # The GNA itself is the organization's (organization_gna); the setting says where the directory is.
    assert [setting[:3] for setting in module.SETTINGS] == [(gcve.DIRECTORY_URL_SETTING, "S", gcve.DEFAULT_DIRECTORY_URL)]
    assert (module.GNA_ID_MIN, module.GNA_ID_MAX) == (gcve.GNA_ID_MIN, gcve.GNA_ID_MAX)
    assert set(module.NEW_ATTRIBUTE_TYPES) == {"AFFECTED", "CREDIT", "TIMELINE", "RELATIONSHIP", "REFERENCE", "JSON"}


def test_its_tables_are_the_models() -> None:
    module = _load()
    recorder = _Recorder()
    module.op = recorder
    module._tables = lambda _connection: set()
    module._create_tables(None)

    for model in (GcveCounter, GcveAssignment, OrganizationGna):
        recorded = recorder.tables[model.__table__.name]
        assert _columns(recorded) == _columns(model.__table__), model.__name__
        assert _keys(recorded) == _keys(model.__table__), model.__name__
        assert _uniques(recorded) == _uniques(model.__table__), model.__name__
        assert _checks(recorded) == _checks(model.__table__), model.__name__


def test_a_reports_organization_is_the_models() -> None:
    module = _load()
    recorder = _Recorder()
    module.op = recorder
    module._columns = lambda _connection, _table: set()
    module._foreign_keys = lambda _connection, _table: set()
    module._indexes = lambda _connection, _table: set()
    module._add_report_organization(None)

    column = ReportItem.__table__.c.organization_id
    recorded = recorder.columns["report_item", "organization_id"]
    assert (type(recorded.type).__name__, recorded.nullable) == (type(column.type).__name__, column.nullable)
    # Named as create_all() names them, so that one made by it is found.
    assert recorder.foreign_keys["report_item_organization_id_fkey"] == ("report_item", "organization", ["organization_id"], "SET NULL")
    assert {key.target_fullname: key.ondelete for key in column.foreign_keys} == {"organization.id": "SET NULL"}
    assert recorder.indexes["ix_report_item_organization_id"] == ("report_item", ["organization_id"])
    assert column.index


def test_its_columns_are_the_models() -> None:
    module = _load()
    recorder = _Recorder()
    module.op = recorder
    module._columns = lambda _connection, _table: set()
    module._add_lock_columns(None)

    for model in (ReportItemType, ProductPreset):
        table = model.__table__
        for name in ("system_key", "enabled"):
            column = recorder.columns[table.name, name]
            assert (type(column.type).__name__, column.nullable) == (type(table.c[name].type).__name__, table.c[name].nullable)
        assert recorder.uniques[f"{table.name}_system_key_key"] == (table.name, ["system_key"])
        assert table.c.system_key.unique


def test_what_create_all_made_is_kept_and_labels_come_first() -> None:
    assert "if 'gcve_counter' not in tables" in _source("_create_tables")
    assert "if 'gcve_assignment' not in tables" in _source("_create_tables")
    assert "if 'organization_gna' not in tables" in _source("_create_tables")
    assert "if 'organization_id' not in _columns(connection, 'report_item')" in _source("_add_report_organization")
    assert "if 'system_key' not in columns" in _source("_add_lock_columns")
    upgrade = _source("upgrade")
    assert upgrade.index("_add_attribute_types") < upgrade.index("_seed_cvd_type")
    assert "autocommit_block" in _source("_add_attribute_types")
    assert "DROP CONSTRAINT IF EXISTS settings_type_key" in _source("_add_settings")


def test_the_generic_attribute_is_the_first_of_its_type_without_a_validator() -> None:
    source = _source("_attribute_ids")
    assert "for generic_type, generic_name in GENERIC_ATTRIBUTES.items()" in source
    assert "ORDER BY CASE WHEN validator IS NULL OR CAST(validator AS text) = 'NONE' THEN 0 ELSE 1 END, id LIMIT 1" in source


def test_the_shipped_type_and_preset_start_switched_off() -> None:
    assert "'[]', 'en', '{}', :key, false) RETURNING id" in _source("_seed_cvd_type")
    assert "VALUES (:name, :description, :icon, true, :key, false" in _source("_seed_gcve_preset")


def test_the_downgrade_keeps_allocated_identifiers() -> None:
    assert "SELECT 1 FROM gcve_assignment LIMIT 1" in _source("downgrade")
    assert "RuntimeError" in _source("downgrade")
