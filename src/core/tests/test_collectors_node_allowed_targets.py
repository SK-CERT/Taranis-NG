"""Internal targets a collectors node may fetch: set on the node, handed out with its sources.

Collectors fetch sources from public addresses only (``shared.url_guard``). The exceptions are a
setting of the collectors node, edited with the node permissions - on purpose not something a
source can carry, since the check exists because of whoever may edit sources. Core tests have no
database: nodes, sources and the session are stand-ins.
"""

from __future__ import annotations

import importlib.util
import re
import types
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from api import config as config_api
from flask import Flask
from managers import collectors_manager
from model import osint_source as osint_source_module
from model.collectors_node import CollectorsNode, NewCollectorsNodeSchema
from model.osint_source import OSINTSource

if TYPE_CHECKING:
    from types import ModuleType

VERSIONS = Path(__file__).parents[1] / "migrations" / "versions"
MIGRATION = VERSIONS / "7a4c1e9b2d36_collectors_node_allowed_targets.py"
NODE = {"id": "", "name": "Collectors", "description": "", "api_url": "http://collectors.example.org", "api_key": "key"}


# --- the node ----------------------------------------------------------------------------------


def test_a_node_keeps_the_list_it_is_saved_with() -> None:
    node = NewCollectorsNodeSchema().load({**NODE, "allowed_private_targets": "intranet.example.org\n10.20.0.0/16"})

    assert node.allowed_private_targets == "intranet.example.org\n10.20.0.0/16"


@pytest.mark.parametrize("extra", [{}, {"allowed_private_targets": None}, {"allowed_private_targets": ""}])
def test_a_node_saved_without_a_list_allows_nothing_internal(extra: dict) -> None:
    assert NewCollectorsNodeSchema().load({**NODE, **extra}).allowed_private_targets == ""


def test_the_column_cannot_be_null_and_defaults_to_empty() -> None:
    column = CollectorsNode.__table__.c.allowed_private_targets

    assert column.nullable is False
    assert column.server_default.arg == ""


# --- saving it from the GUI ----------------------------------------------------------------------


@pytest.fixture
def saved(monkeypatch: pytest.MonkeyPatch) -> list:
    """Record what reaches the manager instead of contacting a node."""
    calls: list = []

    def add(data: dict) -> HTTPStatus:
        calls.append(("add", data))
        return HTTPStatus.OK

    def update(node_id: str, data: dict) -> None:
        calls.append(("update", node_id, data))

    monkeypatch.setattr(config_api.collectors_manager, "add_collectors_node", add)
    monkeypatch.setattr(config_api.collectors_manager, "update_collectors_node", update)
    return calls


def _post(body: dict) -> tuple:
    with Flask(__name__).test_request_context(json=body, method="POST"):
        return config_api.CollectorsNodesResource.post.__wrapped__(config_api.CollectorsNodesResource())


def _put(body: dict) -> tuple | None:
    with Flask(__name__).test_request_context(json=body, method="PUT"):
        return config_api.CollectorsNodeResource.put.__wrapped__(config_api.CollectorsNodeResource(), "node-1")


@pytest.mark.parametrize("allowed", ["0.0.0.0/0", "::/0", "https://intranet.example.org/feed", "intranet.example.org\n*"])
def test_a_list_that_allows_everything_or_is_not_a_list_is_refused_with_the_reason(saved: list, allowed: str) -> None:
    for body, status in (_post({**NODE, "allowed_private_targets": allowed}), _put({**NODE, "allowed_private_targets": allowed})):
        assert status == HTTPStatus.BAD_REQUEST
        assert body["error"].startswith("Allowed internal targets: '")
    assert saved == []


def test_a_good_list_reaches_the_node_on_create_and_update(saved: list) -> None:
    body = {**NODE, "allowed_private_targets": "intranet.example.org\n10.20.0.0/16"}

    assert _post(body) == ("", HTTPStatus.OK)
    assert _put(body) is None
    assert saved == [("add", body), ("update", "node-1", body)]


def test_a_node_saved_by_an_older_client_without_the_field_is_accepted(saved: list) -> None:
    assert _put(NODE) is None
    assert saved == [("update", "node-1", NODE)]


# --- telling the node ----------------------------------------------------------------------------


