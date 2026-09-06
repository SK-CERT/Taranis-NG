"""Static regression tests for the attribute_group_item foreign key migration.

``attribute_group_item.attribute_id`` used to cascade on delete, which made deleting
an attribute strip the fields built on it from every report type - and, once report
items held values under those fields, fail the request with a foreign key violation
from a table the admin never named. ``b8e5d17c3f90`` drops the cascade so the database
enforces the same rule the API does.

Like the other migration tests here, these need neither an application nor a database:
they protect the properties most easily lost while rebasing onto a newer Alembic head.
"""

import ast
import re
from pathlib import Path

CORE_ROOT = Path(__file__).parents[1]
MIGRATIONS = CORE_ROOT / "migrations" / "versions"
FK_MIGRATION = MIGRATIONS / "b8e5d17c3f90_attribute_group_item_no_cascade.py"
REPORT_ITEM_TYPE_MODEL = CORE_ROOT / "model" / "report_item_type.py"

REVISION_RE = re.compile(r"^revision(?::\s*str)?\s*=\s*[\"']([^\"']+)", re.MULTILINE)
DOWN_REVISION_RE = re.compile(r"^down_revision(?::\s*[^=]+)?\s*=\s*[\"']([^\"']+)", re.MULTILINE)


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignment(module: ast.Module, name: str) -> object:
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    message = f"{name} is not assigned"
    raise AssertionError(message)


def _cascade_keyword(module: ast.Module, function_name: str) -> bool:
    """Read the `cascade=` argument the given function passes to the shared rebuild helper."""
    for node in ast.walk(_function(module, function_name)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_recreate":
            for keyword in node.keywords:
                if keyword.arg == "cascade":
                    return ast.literal_eval(keyword.value)
    message = f"{function_name} does not call _recreate(cascade=...)"
    raise AssertionError(message)


def _function(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    message = f"{name} is not defined"
    raise AssertionError(message)


def test_the_revision_graph_has_exactly_one_head() -> None:
    """Two heads make `db_migration.py upgrade` stop short of the real schema.

    Only the count is asserted: naming the current head would turn this into a test that every
    new migration has to be told about, which is not what it is guarding.
    """
    revisions: dict[str, str] = {}
    parents: set[str] = set()
    for path in MIGRATIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        revision = REVISION_RE.search(text)
        parent = DOWN_REVISION_RE.search(text)
        if revision:
            revisions[revision.group(1)] = path.name
        if parent:
            parents.add(parent.group(1))

    heads = sorted(set(revisions) - parents)
    assert len(heads) == 1, f"expected a single head, got {[(h, revisions[h]) for h in heads]}"


def test_the_migration_extends_the_multi_choice_head() -> None:
    module = _module(FK_MIGRATION)

    assert _assignment(module, "revision") == "b8e5d17c3f90"
    assert _assignment(module, "down_revision") == "c7a1b4e9d203"


def test_upgrade_drops_the_cascade_and_downgrade_restores_it() -> None:
    module = _module(FK_MIGRATION)

    assert _cascade_keyword(module, "upgrade") is False
    assert _cascade_keyword(module, "downgrade") is True


def test_the_migration_targets_only_the_attribute_reference() -> None:
    """The sibling cascades are deliberate compositions and must be left alone."""
    module = _module(FK_MIGRATION)

    assert _assignment(module, "TABLE") == "attribute_group_item"
    assert _assignment(module, "COLUMN") == "attribute_id"
    assert _assignment(module, "REFERENCED") == "attribute"


def test_the_model_agrees_that_the_reference_does_not_cascade() -> None:
    """A model-side ondelete would put create_all-built databases back out of step."""
    source = REPORT_ITEM_TYPE_MODEL.read_text(encoding="utf-8")
    declaration = re.search(r"attribute_id\s*=\s*db\.Column\((.*?)\)\n", source, re.DOTALL)

    assert declaration is not None, "attribute_group_item.attribute_id is no longer declared as expected"
    assert 'db.ForeignKey("attribute.id")' in declaration.group(1)
    assert "ondelete" not in declaration.group(1)
