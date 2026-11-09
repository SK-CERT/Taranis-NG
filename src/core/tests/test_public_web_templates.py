"""Report templates of the public web.

A template is checked when it is saved, so a mistake shows in the form instead of on
the public page. A product template belongs to a product preset, an item template to a
report item type. Which webs show a product is decided by its preset and the product (see
test_product_public_webs.py). The built-in templates are never deleted, but those public-web
falls back on can be switched off.
"""

from __future__ import annotations

import ast
import re
import types
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import pytest
from api import config as config_api
from api import public_web as public_web_api
from flask import Flask
from model import public_web_template as public_web_template_module
from model.public_web_template import (
    PublicWebBuiltinTemplate,
    PublicWebTemplate,
    PublicWebTemplateWeb,
    TemplateValidationError,
    _check_claims,
    validate_source,
)
from shared.common import TZ
from shared.public_web_templates import DEFAULTS, PRODUCT_BASES, builtin_sources

CORE_ROOT = Path(__file__).parents[1]
PRODUCT_SOURCE = '{% extends "builtin/product_base.html" %}'
# One migration for the templates, their webs and the switches (nodes: see test_public_web_node_enabled.py).
MIGRATION = CORE_ROOT / "migrations" / "versions" / "7d3b9e5f1a2c_public_web_templates.py"


# -- validation --------------------------------------------------------------


def test_an_item_template_needs_only_to_compile() -> None:
    validate_source("<p>{{ item.attrs.description | link_refs(links) | clean }}</p>", product_template=False)


def test_a_syntax_error_names_its_line() -> None:
    with pytest.raises(TemplateValidationError, match="line 2"):
        validate_source("<p>\n{% if %}\n</p>", product_template=False)


def test_an_unknown_filter_is_reported() -> None:
    with pytest.raises(TemplateValidationError, match="no_such_filter"):
        validate_source("{{ item.name | no_such_filter }}", product_template=False)


def test_a_product_template_must_extend_a_builtin_base() -> None:
    validate_source('{% extends "builtin/product_base.html" %}{% block items %}{% endblock %}', product_template=True)
    validate_source('{% extends "builtin/product_vulnerability.html" %}', product_template=True)
    with pytest.raises(TemplateValidationError, match="extends"):
        validate_source("<h1>{{ product.title }}</h1>", product_template=True)
    with pytest.raises(TemplateValidationError, match="extends"):
        validate_source('{% extends "builtin/item_generic.html" %}', product_template=True)


@pytest.mark.parametrize(
    "target",
    [{}, {"product_preset_id": 1, "report_item_type_id": 2}],
    ids=["neither", "both"],
)
def test_a_template_is_for_exactly_one_target(target: dict) -> None:
    with pytest.raises(TemplateValidationError, match="either a product preset or a report item type"):
        PublicWebTemplate._checked({"name": "Template", "source": "", **target})


def test_public_web_gets_what_it_renders_with() -> None:
    template = types.SimpleNamespace(
        id=3,
        name="Disinformation",
        product_preset_id=None,
        report_item_type_id=7,
        source="<p>{{ item.name }}</p>",
        require_tlp_clear=True,
        updated_by="admin",
        public_web_ids=[2],
    )

    assert PublicWebTemplate.node_json(template) == {
        "id": 3,
        "name": "Disinformation",
        "product_preset_id": None,
        "report_item_type_id": 7,
        "source": "<p>{{ item.name }}</p>",
        "require_tlp_clear": True,
        "public_web_ids": [2],
    }


# -- templates for chosen webs ---------------------------------------------------------