@pytest.fixture
def node_update(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """A stored node with two collectors; records the refreshes asked of the node."""
    collectors = [types.SimpleNamespace(type="RSS_COLLECTOR"), types.SimpleNamespace(type="WEB_COLLECTOR")]
    stored = types.SimpleNamespace(id="node-1", allowed_private_targets="", collectors=collectors)
    recorded = types.SimpleNamespace(stored=stored, refreshed=[])

    class NodeApi:
        def __init__(self, *_args: object) -> None:
            pass

        def get_collectors_info(self, _node_id: str) -> tuple[list, HTTPStatus]:
            return [], HTTPStatus.OK

    def update(_node_id: str, data: dict, _collectors: list) -> None:
        stored.allowed_private_targets = data.get("allowed_private_targets") or ""

    monkeypatch.setattr(collectors_manager, "keep_stored_api_key", lambda data, *_args: data)
    monkeypatch.setattr(collectors_manager, "CollectorsApi", NodeApi)
    monkeypatch.setattr(collectors_manager.Collector, "create_all", lambda _info: [])
    monkeypatch.setattr(collectors_manager.CollectorsNode, "get_by_id", lambda _node_id: stored)
    monkeypatch.setattr(collectors_manager.CollectorsNode, "update", update)
    monkeypatch.setattr(
        collectors_manager,
        "refresh_collector",
        lambda collector, *, collect_now: recorded.refreshed.append((collector.type, collect_now)),
    )
    return recorded


def test_a_changed_list_has_the_node_read_its_sources_again_without_collecting(node_update: types.SimpleNamespace) -> None:
    collectors_manager.update_collectors_node("node-1", {**NODE, "id": "node-1", "allowed_private_targets": "intranet.example.org"})

    assert node_update.stored.allowed_private_targets == "intranet.example.org"
    assert node_update.refreshed == [("RSS_COLLECTOR", False), ("WEB_COLLECTOR", False)]


def test_saving_a_node_with_the_same_list_does_not_disturb_it(node_update: types.SimpleNamespace) -> None:
    collectors_manager.update_collectors_node("node-1", {**NODE, "id": "node-1", "name": "Renamed"})

    assert node_update.refreshed == []


# --- handing it out with the sources -------------------------------------------------------------


def _node_with_sources(allowed: str | None, monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    class Dumps:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def dump(self, sources: list) -> list[dict]:
            return [dict(source) for source in sources]

    monkeypatch.setattr(osint_source_module, "OSINTSourceSchema", Dumps)
    sources = [{"id": "s1", "name": "one"}, {"id": "s2", "name": "two", "allowed_private_targets": "0.0.0.0/0"}]
    return types.SimpleNamespace(allowed_private_targets=allowed, collectors=[types.SimpleNamespace(type="RSS_COLLECTOR", sources=sources)])


def test_every_source_handed_to_a_node_carries_the_node_s_list(monkeypatch: pytest.MonkeyPatch) -> None:
    node = _node_with_sources("intranet.example.org\n10.20.0.0/16", monkeypatch)

    sources = OSINTSource.get_all_for_collector_json(node, "RSS_COLLECTOR")

    assert [source["allowed_private_targets"] for source in sources] == ["intranet.example.org\n10.20.0.0/16"] * 2


@pytest.mark.parametrize("allowed", ["", None])
def test_a_source_cannot_carry_a_list_of_its_own(monkeypatch: pytest.MonkeyPatch, allowed: str | None) -> None:
    node = _node_with_sources(allowed, monkeypatch)

    sources = OSINTSource.get_all_for_collector_json(node, "RSS_COLLECTOR")

    assert [source["allowed_private_targets"] for source in sources] == ["", ""]


# --- the migration -------------------------------------------------------------------------------


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("collectors_node_allowed_targets_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Op:
    """Records what the migration asks alembic to do."""

    def __init__(self) -> None:
        """Start with nothing asked."""
        self.calls: list = []

    def add_column(self, table: str, column: object) -> None:
        """Record an added column."""
        self.calls.append(("add_column", table, column))

    def drop_column(self, table: str, column: str) -> None:
        """Record a dropped column."""
        self.calls.append(("drop_column", table, column))


@pytest.fixture
def migration(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, _Op]:
    """The migration module with alembic's ``op`` replaced by a recorder."""
    module = _load()
    op = _Op()
    monkeypatch.setattr(module, "op", op)
    return module, op


def test_the_migration_follows_the_publication_time_and_the_gcve_one_follows_it() -> None:
    module = _load()

    def children(revision: str) -> list[str]:
        revises = re.compile(rf'^down_revision = "{revision}"$', re.MULTILINE)
        return [path.name for path in VERSIONS.glob("*.py") if revises.search(path.read_text(encoding="utf-8"))]

    assert (module.revision, module.down_revision) == ("7a4c1e9b2d36", "5c915192b607")
    assert children("5c915192b607") == [MIGRATION.name]
    # The GCVE revision follows it (see test_gcve_migration).
    assert children("7a4c1e9b2d36") == ["6d1f0a9c3e25_gcve_numbering_authority.py"]


def test_the_column_is_the_one_the_model_declares(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: False)
    module.upgrade()

    ((_add, table, column),) = op.calls
    declared = CollectorsNode.__table__.c.allowed_private_targets
    assert (table, column.name, column.nullable) == (CollectorsNode.__tablename__, "allowed_private_targets", declared.nullable)
    assert type(column.type) is type(declared.type)
    assert column.server_default.arg == ""  # existing nodes: nothing internal allowed


def test_a_column_create_all_made_is_left_alone(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: True)
    module.upgrade()

    assert op.calls == []


def test_downgrade_drops_the_column(migration: tuple[ModuleType, _Op], monkeypatch: pytest.MonkeyPatch) -> None:
    module, op = migration
    monkeypatch.setattr(module, "_has_column", lambda: True)
    module.downgrade()

    assert op.calls == [("drop_column", "collectors_node", "allowed_private_targets")]
