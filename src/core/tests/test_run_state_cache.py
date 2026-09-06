"""A source's run state is cache, not record.

Both halves describe a collector node that is running. The schedule is rebuilt from scratch on
every node start and refresh, so serving a stored time after a restart would promise a collection
nobody intends to make. A run in progress belongs to a process that may be killed, and then nothing
would ever report its end.

Redis expiry answers both. These tests pin what that buys: a schedule that fades when a node stops
reporting, a run that frees its source on its own when its collector dies, and a Redis outage that
costs the display rather than the request.
"""

from __future__ import annotations

import pytest
from managers import run_state_cache


class FakeRedis:
    """Enough Redis to exercise the cache, including a broken mode."""

    def __init__(self, *, broken: bool = False) -> None:
        """Start empty, optionally failing every call."""
        self.store: dict[str, str] = {}
        self.expiries: dict[str, int] = {}
        self.broken = broken

    def _check(self) -> None:
        if self.broken:
            msg = "redis is down"
            raise ConnectionError(msg)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        """Store a value with its expiry."""
        self._check()
        self.store[key] = value
        if ex is not None:
            self.expiries[key] = ex

    def mget(self, keys: list[str]) -> list[str | None]:
        """Read several values at once."""
        self._check()
        return [self.store.get(key) for key in keys]

    def scan_iter(self, match: str) -> list[str]:
        """Find keys by prefix."""
        self._check()
        prefix = match.rstrip("*")
        return [key for key in self.store if key.startswith(prefix)]

    def delete(self, *keys: str) -> None:
        """Forget keys."""
        self._check()
        for key in keys:
            self.store.pop(key, None)


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """Point the cache at a fake Redis."""
    fake = FakeRedis()
    monkeypatch.setattr(run_state_cache, "redis_client", fake)
    return fake


@pytest.mark.usefixtures("redis")
def test_a_next_run_can_be_stored_and_read_back() -> None:
    run_state_cache.set_next_run("source-1", "2026-09-04T12:00:00+00:00")

    assert run_state_cache.get_next_runs(["source-1"]) == {"source-1": "2026-09-04T12:00:00+00:00"}


def test_entries_expire_so_a_node_that_stopped_reporting_stops_promising_a_run(redis: FakeRedis) -> None:
    run_state_cache.set_next_run("source-1", "2026-09-04T12:00:00+00:00")

    assert redis.expiries["osint-source:next-run:source-1"] == run_state_cache.NEXT_RUN_TTL_SECONDS


@pytest.mark.usefixtures("redis")
def test_sources_without_a_schedule_are_simply_absent() -> None:
    run_state_cache.set_next_run("source-1", "2026-09-04T12:00:00+00:00")

    result = run_state_cache.get_next_runs(["source-1", "source-2"])

    assert result == {"source-1": "2026-09-04T12:00:00+00:00"}


def test_asking_for_nothing_does_not_touch_redis(redis: FakeRedis) -> None:
    redis.broken = True  # any call would raise

    assert run_state_cache.get_next_runs([]) == {}


def test_starting_core_forgets_every_cached_schedule(redis: FakeRedis) -> None:
    run_state_cache.set_next_run("source-1", "2026-09-04T12:00:00+00:00")
    run_state_cache.set_next_run("source-2", "2026-09-04T13:00:00+00:00")
    redis.store["unrelated:key"] = "keep me"

    run_state_cache.clear_all()

    assert run_state_cache.get_next_runs(["source-1", "source-2"]) == {}
    assert "unrelated:key" in redis.store


def test_a_redis_outage_costs_the_countdown_not_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_state_cache, "redis_client", FakeRedis(broken=True))

    # None of these may raise: a countdown is not worth failing a page over.
    run_state_cache.set_next_run("source-1", "2026-09-04T12:00:00+00:00")
    run_state_cache.clear_all()

    assert run_state_cache.get_next_runs(["source-1"]) == {}


@pytest.mark.usefixtures("redis")
def test_a_run_can_be_marked_and_cleared() -> None:
    run_state_cache.mark_collecting("source-1")
    assert run_state_cache.get_collecting(["source-1"]) == {"source-1"}

    run_state_cache.clear_collecting("source-1")
    assert run_state_cache.get_collecting(["source-1"]) == set()


def test_a_run_expires_so_a_dead_collector_frees_its_source(redis: FakeRedis) -> None:
    # Nothing else would ever clear this: the collector that would report the end is gone.
    run_state_cache.mark_collecting("source-1")

    assert redis.expiries["osint-source:collecting:source-1"] == run_state_cache.COLLECTING_TTL_SECONDS


@pytest.mark.usefixtures("redis")
def test_only_the_sources_asked_about_are_reported() -> None:
    run_state_cache.mark_collecting("source-1")

    assert run_state_cache.get_collecting(["source-1", "source-2"]) == {"source-1"}


@pytest.mark.usefixtures("redis")
def test_asking_about_no_sources_reports_nothing() -> None:
    assert run_state_cache.get_collecting([]) == set()


@pytest.mark.usefixtures("redis")
def test_starting_core_forgets_runs_that_nobody_can_finish() -> None:
    # A compose restart takes the collector nodes down with core, so nothing is left to report
    # these runs finishing. Keeping them would leave the sources claiming to collect for hours.
    run_state_cache.mark_collecting("source-1")
    run_state_cache.set_next_run("source-1", "2026-09-04T12:00:00+00:00")

    run_state_cache.clear_all()

    assert run_state_cache.get_collecting(["source-1"]) == set()
    assert run_state_cache.get_next_runs(["source-1"]) == {}


def test_a_redis_outage_leaves_the_run_state_unknown_not_broken(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_state_cache, "redis_client", FakeRedis(broken=True))

    run_state_cache.mark_collecting("source-1")
    run_state_cache.clear_collecting("source-1")

    assert run_state_cache.get_collecting(["source-1"]) == set()