def _web(web_id: int, name: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(id=web_id, name=name)


def _other(name: str, *web_ids: int) -> types.SimpleNamespace:
    return types.SimpleNamespace(name=name, public_web_ids=list(web_ids))


@pytest.mark.parametrize(
    ("webs", "others", "refused"),
    [
        ([], [_other("Bulletin", 1)], None),
        ([_web(1, "Cyberfeed")], [_other("Default")], None),
        ([_web(2, "Partners")], [_other("Default"), _other("Cyberfeed only", 1)], None),
        ([], [_other("Default")], "already has a template for every web: 'Default'"),
        (
            [_web(1, "Cyberfeed"), _web(2, "Partners")],
            [_other("Cyberfeed only", 1)],
            "already has a template for Cyberfeed: 'Cyberfeed only'",
        ),
    ],
    ids=["every web beside one web", "one web beside every web", "another web", "two for every web", "the same web twice"],
)
def test_two_templates_of_a_target_never_claim_the_same_web(webs: list, others: list, refused: str | None) -> None:
    """A web uses the template that lists it, else the one for every web - so each must be unambiguous."""
    if refused is None:
        _check_claims("product preset", webs, others)
        return
    with pytest.raises(TemplateValidationError, match=re.escape(f"That product preset {refused}")):
        _check_claims("product preset", webs, others)


def test_a_template_may_only_list_webs_that_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(public_web_template_module.db, "session", types.SimpleNamespace)
    monkeypatch.setattr(PublicWebTemplate, "query", types.SimpleNamespace(filter=lambda *_criteria: types.SimpleNamespace(all=list)))
    monkeypatch.setattr(public_web_template_module.db, "session", types.SimpleNamespace(get=lambda _cls, _id: object()))
    known = {1: _web(1, "Cyberfeed")}
    monkeypatch.setattr(public_web_template_module.PublicWeb, "find", classmethod(lambda _cls, web_id: known.get(web_id)))

    template, webs = PublicWebTemplate._checked({"name": "T", "product_preset_id": 3, "source": PRODUCT_SOURCE, "public_web_ids": [1, 1]})
    assert (template.product_preset_id, [web.id for web in webs]) == (3, [1])

    with pytest.raises(TemplateValidationError, match="Public web 9 does not exist"):
        PublicWebTemplate._checked({"name": "T", "product_preset_id": 3, "source": PRODUCT_SOURCE, "public_web_ids": [9]})


# -- built-in templates ------------------------------------------------------------


def test_only_the_builtins_public_web_falls_back_on_can_be_switched_off() -> None:
    assert set(DEFAULTS) < set(builtin_sources())
    assert not set(DEFAULTS) & {*PRODUCT_BASES, "builtin/_macros.html"} - {"builtin/product_vulnerability.html"}


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("builtin/no_such.html", "no built-in template"),
        ("builtin/product_base.html", "cannot be switched off"),
        ("builtin/_macros.html", "cannot be switched off"),
    ],
)
def test_a_base_or_an_unknown_builtin_cannot_be_switched_off(name: str, message: str) -> None:
    with pytest.raises(TemplateValidationError, match=message):
        PublicWebBuiltinTemplate.set_enabled(name, False, "admin")


def test_switching_a_builtin_records_who_did_it(monkeypatch: pytest.MonkeyPatch) -> None:
    added: list[object] = []
    commits: list[bool] = []
    session = types.SimpleNamespace(get=lambda _cls, _name: None, add=added.append, commit=lambda: commits.append(True))
    monkeypatch.setattr(public_web_template_module.db, "session", session)

    row = PublicWebBuiltinTemplate.set_enabled("builtin/item_generic.html", False, "admin")

    assert added == [row]
    assert commits == [True]
    assert (row.name, row.enabled, row.updated_by) == ("builtin/item_generic.html", False, "admin")
    assert row.updated_at is not None


def _stub_query(monkeypatch: pytest.MonkeyPatch, query: object) -> None:
    """Replace the model's query; reading the real one first (to restore it) needs a session."""
    monkeypatch.setattr(public_web_template_module.db, "session", types.SimpleNamespace)
    monkeypatch.setattr(PublicWebBuiltinTemplate, "query", query)


