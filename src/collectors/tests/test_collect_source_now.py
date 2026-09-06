"""Collecting one source on demand, without waiting for its schedule.

The call has to answer immediately, because a real run takes minutes - one Broadcom source takes
twelve. So the answer cannot describe the result of the collection, only whether a run was
started, and that has to be decided before the thread is handed the work. These tests pin that:
the claim is taken synchronously, the call returns while the run is still going, and a second
caller is told the source is busy rather than starting a second browser on the same site.
"""

import threading
import types
from http import HTTPStatus

import pytest
from collectors.base_collector import BaseCollector


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Nothing is collecting when a test starts."""
    BaseCollector._running_sources.clear()


def make_source(source_id: str, name: str = "a source", *, enabled: bool = True) -> types.SimpleNamespace:
    """The minimal source object the on-demand path reads."""
    return types.SimpleNamespace(
        id=source_id,
        name=name,
        enabled=enabled,
        param_key_values={"REFRESH_INTERVAL": "5"},
        word_lists=[],
    )


class FakeCollector(BaseCollector):
    """A collector whose runs record themselves instead of reaching the network."""

    collector_type = "FAKE_COLLECTOR"
    name = "Fake Collector"

    def __init__(self) -> None:
        """Start with no sources and nothing collected."""
        super().__init__()
        self.ran: list[str] = []
        self.reloaded = 0

    def _do_run(self, source: object) -> None:
        self.ran.append(source.id)

    def _reload_sources(self) -> None:
        self.reloaded += 1


def test_collecting_a_known_source_starts_a_run() -> None:
    collector = FakeCollector()
    collector.osint_sources = [make_source("s1")]

    body, status = collector.collect_source_now("s1")

    assert status == HTTPStatus.ACCEPTED
    assert body == {"started": True}


def test_an_unknown_source_is_reported_not_started() -> None:
    collector = FakeCollector()
    collector.osint_sources = []

    _, status = collector.collect_source_now("nope")

    assert status == HTTPStatus.NOT_FOUND
    assert collector.ran == []


def test_a_source_missing_from_the_cache_is_looked_up_once_more() -> None:
    # A source created since the last refresh is not in the cached list yet.
    collector = FakeCollector()
    collector.osint_sources = []

    collector.collect_source_now("s1")

    assert collector.reloaded == 1


def test_a_second_request_while_collecting_is_refused() -> None:
    collector = FakeCollector()
    collector.osint_sources = [make_source("s1")]
    assert BaseCollector._try_begin_run("s1") is True  # something else is already collecting it

    body, status = collector.collect_source_now("s1")

    assert status == HTTPStatus.CONFLICT
    assert body == {"error": "already collecting"}
    assert collector.ran == []


def test_the_call_returns_while_the_run_is_still_going() -> None:
    started = threading.Event()
    finish = threading.Event()

    class BlockingCollector(FakeCollector):
        """Holds its run open so the test can observe the call returning."""

        def _do_run(self, source: object) -> None:
            self.ran.append(source.id)
            started.set()
            finish.wait(5)

    collector = BlockingCollector()
    collector.osint_sources = [make_source("s1")]

    _, status = collector.collect_source_now("s1")

    assert status == HTTPStatus.ACCEPTED
    assert started.wait(5)  # the run is under way...
    assert BaseCollector.is_running("s1") is True  # ...and still holds the claim

    finish.set()
    for _ in range(50):
        if not BaseCollector.is_running("s1"):
            break
        threading.Event().wait(0.1)
    assert BaseCollector.is_running("s1") is False


def test_the_claim_is_released_when_an_on_demand_run_fails() -> None:
    class ExplodingCollector(FakeCollector):
        """Fails the way a collector does when its run blows up."""

        def _do_run(self, source: object) -> None:
            msg = f"collection of {source.id} blew up"
            raise RuntimeError(msg)

    collector = ExplodingCollector()
    collector.osint_sources = [make_source("s1")]

    collector.collect_source_now("s1")

    for _ in range(50):
        if not BaseCollector.is_running("s1"):
            break
        threading.Event().wait(0.1)
    assert BaseCollector.is_running("s1") is False


def test_a_switched_off_source_is_not_collected() -> None:
    collector = FakeCollector()
    collector.osint_sources = [make_source("s1", enabled=False)]

    body, status = collector.collect_source_now("s1")

    assert status == HTTPStatus.CONFLICT
    assert body == {"error": "OSINT source is switched off"}
    assert collector.ran == []
    # and the claim was never taken, so a later run is not blocked
    assert BaseCollector.is_running("s1") is False
