"""Collectors preserve instants when exchanging timestamps with core and HTTP servers."""

from datetime import UTC, datetime, timedelta, timezone
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from collectors.base_collector import BaseCollector, not_modified
from collectors.rss_collector import RSSCollector
from shared.time_manager import SchedulerManager


@pytest.mark.parametrize("field", ["published", "updated"])
def test_rss_parsed_dates_are_already_utc(field: str) -> None:
    collector = RSSCollector()
    collector.source = SimpleNamespace(logger=Mock())
    parsed = (2026, 7, 1, 22, 30, 0, 2, 182, 0)
    result = collector._resolve_date(parsed if field == "published" else (), parsed if field == "updated" else (), "", "")
    assert result == "2026-07-01T22:30:00Z"


def test_rss_raw_publication_text_is_preserved() -> None:
    collector = RSSCollector()
    collector.source = SimpleNamespace(logger=Mock())
    assert collector._resolve_date((), (), "date unknown", "") == "date unknown"


def test_scheduler_due_time_is_serialized_with_utc_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = BaseCollector()
    collector.osint_sources = [SimpleNamespace(id="source-1")]
    job = SimpleNamespace(next_run=datetime(2026, 7, 2, 0, 30, tzinfo=timezone(timedelta(hours=2))))
    monkeypatch.setattr(SchedulerManager, "get_jobs_by_tag", lambda _tag: [job])
    assert collector.next_run_by_source() == {"source-1": "2026-07-01T22:30:00Z"}


@pytest.mark.parametrize("offset", [0, 2, -5])
def test_if_modified_since_converts_the_instant_to_gmt(offset: int) -> None:
    instant = datetime(2026, 7, 1, 22, 30, tzinfo=UTC)
    last_collected = instant.astimezone(timezone(timedelta(hours=offset)))
    response = Mock()
    response.status = HTTPStatus.OK
    response.headers = {"Last-Modified": "Wed, 01 Jul 2026 22:29:00 GMT"}
    opener = Mock()
    opener.return_value.__enter__ = Mock(return_value=response)
    opener.return_value.__exit__ = Mock(return_value=False)
    source = SimpleNamespace(last_collected=last_collected, user_agent="", url="https://example.test/feed", opener=opener, logger=Mock())

    assert not_modified(source) is True
    request = opener.call_args.args[0]
    assert request.get_header("If-modified-since") == "Wed, 01 Jul 2026 22:30:00 GMT"
    assert source.last_collected == instant
