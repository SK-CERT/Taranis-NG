"""Saving a report item attribute: what is stored, and when a save is refused as a conflict.

Users reported values "not always saved" when adding several attributes to a report. On the
server side two things could lose an edit: two saves based on the same version both passed the
version check (the second silently overwrote the first), and a description cleared to "" was
ignored. Core tests have no database: the report item and the session are stand-ins.
"""

from __future__ import annotations

import types

import pytest
from model import report_item as report_item_module
from model.report_item import ReportItem

USER = types.SimpleNamespace(id=3, name="Analyst")


def _attribute(**fields: object) -> types.SimpleNamespace:
    defaults = {"id": 5, "value": "old", "value_description": "old note", "version": 3, "last_updated": None, "user": None}
    return types.SimpleNamespace(**{**defaults, **fields})


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """A report item with one attribute; the session records refreshes and commits."""
    attribute = _attribute()
    report_item = types.SimpleNamespace(id=1, language=None, attributes=[attribute], update_cpes=lambda: None)
    recorded = types.SimpleNamespace(attribute=attribute, refreshes=[], commits=0, stored_version=None)

    def refresh(instance: object, attribute_names: list | None = None, with_for_update: bool = False) -> None:
        recorded.refreshes.append((instance, attribute_names, with_for_update))
        if recorded.stored_version is not None:
            instance.version = recorded.stored_version

    def commit() -> None:
        recorded.commits += 1

    session = types.SimpleNamespace(get=lambda _cls, _id: report_item, refresh=refresh, commit=commit)
    monkeypatch.setattr(report_item_module.db, "session", session)
    return recorded


def test_the_version_is_checked_under_a_row_lock(stored: types.SimpleNamespace) -> None:
    """Another save bumped the stored version after this request loaded the report item."""
    stored.stored_version = 4

    modified, data = ReportItem.update_report_item(1, {"update": True, "attribute_id": 5, "attribute_value": "mine", "base_version": 3}, USER)

    assert modified is False
    assert data["conflict"]["current_version"] == 4
    assert stored.attribute.value == "old"
    ((instance, names, locked),) = stored.refreshes
    assert (instance, names, locked) == (stored.attribute, ["version"], True)


def test_a_save_on_the_current_version_goes_through(stored: types.SimpleNamespace) -> None:
    modified, data = ReportItem.update_report_item(1, {"update": True, "attribute_id": 5, "attribute_value": "mine", "base_version": 3}, USER)

    assert modified is True
    assert stored.attribute.value == "mine"
    assert data["attribute_version"] == 4


def test_a_cleared_description_is_stored(stored: types.SimpleNamespace) -> None:
    modified, _data = ReportItem.update_report_item(
        1,
        {"update": True, "attribute_id": 5, "attribute_value": "old", "value_description": ""},
        USER,
    )

    assert modified is True
    assert stored.attribute.value_description == ""


def test_an_empty_description_for_none_changes_nothing(stored: types.SimpleNamespace) -> None:
    """Sending "" for a value that never had a description must not bump the version: every other client would then get a false conflict."""
    stored.attribute.value_description = None

    modified, data = ReportItem.update_report_item(
        1,
        {"update": True, "attribute_id": 5, "attribute_value": "old", "value_description": ""},
        USER,
    )

    assert modified is False
    assert "attribute_version" not in data
    assert stored.attribute.version == 3
