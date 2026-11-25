"""A collectors node's API key reaches the node's own OSINT sources only.

Any collectors key used to be good for every source: it could put news items into a source of
another node (every analyst who may read that source then took them for its own), rewrite a
versioned item another node had collected, and mark any source as collecting or failed.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import collectors
from flask import Flask
from model.news_item import NewsItemAggregate
from model.osint_source import OSINTSource

APP = Flask(__name__)


@pytest.fixture
def node() -> types.SimpleNamespace:
    sources = [types.SimpleNamespace(id="own-1"), types.SimpleNamespace(id="own-2")]
    return types.SimpleNamespace(
        name="node-a",
        collectors=[types.SimpleNamespace(sources=sources[:1]), types.SimpleNamespace(sources=sources[1:])],
    )


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> list:
    calls: list = []
    monkeypatch.setattr(
        NewsItemAggregate,
        "add_news_items",
        classmethod(lambda _cls, items, source_ids=None: calls.append((items, source_ids)) or set()),
    )
    monkeypatch.setattr(collectors.logger, "warning", lambda *_args, **_kwargs: None)
    return calls


def _post(node: types.SimpleNamespace, items: list) -> object:
    with APP.test_request_context("/api/v1/collectors/news-items", method="POST", json=items):
        return collectors.AddNewsItems.post.__wrapped__(collectors.AddNewsItems(), collectors_node=node)


def test_news_items_of_the_node_s_own_sources_are_stored(node: types.SimpleNamespace, stored: list) -> None:
    items = [{"osint_source_id": "own-1"}, {"osint_source_id": "own-2"}]

    assert _post(node, items) is None
    assert stored == [(items, {"own-1", "own-2"})]


def test_a_batch_naming_another_node_s_source_is_refused_whole(node: types.SimpleNamespace, stored: list) -> None:
    body, status = _post(node, [{"osint_source_id": "own-1"}, {"osint_source_id": "theirs"}])

    assert status == HTTPStatus.FORBIDDEN
    assert "does not collect" in body["error"]
    assert stored == []


def test_an_item_without_a_source_is_refused(node: types.SimpleNamespace, stored: list) -> None:
    assert _post(node, [{"title": "no source"}])[1] == HTTPStatus.FORBIDDEN
    assert stored == []


@pytest.mark.parametrize(
    ("resource", "marker"),
    [(collectors.OSINTSourceLastAttempt, "mark_collection_started"), (collectors.OSINTSourceLastErrorMessage, "mark_collection_finished")],
)
def test_the_node_reports_on_its_own_sources_only(
    node: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    resource: type,
    marker: str,
) -> None:
    marked: list = []
    monkeypatch.setattr(OSINTSource, "find", classmethod(lambda _cls, source_id: types.SimpleNamespace(id=source_id)))
    monkeypatch.setattr(OSINTSource, marker, classmethod(lambda _cls, source_id, *_args: marked.append(source_id)))
    monkeypatch.setattr(collectors.logger, "warning", lambda *_args, **_kwargs: None)

    with APP.test_request_context("/?message=boom"):
        refused = resource.get.__wrapped__(resource(), "theirs", collectors_node=node)
        allowed = resource.get.__wrapped__(resource(), "own-2", collectors_node=node)

    assert refused[1] == HTTPStatus.NOT_FOUND
    assert allowed == ({}, HTTPStatus.OK)
    assert marked == ["own-2"]


def test_a_schedule_is_kept_for_the_node_s_own_sources_only(node: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    kept: dict = {}
    monkeypatch.setattr(collectors.run_state_cache, "set_next_run", kept.__setitem__)

    with APP.test_request_context("/", method="POST", json={"own-1": "2026-11-26T10:00:00", "theirs": "2026-11-26T10:00:00"}):
        collectors.CollectorSourcesSchedule.post.__wrapped__(collectors.CollectorSourcesSchedule(), "collector-1", collectors_node=node)

    assert kept == {"own-1": "2026-11-26T10:00:00"}
