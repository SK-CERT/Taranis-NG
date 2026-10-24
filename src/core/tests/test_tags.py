"""Tags: what admins may define, what people may put on items, and the built-in tags.

Built-in tags (the translation status, "language not set") are worked out by Taranis, so nobody
can put them on an item or delete them; admins restyle them and switch them off instead. No
database: lookups are stubbed.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import re
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import analyze as analyze_api
from api import tag as tag_api
from flask import Flask

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model import tag as tag_module  # noqa: E402 - after every mapper is registered
from model.tag import SYSTEM_KEYS, Tag, TagEntityType, clean_tag  # noqa: E402

USER = SimpleNamespace(id=3, name="Ann Analyst")
OFFERED = [
    {"id": 1, "system_key": None},
    {"id": 2, "system_key": None},
    {"id": 9, "system_key": "translation_outdated"},
]


def test_a_tag_needs_a_name_and_a_real_colour() -> None:
    assert clean_tag({"display_name": " Urgent ", "color": "#FF0000", "icon": "mdi-fire"}) == {
        "display_name": "Urgent",
        "description": "",
        "color": "#FF0000",
        "icon": "mdi-fire",
    }
    with pytest.raises(ValueError, match="needs a name"):
        clean_tag({"display_name": "  "})
    with pytest.raises(ValueError, match="Not a colour: red"):
        clean_tag({"display_name": "Urgent", "color": "red"})
    with pytest.raises(ValueError, match="at most 100"):
        clean_tag({"display_name": "x" * 101})
    # Nobody adds a built-in tag; they come with Taranis.
    with pytest.raises(ValueError, match="built in"):
        clean_tag({"display_name": "Mine", "system_key": "translation_done"})


def test_a_built_in_tag_keeps_its_key_when_renamed() -> None:
    tag = Tag(display_name="translation_done", system_key="translation_done")

    assert clean_tag({"display_name": "Přeloženo", "system_key": "translation_done"}, system=True)["display_name"] == "Přeloženo"
    assert tag.is_system


@pytest.fixture
def offered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Tag, "offered", classmethod(lambda _cls, _entity_type: OFFERED))


@pytest.mark.usefixtures("offered")
def test_people_put_only_offered_admin_tags_on_items() -> None:
    assert Tag.assignable("report_item", [2, 1, 2]) == [2, 1]
    assert Tag.assignable("report_item", None) == []
    with pytest.raises(ValueError, match="cannot be put on this item: 9"):
        Tag.assignable("report_item", [1, 9])
    with pytest.raises(ValueError, match="cannot be put on this item: 4"):
        Tag.assignable("report_item", [4])
    with pytest.raises(ValueError, match="list of tag ids"):
        Tag.assignable("report_item", "1")
    with pytest.raises(ValueError, match="list of tag ids"):
        Tag.assignable("report_item", [True])


def test_built_in_tags_and_tags_in_use_are_not_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    built_in = Tag(display_name="translation_ai", system_key="translation_ai")
    assert built_in.delete()[1] == HTTPStatus.FORBIDDEN

    used = Tag(display_name="Urgent")
    monkeypatch.setattr(Tag, "usage", lambda _self: 4)
    body, status = used.delete()
    assert (status, body["usage_count"]) == (HTTPStatus.CONFLICT, 4)


def test_a_built_in_tag_stays_linked_and_a_link_keeps_its_entity_type() -> None:
    link = TagEntityType(entity_type="product")
    link.tag = Tag(display_name="language_not_set", system_key="language_not_set")
    assert link.delete()[1] == HTTPStatus.FORBIDDEN

    assert TagEntityType._clean({"entity_type": "product", "is_active": False, "sort_order": "3"}) == {
        "entity_type": "product",
        "is_active": False,
        "sort_order": 3,
    }
    with pytest.raises(ValueError, match="Tags are for"):
        TagEntityType._clean({"entity_type": "news_item"})


def test_a_list_request_names_tags_and_one_translation_filter() -> None:
    assert tag_api.list_filter({"tags": "3,x,5", "translation": "needs", "translation_language": "sk"}) == {
        "tags": [3, 5],
        "translation": "needs",
        "translation_language": "sk",
    }
    assert tag_api.list_filter({"translation": "not_set", "translation_language": "zz"}) == {"translation": "not_set"}
    # A translation filter without a real language is left out.
    assert tag_api.list_filter({"translation": "unreviewed", "translation_language": "zz"}) == {}
    assert tag_api.list_filter({"translation": "everything"}) == {}


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    """A bare app and an analyst; SSE goes into a list."""
    events: list = []
    monkeypatch.setattr(analyze_api.auth_manager, "get_user_from_jwt", lambda: USER)
    monkeypatch.setattr(analyze_api.sse_manager, "report_item_updated", lambda data: events.append(("report-item-updated", data)))
    monkeypatch.setattr(analyze_api.sse_manager, "report_items_updated", lambda: events.append(("report-items-updated", None)))
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, report_item_id: SimpleNamespace(id=report_item_id)))
    monkeypatch.setattr(analyze_api.db.session, "commit", lambda: None)
    monkeypatch.setattr(analyze_api.db.session, "rollback", lambda: None)
    app = Flask(__name__)
    app.events = events
    return app


def _put_tags(app: Flask, body: dict) -> tuple[dict, HTTPStatus]:
    resource = analyze_api.ReportItemTags()
    with app.test_request_context("/", method="PUT", json=body):
        return type(resource).put.__wrapped__(resource, 7)


@pytest.mark.usefixtures("offered")
def test_tags_put_on_a_report_are_stored_and_announced(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    stored: list = []
    monkeypatch.setattr("model.report_item.set_item_tags", lambda *args: stored.append(args))

    payload, status = _put_tags(app, {"tag_ids": [2, 1]})

    assert (payload, status) == ({"tags": [2, 1]}, HTTPStatus.OK)
    assert stored == [("report_item", 7, [2, 1], USER.id)]
    assert app.events == [
        ("report-item-updated", {"report_item_id": 7, "user_id": USER.id, "tags": [2, 1]}),
        ("report-items-updated", None),
    ]


@pytest.mark.usefixtures("offered")
def test_a_built_in_tag_put_on_a_report_is_refused(app: Flask) -> None:
    payload, status = _put_tags(app, {"tag_ids": [9]})

    assert status == HTTPStatus.BAD_REQUEST
    assert "cannot be put on this item: 9" in payload["error"]
    assert app.events == []


# ---- migration -------------------------------------------------------------------------

MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "6e1d4b8a2f97_tags.py"


def _migration() -> object:
    spec = importlib.util.spec_from_file_location("tags_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_migration_extends_the_product_languages_head() -> None:
    module = _migration()
    assert (module.revision, module.down_revision) == ("6e1d4b8a2f97", "4bc3bad77008")
    revises = re.compile(r'^down_revision = "4bc3bad77008"$', re.MULTILINE)
    children = [path.name for path in MIGRATION.parent.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]
    assert children == [MIGRATION.name]


def test_the_migration_adds_every_built_in_tag_once_and_reuses_existing_tables() -> None:
    module = _migration()
    assert [key for key, _color, _icon in module.SYSTEM_TAGS] == list(SYSTEM_KEYS)
    assert all(re.fullmatch(r"#[0-9A-F]{6}", color) for _key, color, _icon in module.SYSTEM_TAGS)
    functions = {
        node.name: ast.unparse(node) for node in ast.parse(MIGRATION.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef)
    }
    for table in ("tag", "tag_entity_type", "report_item_tag", "product_tag"):
        assert f"if '{table}' not in tables" in functions["_create_tables"]
    # A built-in tag or link that is already there is kept, not added again.
    assert "if tag_id is None" in functions["_seed_system_tags"]
    assert "if not linked" in functions["_seed_system_tags"]


def test_the_models_declare_what_the_migration_creates() -> None:
    tables = {table.name: table for table in (Tag.__table__, TagEntityType.__table__, tag_module.report_item_tag, tag_module.product_tag)}
    assert set(tables) == {"tag", "tag_entity_type", "report_item_tag", "product_tag"}
    assert {column.name for column in tables["report_item_tag"].primary_key} == {"report_item_id", "tag_id"}
    assert tables["tag"].columns["system_key"].unique
