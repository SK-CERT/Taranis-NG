"""A public-web node can be switched off.

Off, core leaves the node alone (no health check, no cache resets: see
test_public_web_gating.py), publishes none of its webs, tells the node every web of its is
disabled - so it answers 503 for them - and serves it no products, templates or images. The
node and its webs are kept as they are, so switching it on again restores it.
"""

from __future__ import annotations

import ast
import re
import types
from http import HTTPStatus
from pathlib import Path

import pytest
from api import config as config_api
from api import public_web as public_web_api
from flask import Flask
from model import public_web as public_web_module
from model import public_web_node as public_web_node_module
from model.public_web import PublicWeb
from model.public_web_node import PublicWebNode

# Shared with the built-in template switches (see test_public_web_templates.py).
MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "7d3b9e5f1a2c_public_web_templates.py"


def _node(*, enabled: bool) -> types.SimpleNamespace:
    node = types.SimpleNamespace(id=4, name="node", enabled=enabled, touch=lambda: None)
    web = types.SimpleNamespace(id=7, name="Cyberfeed", hostname="feed.example", enabled=True, config={}, images=[], node=node)
    node.webs = [web]
    return node


# -- the node's own requests --------------------------------------------------------


@pytest.mark.parametrize(
    ("resource", "arguments"),
    [
        (public_web_api.PublicWebProducts, {}),
        (public_web_api.PublicWebProduct, {"product_id": 3}),
        (public_web_api.PublicWebTemplates, {}),
        (public_web_api.PublicWebWebImage, {"web_id": 7, "kind": "logo"}),
    ],
    ids=["products", "product", "templates", "image"],
)
def test_a_disabled_node_is_served_nothing(monkeypatch: pytest.MonkeyPatch, resource: type, arguments: dict) -> None:
    def nothing_may_be_read(*_args: object, **_kwargs: object) -> None:
        pytest.fail("a disabled node got as far as reading content")

    monkeypatch.setattr(public_web_api, "Product", types.SimpleNamespace(get_published=nothing_may_be_read))
    monkeypatch.setattr(public_web_api, "PublicWebTemplate", types.SimpleNamespace(get_all=nothing_may_be_read))
    monkeypatch.setattr(public_web_api, "PublicWeb", types.SimpleNamespace(find=nothing_may_be_read))
    monkeypatch.setattr(public_web_api, "_find_published", nothing_may_be_read)
    handler = resource.get.__wrapped__

    with Flask(__name__).test_request_context("/"):
        body, status = handler(resource(), public_web_node=_node(enabled=False), **arguments)

    assert status == HTTPStatus.FORBIDDEN
    assert "disabled" in body["error"]


@pytest.mark.parametrize("enabled", [True, False])
def test_a_node_learns_its_webs_are_disabled_with_it(enabled: bool) -> None:
    """So it answers 503 for each of them rather than serving what it has cached."""
    resource = public_web_api.PublicWebWebs()

    with Flask(__name__).test_request_context("/"):
        body, status = resource.get.__wrapped__(resource, public_web_node=_node(enabled=enabled))

    assert status == HTTPStatus.OK
    assert [web["enabled"] for web in body["items"]] == [enabled]


# -- what is published ----------------------------------------------------------------


class _Listed:
    """A query that lists nothing, whatever it is narrowed to."""

    def filter(self, *_criteria: object) -> _Listed:
        return self

    def order_by(self, *_columns: object) -> _Listed:
        return self

    def all(self) -> list:
        return []


