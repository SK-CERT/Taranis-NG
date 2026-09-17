"""Dispatching an on-demand collection, and what core records when it does.

The source is marked as collecting only once the node confirms it started a run. Marking it
beforehand would be simpler, but a node that refuses - because the source is already being
collected - would leave the source stuck looking busy until the staleness window expired, with the
play button disabled the whole time for no reason.

The second thing pinned here is which refresh calls collect everything. Every source save asks the
node to refresh, and a refresh used to collect every source of that type; a single edit therefore
re-collected dozens of sources. These tests are the regression guard for that.

No database and no network: the model and the node client are both replaced with fakes.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import ClassVar

import pytest
from managers import collectors_manager


class FakeCollectorsApi:
    """Stands in for the node client, recording what core asked the node to do."""

    calls: ClassVar[list[tuple]] = []
    collect_response: ClassVar[tuple[dict, HTTPStatus]] = ({"started": True}, HTTPStatus.ACCEPTED)

    def __init__(self, api_url: str, api_key: str) -> None:
        """Record the node this client was pointed at."""
        self.api_url = api_url
        self.api_key = api_key

    def refresh_collector(self, collector_type: str, *, collect_now: bool = True) -> HTTPStatus:
        """Record a refresh and whether it was asked to collect everything."""
        FakeCollectorsApi.calls.append(("refresh", collector_type, collect_now))
        return HTTPStatus.OK

    def collect_source(self, collector_type: str, source_id: str) -> tuple[dict, HTTPStatus]:
        """Record a single-source collection request and answer as configured."""
        FakeCollectorsApi.calls.append(("collect", collector_type, source_id))
        return FakeCollectorsApi.collect_response


def make_source(*, enabled: bool = True) -> types.SimpleNamespace:
    """A source pointing at a collector on a node, the way a stored row would."""
    node = types.SimpleNamespace(api_url="http://node.test", api_key="key")
    collector = types.SimpleNamespace(type="WEB_COLLECTOR", node=node)
    return types.SimpleNamespace(id="source-1", enabled=enabled, collector=collector)


@pytest.fixture
def marks(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace the node client and the model, and record every mark_collection_started call."""
    FakeCollectorsApi.calls = []
    FakeCollectorsApi.collect_response = ({"started": True}, HTTPStatus.ACCEPTED)
    started: list[str] = []

    source = make_source()
    fake_model = types.SimpleNamespace(
        find=lambda _id: source,
        mark_collection_started=started.append,
        set_enabled=lambda _id, _enabled: None,
    )
    monkeypatch.setattr(collectors_manager, "CollectorsApi", FakeCollectorsApi)
    monkeypatch.setattr(collectors_manager, "OSINTSource", fake_model)
    return started


def test_a_started_run_is_recorded_as_collecting(marks: list[str]) -> None:
    body, status = collectors_manager.collect_osint_source("source-1")

    assert status == HTTPStatus.ACCEPTED
    assert body == {"started": True}
    assert marks == ["source-1"]


def test_a_refused_run_does_not_mark_the_source_as_collecting(marks: list[str]) -> None:
    # The node is already collecting this source, so core must not claim a run just began.
    FakeCollectorsApi.collect_response = ({"error": "already collecting"}, HTTPStatus.CONFLICT)

    _, status = collectors_manager.collect_osint_source("source-1")

    assert status == HTTPStatus.CONFLICT
    assert marks == []


def test_a_disabled_source_is_not_dispatched_at_all(monkeypatch: pytest.MonkeyPatch, marks: list[str]) -> None:
    monkeypatch.setattr(collectors_manager, "OSINTSource", types.SimpleNamespace(find=lambda _id: make_source(enabled=False)))

    _, status = collectors_manager.collect_osint_source("source-1")

    assert status == HTTPStatus.BAD_REQUEST
    assert FakeCollectorsApi.calls == []
    assert marks == []


@pytest.mark.usefixtures("marks")
def test_an_unknown_source_is_not_dispatched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(collectors_manager, "OSINTSource", types.SimpleNamespace(find=lambda _id: None))

    _, status = collectors_manager.collect_osint_source("source-1")

    assert status == HTTPStatus.NOT_FOUND
    assert FakeCollectorsApi.calls == []


@pytest.mark.usefixtures("marks")
def test_switching_a_source_reschedules_without_collecting_everything() -> None:
    _, status = collectors_manager.set_osint_source_enabled("source-1", enabled=False)

    assert status == HTTPStatus.OK
    assert FakeCollectorsApi.calls == [("refresh", "WEB_COLLECTOR", False)]


@pytest.mark.usefixtures("marks")
def test_editing_a_source_does_not_re_collect_every_source_of_its_type(monkeypatch: pytest.MonkeyPatch) -> None:
    source = make_source()
    monkeypatch.setattr(
        collectors_manager,
        "OSINTSource",
        types.SimpleNamespace(update=lambda _id, _data: (source, None), find=lambda _id: source),
    )

    collectors_manager.update_osint_source("source-1", {})

    assert FakeCollectorsApi.calls == [("refresh", "WEB_COLLECTOR", False)]


@pytest.mark.usefixtures("marks")
def test_deleting_a_source_does_not_re_collect_every_source_of_its_type(monkeypatch: pytest.MonkeyPatch) -> None:
    source = make_source()
    monkeypatch.setattr(
        collectors_manager,
        "OSINTSource",
        types.SimpleNamespace(find=lambda _id: source, delete=lambda _id: None),
    )

    collectors_manager.delete_osint_source("source-1")

    assert FakeCollectorsApi.calls == [("refresh", "WEB_COLLECTOR", False)]


def test_adding_a_source_collects_only_the_new_one(monkeypatch: pytest.MonkeyPatch, marks: list[str]) -> None:
    source = make_source()
    monkeypatch.setattr(
        collectors_manager,
        "OSINTSource",
        types.SimpleNamespace(
            add_new=lambda _data: source,
            find=lambda _id: source,
            mark_collection_started=marks.append,
        ),
    )

    collectors_manager.add_osint_source({})

    assert FakeCollectorsApi.calls == [
        ("refresh", "WEB_COLLECTOR", False),
        ("collect", "WEB_COLLECTOR", "source-1"),
    ]
    assert marks == ["source-1"]
