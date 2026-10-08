"""The tag cloud: which words count, how a batch is written, how the cloud is read.

Core tests run without a database, so the session and Redis are replaced by fakes.
"""

from __future__ import annotations

import contextlib
import datetime
import types
from collections import Counter

import pytest
from model import tag_cloud as tag_cloud_module
from model.setting import Setting
from model.tag_cloud import CACHE_SECONDS_TODAY, TagCloud
from sqlalchemy.exc import OperationalError


def words_of(title: str = "", review: str = "", content: str = "") -> set[str]:
    return TagCloud.words(types.SimpleNamespace(title=title, review=review, content_plaintext=content))


# --- which words count -----------------------------------------------------------------


def test_word_like_tokens_are_kept_whole() -> None:
    assert words_of("Zero-day in CVE-2026-1234 affects Node.js; don't panic.") == {
        "zero-day",
        "cve-2026-1234",
        "affects",
        "node.js",
        "don't",
        "panic",
    }


@pytest.mark.parametrize(
    "chunk",
    [
        "https://access.redhat.com/errata/RHSA-2026:72508",
        "security@example.com",
        "CVSS:3.1/AV:N/AC:L",
        "x86_64",
        "RHSA-2026:72508",
        "csaf_security_advisory",
        "openssl-3.0.7-27.el9",
        "2026",
        "4.20",
        "2026-09-29",
        "e.g.",
        "0123456789abcdef0123456789abcdef",
        "a" * 41,
        "ab",
        '<a href="https://example.com/">',
    ],
)
def test_structured_chunks_are_left_out_whole(chunk: str) -> None:
    # Not glued into a word no other item shares, and not split into fragments like "av".
    assert words_of(content=f"keep {chunk} this") == {"keep", "this"}


def test_surrounding_punctuation_is_stripped() -> None:
    assert words_of(content='(high), "quoted" [bracketed]: end.') == {"high", "quoted", "bracketed", "end"}


def test_a_typographic_apostrophe_matches_the_stopword_form() -> None:
    assert words_of(content="don\N{RIGHT SINGLE QUOTATION MARK}t") == {"don't"}


def test_words_in_any_script_are_counted() -> None:
    assert words_of(content="уязвимость sécurité") == {"уязвимость", "sécurité"}


def test_each_word_counts_once_per_item_and_is_lowercased() -> None:
    assert words_of("Kernel update", "kernel KERNEL", "Kernel") == {"kernel", "update"}


# --- writing ---------------------------------------------------------------------------


class FakeSession:
    """Records the statements add_words runs, optionally failing them."""

    def __init__(self, error: Exception | None = None) -> None:
        """Start with nothing run."""
        self.error = error
        self.executed: list[tuple[str, dict]] = []
        self.flushes = 0
        self.savepoints = 0

    def flush(self) -> None:
        """Count a flush."""
        self.flushes += 1

    @contextlib.contextmanager
    def begin_nested(self) -> object:
        """Open a savepoint; an error inside it propagates, as SQLAlchemy's does."""
        self.savepoints += 1
        yield

    def execute(self, statement: object, params: dict) -> None:
        """Record a statement, or fail it."""
        if self.error is not None:
            raise self.error
        self.executed.append((str(statement), params))


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> FakeSession:
    fake = FakeSession()
    monkeypatch.setattr(tag_cloud_module, "db", types.SimpleNamespace(session=fake))
    return fake


def test_a_batch_is_one_upsert_in_a_savepoint(session: FakeSession) -> None:
    TagCloud.add_words(Counter({"kernel": 3, "openssl": 1}))

    ((statement, params),) = session.executed
    assert "ON CONFLICT (collected, word) DO UPDATE" in statement
    assert "ORDER BY v.word" in statement
    assert dict(zip(params["words"], params["quantities"], strict=True)) == {"kernel": 3, "openssl": 1}
    assert (session.flushes, session.savepoints) == (1, 1)


def test_nothing_to_count_runs_nothing(session: FakeSession) -> None:
    TagCloud.add_words(Counter())

    assert session.executed == []
    assert session.flushes == 0


def test_a_failed_upsert_does_not_cost_the_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSession(error=OperationalError("INSERT", {}, Exception("no unique constraint")))
    monkeypatch.setattr(tag_cloud_module, "db", types.SimpleNamespace(session=fake))
    logged = []
    monkeypatch.setattr(tag_cloud_module.logger, "exception", logged.append)

    TagCloud.add_words(Counter({"kernel": 1}))  # does not raise

    assert logged == ["Tag cloud not updated; the news items are stored all the same"]