def test_the_webs_published_are_those_of_enabled_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Traefik's routes - core's own and each node's - and the certificate check list only live webs."""
    monkeypatch.setattr(public_web_module.db, "session", types.SimpleNamespace)
    live = re.sub(r"\s+", " ", str(PublicWeb._live().statement))
    switched_on = str(PublicWebNode.enabled.is_(True)).removeprefix("public_web_node.enabled")
    assert "JOIN public_web_node" in live
    assert f"public_web.enabled{switched_on}" in live
    assert f"public_web_node.enabled{switched_on}" in live

    started: list[str] = []
    monkeypatch.setattr(PublicWeb, "_live", classmethod(lambda _cls: started.append("live") or _Listed()))
    PublicWeb.get_all_enabled()
    PublicWeb.get_enabled_fronted_by_core()
    PublicWeb.get_enabled_for_node(4)
    assert started == ["live"] * 3


# -- switching it ---------------------------------------------------------------------


def test_a_node_is_enabled_unless_told_otherwise() -> None:
    assert PublicWebNode("node").enabled is True
    assert PublicWebNode("node", enabled=None).enabled is True
    assert PublicWebNode("node", enabled=False).enabled is False


@pytest.mark.parametrize(("sent", "kept"), [({}, False), ({"enabled": None}, False), ({"enabled": True}, True)])
def test_an_update_without_the_switch_keeps_it(monkeypatch: pytest.MonkeyPatch, sent: dict, kept: bool) -> None:
    """Ansible re-registers a node without it, and must not switch on a node an administrator switched off."""
    stored = PublicWebNode("node", api_key="key", enabled=False)
    session = types.SimpleNamespace(get=lambda _cls, _id: stored, commit=lambda: None)
    monkeypatch.setattr(public_web_node_module.db, "session", session)

    PublicWebNode.update(4, {"name": "node", "description": "", "api_url": "", "api_key": "", **sent})

    assert stored.enabled is kept


@pytest.mark.parametrize(("sent", "resets"), [(False, 1), (True, 0)], ids=["switched off", "left on"])
def test_switching_a_node_resets_its_cache(monkeypatch: pytest.MonkeyPatch, sent: bool, resets: int) -> None:
    """Switched off it drops its webs now instead of when its cache expires; a plain edit pushes nothing."""
    from managers import public_web_manager  # noqa: PLC0415 (as the endpoint imports it)

    stored = types.SimpleNamespace(id=4, api_url="http://public-web", api_key="key", enabled=True)
    pushed: list[object] = []

    def update(_cls: type, _node_id: int, data: dict) -> None:
        stored.enabled = data["enabled"]

    monkeypatch.setattr(config_api.db, "session", types.SimpleNamespace(get=lambda _cls, _id: stored))
    monkeypatch.setattr(config_api.public_web_node.PublicWebNode, "update", classmethod(update))
    monkeypatch.setattr(public_web_manager, "reset_node", pushed.append)
    resource = config_api.PublicWebNodeResource()

    with Flask(__name__).test_request_context(
        "/",
        method="PUT",
        json={"name": "node", "api_url": "http://public-web", "api_key": "", "enabled": sent},
    ):
        result = resource.put.__wrapped__(resource, 4)

    assert result is None
    assert pushed == [stored] * resets


# -- migration -------------------------------------------------------------------------


def _assignment(name: str) -> object:
    for node in ast.parse(MIGRATION.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    message = f"{name} is not assigned"
    raise AssertionError(message)


def test_the_migration_adds_what_the_model_declares_and_tolerates_create_all() -> None:
    column = PublicWebNode.__table__.c["enabled"]
    assert _assignment("revision") == "7d3b9e5f1a2c"
    assert _assignment("NODE_TABLE") == PublicWebNode.__table__.name
    assert _assignment("NODE_COLUMN") == column.name
    assert column.nullable is False
    source = MIGRATION.read_text(encoding="utf-8")
    assert "op.add_column(NODE_TABLE, sa.Column(NODE_COLUMN, sa.Boolean(), nullable=False, server_default=sa.true()))" in source
    # A fresh database gets the column from create_all(); the migration must not add it twice.
    assert source.index("if not _has_node_column():") < source.index("op.add_column(")
    assert "op.drop_column(NODE_TABLE, NODE_COLUMN)" in source
