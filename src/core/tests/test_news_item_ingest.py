"""Storing a batch of news items: what it avoids doing more than once.

A new aggregate's search row is created without looking one up, the search rows of a batch are
committed with the batch, and an item's content is parsed to plain text once, however many
groups show it. Core tests run without a database, so the session is a fake.
"""

from __future__ import annotations

import types
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from model import news_item as news_item_module
from model.news_item import NewsItemAggregateSearchIndex, NewsItemData

if TYPE_CHECKING:
    from collections.abc import Iterator


class FakeSession:
    """Records what the search index asks of the session."""

    def __init__(self, aggregate: types.SimpleNamespace) -> None:
        """Flushing gives the aggregate its id, as the database would."""
        self.aggregate = aggregate
        self.added: list = []
        self.flushes = 0
        self.commits = 0

    def add(self, item: object) -> None:
        """Record an added object."""
        self.added.append(item)

    def flush(self) -> None:
        """Assign the pending aggregate its id."""
        self.flushes += 1
        self.aggregate.id = 42

    def commit(self) -> None:
        """Count a commit."""
        self.commits += 1


def make_aggregate(aggregate_id: int | None) -> types.SimpleNamespace:
    data = types.SimpleNamespace(
        title="Kernel Update",
        review="Review",
        content_plaintext="Body text",
        author="PSIRT",
        link="https://example.com/a",
        attributes=[types.SimpleNamespace(value="CVE-2026-1234")],
    )
    return types.SimpleNamespace(
        id=aggregate_id,
        title="Kernel Update",
        description="Review",
        comments="",
        news_items=[types.SimpleNamespace(news_item_data=data)],
    )


@pytest.fixture
def no_lookup() -> Iterator[list]:
    """Record search index lookups; a new aggregate must not make any.

    `query` is Flask-SQLAlchemy's descriptor, inherited from db.Model; reading it needs an
    application context, so monkeypatch cannot save it. Shadowing it on the class and deleting
    the shadow afterwards restores it.
    """
    lookups = []

    class Query:
        def filter_by(self, **criteria: object) -> types.SimpleNamespace:
            lookups.append(criteria)
            return types.SimpleNamespace(first=lambda: None)

    assert "query" not in vars(NewsItemAggregateSearchIndex)
    NewsItemAggregateSearchIndex.query = Query()
    yield lookups
    del NewsItemAggregateSearchIndex.query


def test_a_new_aggregate_gets_its_row_without_a_lookup(monkeypatch: pytest.MonkeyPatch, no_lookup: list) -> None:
    aggregate = make_aggregate(None)
    session = FakeSession(aggregate)
    monkeypatch.setattr(news_item_module, "db", types.SimpleNamespace(session=session))

    NewsItemAggregateSearchIndex.prepare(aggregate, commit=False)

    assert no_lookup == []
    (row,) = session.added
    assert row.news_item_aggregate_id == 42
    assert row.data == "kernel update review  kernel update review body text psirt https://example.com/a cve-2026-1234"
    # Stored with the batch, not on its own.
    assert session.commits == 0


def test_an_existing_aggregate_is_looked_up_and_committed(monkeypatch: pytest.MonkeyPatch, no_lookup: list) -> None:
    aggregate = make_aggregate(5)
    session = FakeSession(aggregate)
    monkeypatch.setattr(news_item_module, "db", types.SimpleNamespace(session=session))

    NewsItemAggregateSearchIndex.prepare(aggregate)

    assert no_lookup == [{"news_item_aggregate_id": 5}]
    assert session.flushes == 0
    assert session.commits == 1


def test_content_is_parsed_to_plain_text_once(monkeypatch: pytest.MonkeyPatch) -> None:
    parses = []

    def strip_html(html: str) -> str:
        parses.append(html)
        return html.replace("<p>", "").replace("</p>", "")

    monkeypatch.setattr(news_item_module, "strip_html", strip_html)
    data = NewsItemData(
        id="item-1",
        hash="hash-1",
        title="Advisory",
        review="Review",
        source="https://example.com/csaf",
        link="https://example.com/advisory",
        published="01.09.2026 - 10:00",
        author="PSIRT",
        collected=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
        content="<p>First</p>",
        osint_source_id="source-1",
        attributes=[],
    )

    assert data.content_plaintext == "First"
    assert data.content_plaintext == "First"
    assert parses == ["<p>First</p>"]

    # A new revision replaces the content: parsed again.
    data.content = "<p>Second</p>"
    assert data.content_plaintext == "Second"
    assert len(parses) == 2
