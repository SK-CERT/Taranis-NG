"""The CNA revision: the chain, its seed equal to shared.gcve, its tables equal to the models.

As in the other migration tests, no database is needed: the migration's functions run against a
recorder standing in for ``op``.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING

import sqlalchemy as sa
from model.cve_assignment import CveAssignment
from model.cve_services_account import CveServicesAccount

from shared import gcve

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "9e4b2d7c1a38_cve_numbering_authority.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cve_migration", MIGRATION)
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
    """Stands in for ``op``: keeps the tables and indexes a function makes."""

    def __init__(self) -> None:
        self.tables: dict[str, sa.Table] = {}
        self.indexes: dict[str, tuple[str, list[str], bool, object]] = {}

    def create_table(self, name: str, *elements: object) -> None:
        self.tables[name] = sa.Table(name, sa.MetaData(), *elements)

    def create_index(self, name: str, table: str, columns: list[str], unique: bool = False, **kwargs: object) -> None:
        self.indexes[name] = (table, columns, unique, kwargs.get("postgresql_where"))


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


def test_the_revision_follows_the_gcve_one() -> None:
    module = _load()
    assert (module.revision, module.down_revision) == ("9e4b2d7c1a38", "6d1f0a9c3e25")
    assert _children("9e4b2d7c1a38") == [PROVIDER_MIGRATION.name]


# -- the CVE Services data provider (a3f8c6e1d5b9) ----------------------------------------------

PROVIDER_MIGRATION = VERSIONS / "a3f8c6e1d5b9_cve_services_provider.py"


def _load_provider() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cve_services_provider_migration", PROVIDER_MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Bind:
    """Stands in for the connection: keeps the statements run and their parameters."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, dict]] = []

    def execute(self, statement: object, parameters: dict) -> None:
        self.executed.append((str(statement), parameters))


def test_the_provider_revision_follows_the_cna_one_and_is_the_head() -> None:
    module = _load_provider()
    assert (module.revision, module.down_revision) == ("a3f8c6e1d5b9", "9e4b2d7c1a38")
    assert _children("a3f8c6e1d5b9") == []


def test_the_provider_is_seeded_once_with_shared_gcve_and_removed_on_downgrade() -> None:
    module = _load_provider()
    assert (module.API_TYPE, module.API_URL, module.WEB_URL) == (
        gcve.CVE_SERVICES_API_TYPE,
        gcve.CVE_SERVICES_PUBLIC_URL,
        gcve.CVE_RECORD_WEB_URL,
    )
    bind = _Bind()
    module.op = type("Op", (), {"get_bind": staticmethod(lambda: bind)})

    module.upgrade()
    module.downgrade()

    (insert, inserted), (delete, deleted) = bind.executed
    # Only when no provider of the type exists: an administrator's stays as it is.
    assert "WHERE NOT EXISTS (SELECT 1 FROM data_provider WHERE api_type = CAST(:api_type AS VARCHAR))" in insert
    # A parameter used twice has one type: PostgreSQL refused text in the SELECT against varchar.
    assert "SELECT :name, CAST(:api_type AS VARCHAR)," in insert
    assert inserted == {
        "name": "CVE Services (MITRE)",
        "api_type": "CVE_SERVICES",
        "api_url": "https://cveawg.mitre.org/api/",
        "user_agent": module.USER_AGENT,
        "web_url": "https://www.cve.org/CVERecord?id=",
    }
    assert delete.startswith("DELETE FROM data_provider WHERE api_type = :api_type")
    assert deleted == {"api_type": "CVE_SERVICES"}


def test_the_seed_is_shared_gcve() -> None:
    module = _load()
    assert (module.CVE_PRESET_KEY, module.CVE_PRESET_NAME, module.CVE_PRESET_DESCRIPTION) == (
        gcve.CVE_PRESET_KEY,
        gcve.CVE_PRESET_NAME,
        gcve.CVE_PRESET_DESCRIPTION,
    )
    assert (module.CVD_TYPE_KEY, module.CVD_TYPE_DESCRIPTION) == (gcve.CVD_TYPE_KEY, gcve.CVD_TYPE_DESCRIPTION)
    # Off the public web (a CVE Record goes to CVE Services, not to a web), and switched off.
    assert "VALUES (:name, :description, :icon, false, :key, false" in _source("_seed_cve_preset")


def test_its_tables_are_the_models() -> None:
    module = _load()
    recorder = _Recorder()
    module.op = recorder
    module._tables = lambda _connection: set()
    module._create_tables(None)

    for model in (CveServicesAccount, CveAssignment):
        recorded = recorder.tables[model.__table__.name]
        assert _columns(recorded) == _columns(model.__table__), model.__name__
        assert _keys(recorded) == _keys(model.__table__), model.__name__
    # One account per organization.
    account = recorder.tables["cve_services_account"]
    assert any(
        isinstance(constraint, sa.UniqueConstraint) and constraint.columns.keys() == ["organization_id"] for constraint in account.constraints
    )
    assert account.c.id.autoincrement is not False
    model_indexes = {index.name: (index.unique, [column.name for column in index.columns]) for index in CveAssignment.__table__.indexes}
    recorded_indexes = {name: (unique, columns) for name, (_table, columns, unique, _where) in recorder.indexes.items()}
    assert recorded_indexes == model_indexes
    where = recorder.indexes["uq_cve_assignment_live_report"][3]
    assert str(where) == "state <> 'REJECTED' AND report_item_id IS NOT NULL"


def test_what_create_all_made_is_kept_and_reserved_ids_stay() -> None:
    assert "if 'cve_services_account' not in tables" in _source("_create_tables")
    assert "if 'cve_assignment' not in tables" in _source("_create_tables")
    downgrade = _source("downgrade")
    assert "SELECT 1 FROM cve_assignment LIMIT 1" in downgrade
    assert "RuntimeError" in downgrade