# --- reading ---------------------------------------------------------------------------


class FakeRedis:
    """Enough Redis for the cache, including a broken mode."""

    def __init__(self, *, broken: bool = False) -> None:
        """Start empty."""
        self.store: dict[str, bytes] = {}
        self.expiries: dict[str, int] = {}
        self.broken = broken

    def get(self, key: str) -> bytes | None:
        """Return a stored value."""
        if self.broken:
            msg = "redis is down"
            raise ConnectionError(msg)
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int) -> None:
        """Store a value with its expiry."""
        if self.broken:
            msg = "redis is down"
            raise ConnectionError(msg)
        self.store[key] = value.encode()
        self.expiries[key] = ex


WORDS = [{"word": "kernel", "word_quantity": 5}]


@pytest.fixture
def queries(monkeypatch: pytest.MonkeyPatch) -> list:
    made = []

    def query(_cls: type, date_from: datetime.date, date_to: datetime.date) -> list[dict]:
        made.append((date_from, date_to))
        return WORDS

    monkeypatch.setattr(TagCloud, "_query_grouped_words", classmethod(query))
    return made


def test_the_cloud_is_cached_and_served_from_the_cache(monkeypatch: pytest.MonkeyPatch, queries: list) -> None:
    redis = FakeRedis()
    monkeypatch.setattr(tag_cloud_module, "redis_client", redis)
    today = datetime.datetime.now(tag_cloud_module.TZ).date()

    assert TagCloud.get_grouped_words_between(today, today) == WORDS
    assert TagCloud.get_grouped_words_between(today, today) == WORDS

    assert len(queries) == 1
    assert redis.expiries == {f"tag-cloud:top:{today}:{today}": CACHE_SECONDS_TODAY}


def test_a_redis_outage_costs_the_cache_not_the_dashboard(monkeypatch: pytest.MonkeyPatch, queries: list) -> None:
    monkeypatch.setattr(tag_cloud_module, "redis_client", FakeRedis(broken=True))
    today = datetime.datetime.now(tag_cloud_module.TZ).date()

    assert TagCloud.get_grouped_words_between(today, today) == WORDS
    assert len(queries) == 1


def test_a_period_including_today_is_cached_for_a_minute() -> None:
    now = datetime.datetime(2026, 9, 29, 12, 0, tzinfo=datetime.UTC)
    assert TagCloud._cache_seconds(datetime.date(2026, 9, 29), now) == CACHE_SECONDS_TODAY


def test_a_past_period_is_cached_until_after_the_nightly_cleanup() -> None:
    now = datetime.datetime(2026, 9, 29, 12, 0, tzinfo=datetime.UTC)
    # Until 00:05 tomorrow: twelve hours and five minutes.
    assert TagCloud._cache_seconds(datetime.date(2026, 9, 28), now) == 12 * 3600 + 5 * 60


def test_a_past_period_read_before_the_cleanup_expires_right_after_it() -> None:
    # The cleanup runs at 00:01: a cloud read at 00:00:30 must not outlive it by a day.
    now = datetime.datetime(2026, 9, 29, 0, 0, 30, tzinfo=datetime.UTC)
    assert TagCloud._cache_seconds(datetime.date(2026, 9, 28), now) == 4 * 60 + 30


def test_a_past_period_is_cached_at_least_a_minute() -> None:
    now = datetime.datetime(2026, 9, 29, 0, 4, 30, tzinfo=datetime.UTC)
    assert TagCloud._cache_seconds(datetime.date(2026, 9, 28), now) == CACHE_SECONDS_TODAY


# --- retention -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stored", "days"),
    [("7", 7), (" 30 ", 30), ("abc", 7), ("", 7), ("0", 1), ("-5", 1), ("1000", 365)],
)
def test_retention_comes_from_the_setting_within_bounds(monkeypatch: pytest.MonkeyPatch, stored: str, days: int) -> None:
    monkeypatch.setattr(Setting, "get_setting", classmethod(lambda _cls, _user, _key, _default="": stored))

    assert TagCloud.retention_days() == days


def test_the_oldest_date_kept_follows_the_retention(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Setting, "get_setting", classmethod(lambda _cls, _user, _key, _default="": "7"))

    assert TagCloud.oldest_date(datetime.date(2026, 9, 29)) == datetime.date(2026, 9, 22)
