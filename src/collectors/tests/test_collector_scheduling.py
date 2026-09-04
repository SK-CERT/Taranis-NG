"""Tests for how collectors schedule their sources and guard against overlapping runs.

Two properties are asserted here, both of which were broken and caused real damage:

- refresh() used to leave its scheduler jobs behind, so a source ended up scheduled once per
  refresh that had ever run, and was then collected several times at once.
- Nothing stopped two runs of the same source overlapping, which meant two browsers on the same
  site, half-rendered pages, and duplicated news items.

Nothing here touches the network: the collectors are fakes whose _do_run only records a call.
"""

import threading
import types
from collections.abc import Iterator

import pytest
import schedule
from collectors.base_collector import BaseCollector
from shared.time_manager import SchedulerManager


@pytest.fixture(autouse=True)
def _clean_scheduler() -> Iterator[None]:
    """Keep the process-global scheduler and the run registry from leaking between tests."""
    schedule.clear()
    BaseCollector._running_sources.clear()
    yield
    schedule.clear()
    BaseCollector._running_sources.clear()


def make_source(source_id: str, name: str = "a source", interval: str = "5") -> types.SimpleNamespace:
    """Build the minimal source object the scheduling and run paths read."""
    return types.SimpleNamespace(
        id=source_id,
        name=name,
        param_key_values={"REFRESH_INTERVAL": interval},
        word_lists=[],
    )


class FakeCollector(BaseCollector):
    """A collector that records the sources it was asked to collect, and collects nothing."""

    collector_type = "FAKE_COLLECTOR"
    name = "Fake Collector"

    def __init__(self) -> None:
        """Start with an empty record of collected sources."""
        super().__init__()
        self.ran: list[str] = []

    def _do_run(self, source: object) -> None:
        self.ran.append(source.id)


class OtherCollector(FakeCollector):
    """A second collector type, to prove one collector's cancel does not touch another's jobs."""

    collector_type = "OTHER_COLLECTOR"
    name = "Other Collector"


def test_rescheduling_a_source_does_not_stack_up_jobs() -> None:
    collector = FakeCollector()
    source = make_source("s1")

    # Three refreshes' worth of scheduling, each preceded by the cancel refresh() performs.
    for _ in range(3):
        SchedulerManager.cancel_jobs_by_tag(collector._collector_tag)
        collector._schedule_source(source, "5")

    assert len(SchedulerManager.get_jobs_by_tag("collector:FAKE_COLLECTOR")) == 1
    assert len(SchedulerManager.get_jobs_by_tag("source:s1")) == 1


def test_cancelling_one_collectors_jobs_leaves_other_collectors_alone() -> None:
    fake, other = FakeCollector(), OtherCollector()
    fake._schedule_source(make_source("s1"), "5")
    other._schedule_source(make_source("s2"), "5")

    SchedulerManager.cancel_jobs_by_tag(fake._collector_tag)

    assert SchedulerManager.get_jobs_by_tag("collector:FAKE_COLLECTOR") == []
    assert len(SchedulerManager.get_jobs_by_tag("collector:OTHER_COLLECTOR")) == 1


def test_every_supported_interval_format_is_tagged() -> None:
    collector = FakeCollector()
    for index, interval in enumerate(["5", "13:30", "Monday, 10:00"]):
        collector._schedule_source(make_source(f"s{index}", interval=interval), interval)

    assert len(SchedulerManager.get_jobs_by_tag("collector:FAKE_COLLECTOR")) == 3


def test_an_unschedulable_interval_is_reported_not_raised() -> None:
    collector = FakeCollector()
    collector._schedule_source(make_source("s1"), "Caturday, 10:00")

    assert SchedulerManager.get_jobs_by_tag("collector:FAKE_COLLECTOR") == []


def test_a_source_can_only_be_claimed_once() -> None:
    assert BaseCollector._try_begin_run("s1") is True
    assert BaseCollector._try_begin_run("s1") is False
    assert BaseCollector.is_running("s1") is True

    BaseCollector._end_run("s1")

    assert BaseCollector.is_running("s1") is False
    assert BaseCollector._try_begin_run("s1") is True


def test_run_collector_skips_a_source_that_is_already_collecting() -> None:
    running = threading.Event()
    finish = threading.Event()

    class BlockingCollector(FakeCollector):
        """Holds the run open until the test releases it."""

        def _do_run(self, source: object) -> None:
            self.ran.append(source.id)
            running.set()
            finish.wait(5)

    blocking, second = BlockingCollector(), FakeCollector()
    source = make_source("s1")

    thread = threading.Thread(target=blocking.run_collector, args=(source,))
    thread.start()
    assert running.wait(5)

    second.run_collector(source)  # same source, while the first run holds it

    assert second.ran == []
    finish.set()
    thread.join(5)
    assert BaseCollector.is_running("s1") is False


def test_two_different_sources_may_run_at_the_same_time() -> None:
    collector = FakeCollector()
    assert BaseCollector._try_begin_run("s1") is True

    collector.run_collector(make_source("s2"))

    assert collector.ran == ["s2"]


def test_the_claim_is_released_when_a_run_raises() -> None:
    class ExplodingCollector(FakeCollector):
        """Fails the way a collector does when its run blows up."""

        def _do_run(self, source: object) -> None:
            msg = f"collection of {source.id} blew up"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError):
        ExplodingCollector().run_collector(make_source("s1"))

    assert BaseCollector.is_running("s1") is False
