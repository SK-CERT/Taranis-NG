"""Assess pages a group's list by keyset cursors and re-reads a shown window by id.

An offset shifts whenever items are collected or removed above it, so the GUI used to repeat or
skip cards when paging, and refreshed its window by re-reading "the newest N" - which no longer
reached the cards on screen once a collector batch was bigger than that. Each item now carries
its place in the order (``cursor``); the GUI pages on after the last one, asks for what is newer
than its window, and re-reads the cards it shows by id.
"""

from __future__ import annotations

import types
from datetime import datetime
from http import HTTPStatus

import pytest
from api import assess
from flask import Flask
from model.news_item import NewsItemAggregate, make_cursor, parse_cursor

# news_item_aggregate.created is a naive timestamp column.
CREATED = datetime(2026, 11, 8, 1, 2, 3, 456789)  # noqa: DTZ001


def test_a_date_cursor_reads_back_to_the_same_place() -> None:
    aggregate = types.SimpleNamespace(id=42, created=CREATED, relevance=3)

    cursor = make_cursor(aggregate, "DATE_DESC")

    assert cursor == "2026-11-08T01:02:03.456789|42"
    assert parse_cursor(cursor, "DATE_DESC") == (CREATED, 42)


def test_a_relevance_cursor_reads_back_to_the_same_place() -> None:
    aggregate = types.SimpleNamespace(id=7, created=None, relevance=-2)

    assert parse_cursor(make_cursor(aggregate, "RELEVANCE_ASC"), "RELEVANCE_ASC") == (-2, 7)


@pytest.mark.parametrize("cursor", [None, "", "no-bar", "yesterday|1", "2026-11-08T01:00:00|x", 5])
def test_a_malformed_cursor_is_ignored(cursor: object) -> None:
    assert parse_cursor(cursor, "DATE_DESC") is None


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


@pytest.fixture
def listed(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    calls: list[tuple] = []
    monkeypatch.setattr(assess.auth_manager, "get_user_from_jwt", lambda: types.SimpleNamespace(id=1))
    monkeypatch.setattr(assess.auth_manager, "check_acl", lambda *_args: True)

    def fake_json(_cls: type, group_id: str, filters: dict, offset: int, limit: int, _user: object) -> dict:
        calls.append((group_id, filters, offset, limit))
        return {"total_count": 0, "items": []}

    monkeypatch.setattr(NewsItemAggregate, "get_by_group_json", classmethod(fake_json))
    return calls


def _get(app: Flask, query: str) -> object:
    resource = assess.NewsItemsByGroup()
    handler = resource.get.__wrapped__.__get__(resource)
    with app.test_request_context(f"/?{query}"):
        return handler("all")


def test_the_window_parameters_reach_the_query(app: Flask, listed: list) -> None:
    _get(app, "sort=DATE_DESC&after=2026-11-08T01:00:00|5&before=2026-11-08T02:00:00|9&limit=20")
    _get(app, "sort=DATE_DESC&ids=3,1,2")

    (_group, filters, offset, limit), (_group2, by_id, _offset2, id_limit) = listed
    assert (filters["after"], filters["before"], offset, limit) == ("2026-11-08T01:00:00|5", "2026-11-08T02:00:00|9", 0, 20)
    # A re-read returns every card named, beyond the page size.
    assert (by_id["ids"], id_limit) == ([3, 1, 2], 3)


@pytest.mark.parametrize(("query", "limit", "offset"), [("limit=100000", 200, 0), ("limit=0&offset=-5", 1, 0)])
def test_paging_is_kept_within_bounds(app: Flask, listed: list, query: str, limit: int, offset: int) -> None:
    _get(app, query)

    assert (listed[0][3], listed[0][2]) == (limit, offset)


@pytest.mark.parametrize("query", ["limit=many", "offset=1.5", "ids=1,two", f"ids={','.join(str(n) for n in range(501))}"])
def test_bad_paging_is_a_400_not_a_500(app: Flask, listed: list, query: str) -> None:
    body, status = _get(app, query)

    assert status == HTTPStatus.BAD_REQUEST
    assert "error" in body
    assert listed == []
