"""Two access checks a review of the Assess and Analyze endpoints found missing.

- ``GET /analyze/report-items/<id>/data?add=…&aggregate_ids=…`` dumped every aggregate (and with
  ``remote_report_item_ids`` every report) named in the request, linked to the report or not: any
  user who may read one report could read every news item by its (sequential) id.
- ``PUT /assess/news-item-aggregates/<id>`` changed the title, description and comments of any
  aggregate, in groups and of sources the user may not see.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from model import news_item as news_item_model
from model import report_item as report_item_model
from model.news_item import NewsItem, NewsItemAggregate
from model.osint_source import OSINTSourceGroup
from model.report_item import ReportItem


@pytest.fixture
def report(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    linked_aggregate = types.SimpleNamespace(id=5)
    linked_remote = types.SimpleNamespace(id=8)
    item = types.SimpleNamespace(language=None, news_item_aggregates=[linked_aggregate], remote_report_items=[linked_remote], attributes=[])
    monkeypatch.setattr(report_item_model.db, "session", types.SimpleNamespace(get=lambda _cls, _id: item))
    dump = types.SimpleNamespace(dump=lambda obj: {"id": obj.id})
    monkeypatch.setattr(report_item_model, "NewsItemAggregateSchema", lambda: dump)
    monkeypatch.setattr(report_item_model, "RemoteReportItemSchema", lambda: dump)
    monkeypatch.setattr(NewsItemAggregate, "find", classmethod(lambda _cls, _id: pytest.fail("no lookup of an id the report does not hold")))
    monkeypatch.setattr(ReportItem, "find", classmethod(lambda _cls, _id: pytest.fail("no lookup of an id the report does not hold")))
    return item


@pytest.mark.usefixtures("report")
def test_report_data_hands_out_only_what_the_report_holds() -> None:
    data = ReportItem.get_updated_data(1, {"add": "true", "aggregate_ids": ["5", "6", "7"], "remote_report_item_ids": ["8", "9"]})

    assert data["news_item_aggregates"] == [{"id": 5}]
    assert data["remote_report_items"] == [{"id": 8}]


@pytest.fixture
def aggregate(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    data = types.SimpleNamespace(osint_source_id="s")
    item = types.SimpleNamespace(id=1, important=False, read=False, vote=lambda *_args: None, news_item_data=data)
    agg = types.SimpleNamespace(id=3, osint_source_group_id="g", news_items=[item], read=False, title="old", description="", comments="")
    monkeypatch.setattr(NewsItemAggregate, "find", classmethod(lambda _cls, _id: agg))
    monkeypatch.setattr(NewsItemAggregate, "update_status", classmethod(lambda _cls, _id: None))
    monkeypatch.setattr(news_item_model.NewsItemAggregateSearchIndex, "prepare", classmethod(lambda _cls, _agg, **_kw: None))
    monkeypatch.setattr(news_item_model.db, "session", types.SimpleNamespace(commit=lambda: None))
    agg.access = {"group": True, "item": True}
    monkeypatch.setattr(OSINTSourceGroup, "allowed_with_acl", classmethod(lambda _cls, *_args, **_kw: agg.access["group"]))
    monkeypatch.setattr(NewsItem, "allowed_with_acl", classmethod(lambda _cls, *_args, **_kw: agg.access["item"]))
    return agg


USER = types.SimpleNamespace(id=7)


@pytest.mark.parametrize("access", [{"group": False, "item": True}, {"group": True, "item": False}])
def test_an_aggregate_out_of_reach_keeps_its_comments(aggregate: types.SimpleNamespace, access: dict) -> None:
    aggregate.access = access

    _message, _sources, status = NewsItemAggregate.update(3, {"comments": "defaced", "title": "defaced"}, USER)

    assert status == HTTPStatus.FORBIDDEN
    assert (aggregate.title, aggregate.comments) == ("old", "")


def test_an_aggregate_in_reach_is_updated(aggregate: types.SimpleNamespace) -> None:
    _message, _sources, status = NewsItemAggregate.update(3, {"comments": "noted"}, USER)

    assert status == HTTPStatus.OK
    assert aggregate.comments == "noted"


# ── linking news items and reports to a report ────────────────────────────────────


def test_a_report_takes_only_news_items_and_reports_its_author_may_read(monkeypatch: pytest.MonkeyPatch) -> None:
    readable, hidden = types.SimpleNamespace(id=1), types.SimpleNamespace(id=2)
    aggregates = {"1": readable, "2": hidden}
    reports = {"10": types.SimpleNamespace(id=10), "11": types.SimpleNamespace(id=11)}
    monkeypatch.setattr(NewsItemAggregate, "find", classmethod(lambda _cls, aggregate_id: aggregates.get(str(aggregate_id))))
    monkeypatch.setattr(NewsItemAggregate, "allowed_for", classmethod(lambda _cls, aggregate, _user, **_kw: aggregate is readable))
    monkeypatch.setattr(ReportItem, "find", classmethod(lambda _cls, report_id: reports.get(str(report_id))))
    monkeypatch.setattr(ReportItem, "allowed_with_acl", classmethod(lambda _cls, report_id, _user, **_kw: report_id == 10))
    report = types.SimpleNamespace(news_item_aggregates=[], remote_report_items=[])

    ReportItem._link_readable(report, {"aggregate_ids": ["1", "2", "3"], "remote_report_item_ids": ["10", "11", "12"]}, USER)

    assert [aggregate.id for aggregate in report.news_item_aggregates] == [1]
    assert [remote.id for remote in report.remote_report_items] == [10]


@pytest.mark.parametrize(
    ("group", "items", "allowed"),
    [(True, [True], True), (False, [True], False), (True, [False, False], False), (True, [False, True], True)],
)
def test_an_aggregate_is_usable_in_an_accessible_group_with_a_readable_item(
    monkeypatch: pytest.MonkeyPatch,
    group: bool,
    items: list[bool],
    allowed: bool,
) -> None:
    access = dict(enumerate(items))
    monkeypatch.setattr(OSINTSourceGroup, "allowed_with_acl", classmethod(lambda _cls, *_args, **_kw: group))
    monkeypatch.setattr(NewsItem, "allowed_with_acl", classmethod(lambda _cls, news_item_id, *_args, **_kw: access[news_item_id]))
    aggregate = types.SimpleNamespace(osint_source_group_id="g", news_items=[types.SimpleNamespace(id=i) for i in access])

    assert NewsItemAggregate.allowed_for(aggregate, USER) is allowed
    assert NewsItemAggregate.allowed_for(None, USER) is False