def test_the_list_shows_every_builtin_on_unless_switched_off(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        types.SimpleNamespace(
            name="builtin/item_generic.html",
            enabled=False,
            updated_at=datetime(2026, 11, 7, 12, 30, tzinfo=TZ),
            updated_by="admin",
        ),
        # A stray row cannot switch a base off.
        types.SimpleNamespace(name="builtin/product_base.html", enabled=False, updated_at=None, updated_by=None),
    ]
    _stub_query(monkeypatch, types.SimpleNamespace(all=lambda: rows))

    items = {item["name"]: item for item in PublicWebBuiltinTemplate.get_all_json()["items"]}

    assert set(items) == set(builtin_sources())
    assert items["builtin/item_generic.html"] == {
        "name": "builtin/item_generic.html",
        "source": builtin_sources()["builtin/item_generic.html"],
        "can_disable": True,
        "enabled": False,
        "updated_at": "07.11.2026 - 12:30",
        "updated_by": "admin",
    }
    assert (items["builtin/product_base.html"]["can_disable"], items["builtin/product_base.html"]["enabled"]) == (False, True)
    assert (items["builtin/item_vulnerability.html"]["can_disable"], items["builtin/item_vulnerability.html"]["enabled"]) == (True, True)


def test_public_web_gets_the_switched_off_builtins(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [types.SimpleNamespace(name="builtin/item_generic.html"), types.SimpleNamespace(name="builtin/product_base.html")]
    _stub_query(monkeypatch, types.SimpleNamespace(filter=lambda *_criteria: types.SimpleNamespace(all=lambda: rows)))
    monkeypatch.setattr(PublicWebTemplate, "get_all", classmethod(lambda _cls: []))
    resource = public_web_api.PublicWebTemplates()
    node = types.SimpleNamespace(enabled=True, touch=lambda: None)

    body, status = resource.get.__wrapped__(resource, public_web_node=node)

    assert status == HTTPStatus.OK
    assert body == {"total_count": 0, "items": [], "disabled_builtins": ["builtin/item_generic.html"]}


@pytest.fixture
def switched(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Run the switch endpoint past its decorator, recording the switches and node notifications."""
    recorded = types.SimpleNamespace(switches=[], notified=0)

    def set_enabled(_cls: type, name: str, enabled: bool, user_name: str) -> types.SimpleNamespace:
        if name not in DEFAULTS:
            msg = "cannot be switched off"
            raise TemplateValidationError(msg)
        recorded.switches.append((name, enabled, user_name))
        return types.SimpleNamespace(name=name, enabled=enabled)

    def notify() -> None:
        recorded.notified += 1

    monkeypatch.setattr(PublicWebBuiltinTemplate, "set_enabled", classmethod(set_enabled))
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: types.SimpleNamespace(name="admin"))
    monkeypatch.setattr(config_api, "_notify_all_public_web_nodes", notify)
    return recorded


@pytest.mark.parametrize(
    ("payload", "status", "switches"),
    [
        ({"name": "builtin/item_generic.html", "enabled": False}, HTTPStatus.OK, [("builtin/item_generic.html", False, "admin")]),
        ({"name": "builtin/product_base.html", "enabled": False}, HTTPStatus.BAD_REQUEST, []),
        ({"name": "builtin/item_generic.html", "enabled": "no"}, HTTPStatus.BAD_REQUEST, []),
        ({"enabled": True}, HTTPStatus.BAD_REQUEST, []),
    ],
    ids=["switch off", "base", "enabled not a boolean", "no name"],
)
def test_the_switch_endpoint(switched: types.SimpleNamespace, payload: dict, status: HTTPStatus, switches: list) -> None:
    resource = config_api.PublicWebTemplateBuiltinResource()
    with Flask(__name__).test_request_context(method="PUT", json=payload):
        body, got = resource.put.__wrapped__(resource)

    assert got == status
    assert switched.switches == switches
    # The nodes reload their templates after a switch, and only then.
    assert switched.notified == len(switches)
    if status == HTTPStatus.OK:
        assert body == {"name": "builtin/item_generic.html", "enabled": False}
    else:
        assert body["error"]


# -- migration ---------------------------------------------------------------------


def _module(path: Path = MIGRATION) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignment(name: str, path: Path = MIGRATION) -> object:
    for node in _module(path).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    message = f"{name} is not assigned"
    raise AssertionError(message)


def _children(revision: str) -> list[str]:
    revises = re.compile(rf'^down_revision = "{revision}"$', re.MULTILINE)
    return [path.name for path in MIGRATION.parent.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]


def test_the_migration_extends_the_api_keys_head() -> None:
    assert _assignment("revision") == "7d3b9e5f1a2c"
    assert _assignment("down_revision") == "5a9e3c7d1b42"
    assert _children("5a9e3c7d1b42") == [MIGRATION.name]
    # Followed only by the manual entry revision (test_manual_entry_migration.py).
    assert _children("7d3b9e5f1a2c") == ["9c4e2a7b5d13_manual_entry_without_sources.py"]


def test_the_builtin_switch_table_survives_a_premature_create_all() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    table = PublicWebBuiltinTemplate.__table__
    assert _assignment("BUILTIN_TABLE") == table.name
    assert source.index("if BUILTIN_TABLE not in _tables():") < source.index("BUILTIN_TABLE,\n")
    for column in table.columns:
        assert f'"{column.name}"' in source, f"{column.name} is declared on the model but not created by the migration"
    assert [column.name for column in table.primary_key.columns] == ["name"]


def test_the_table_survives_a_premature_create_all() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert source.index("if not _existing_table_is_current():") < source.index("op.create_table(")
    # An empty table from before product presets (keyed by distribution_id) is made again.
    assert '"product_preset_id" in' in source
    assert "op.drop_table(TABLE)" in source


def test_the_migration_creates_what_the_model_declares() -> None:
    table = PublicWebTemplate.__table__
    assert _assignment("TABLE") == table.name
    (check,) = [constraint for constraint in table.constraints if constraint.name == _assignment("ONE_TARGET")]
    assert "<>" in str(check.sqltext)
    source = MIGRATION.read_text(encoding="utf-8")
    for column in table.columns:
        assert f'"{column.name}"' in source, f"{column.name} is declared on the model but not created by the migration"
    for column in ("product_preset_id", "report_item_type_id"):
        # Several templates per target, for different webs.
        assert not table.c[column].unique
        (foreign_key,) = table.c[column].foreign_keys
        assert foreign_key.ondelete == "CASCADE"
    assert "unique=True" not in source


def test_the_template_webs_are_created_and_old_unique_targets_dropped() -> None:
    """A database that ran an earlier version of the migration keeps one template per target unless it is dropped."""
    table = PublicWebTemplateWeb.__table__
    assert _assignment("TEMPLATE_WEB_TABLE") == table.name
    assert _assignment("TEMPLATE_TARGETS") == ("product_preset_id", "report_item_type_id")
    source = MIGRATION.read_text(encoding="utf-8")
    for column in table.columns:
        assert f'"{column.name}"' in source
    assert [column.name for column in table.primary_key.columns] == ["public_web_template_id", "public_web_id"]
    (to_template,) = table.c["public_web_template_id"].foreign_keys
    (to_web,) = table.c["public_web_id"].foreign_keys
    assert to_template.ondelete == "CASCADE"
    # A web a template lists cannot be deleted; else the template would apply to every web.
    assert to_web.ondelete is None
    assert source.index("_target_unique_constraints()") < source.index('op.drop_constraint(name, TABLE, type_="unique")')
    assert source.index("if TEMPLATE_WEB_TABLE not in _tables():") < source.index("TEMPLATE_WEB_TABLE,\n")
