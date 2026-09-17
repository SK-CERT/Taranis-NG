"""What core records when a collector starts and finishes a run.

The collector brackets every run with two calls it already makes: one as the run starts, one as it
ends. Core splits what it learns between two places, and which half goes where is the thing worth
pinning here.

The database keeps the history an operator looks back on: when a run was last attempted, and what
went wrong. Redis keeps the live state, because it describes a process that may be killed and would
otherwise leave the source looking busy forever.

No database and no Redis: both are replaced with fakes, which is also what proves each method
touches only what it claims to.
"""

from __future__ import annotations

import types

import model.osint_source as osint_source_module
import pytest
from model.osint_source import OSINTSource


class FakeCache:
    """Records what the model asked the run-state cache to do."""

    def __init__(self) -> None:
        """Start with nothing marked."""
        self.marked: list[str] = []
        self.cleared: list[str] = []

    def mark_collecting(self, source_id: str) -> None:
        """Record a run starting."""
        self.marked.append(source_id)

    def clear_collecting(self, source_id: str) -> None:
        """Record a run finishing."""
        self.cleared.append(source_id)


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """A single source behind db.session.get(), plus a fake run-state cache."""
    source = types.SimpleNamespace(last_attempted=None, last_error_message=None, enabled=True)
    cache = FakeCache()
    state = types.SimpleNamespace(source=source, cache=cache, commits=0)

    def commit() -> None:
        state.commits += 1

    monkeypatch.setattr(
        osint_source_module.db,
        "session",
        types.SimpleNamespace(get=lambda _cls, _ident: source, commit=commit),
    )
    monkeypatch.setattr(osint_source_module, "run_state_cache", cache)
    return state


def test_a_run_starting_is_recorded_in_both_places(stored: types.SimpleNamespace) -> None:
    OSINTSource.mark_collection_started("source-1")

    # History goes to the database...
    assert stored.source.last_attempted is not None
    assert stored.commits == 1
    # ...live state to the cache, where it can expire if the collector dies.
    assert stored.cache.marked == ["source-1"]


def test_a_run_finishing_keeps_the_error_and_frees_the_source(stored: types.SimpleNamespace) -> None:
    OSINTSource.mark_collection_started("source-1")

    OSINTSource.mark_collection_finished("source-1", "it went wrong")

    assert stored.source.last_error_message == "it went wrong"
    assert stored.cache.cleared == ["source-1"]
    # last_attempted survives: it is when the run started, not when it ended.
    assert stored.source.last_attempted is not None


def test_a_successful_run_reports_no_error_and_still_frees_the_source(stored: types.SimpleNamespace) -> None:
    OSINTSource.mark_collection_started("source-1")

    # The collector sends an empty message when nothing went wrong.
    OSINTSource.mark_collection_finished("source-1", None)

    assert stored.source.last_error_message is None
    assert stored.cache.cleared == ["source-1"]


def test_setting_enabled_touches_only_that_column(stored: types.SimpleNamespace) -> None:
    OSINTSource.set_enabled("source-1", enabled=False)

    assert stored.source.enabled is False
    assert stored.source.last_error_message is None
    # Switching a source off is not a run: nothing about the cache changes.
    assert stored.cache.marked == []
    assert stored.cache.cleared == []
