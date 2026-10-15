"""Reports in a product that is created straight in a FINAL state get completed.

The cascade completing a product's reports used to run only when an existing product was
updated: its state changed toward FINAL, or reports were added to an already FINAL product.
A product created in the publish dialog with its state already set to "published" skipped
both, so its reports stayed "work in progress".
"""

from __future__ import annotations

import types

import pytest
from model import product as product_module
from model.product import Product
from model.report_item import ReportItem
from model.state import StateDefinition, StateEntityTypeEnum, StateManager

PUBLISHED = 1
WORK_IN_PROGRESS = 2
COMPLETED = 3


class _FakeSession:
    """Accepts the new product without a database."""

    def add(self, _instance: object) -> None:
        """Nothing to store."""

    def commit(self) -> None:
        """Nothing to commit."""


@pytest.fixture
def report_updates(monkeypatch: pytest.MonkeyPatch) -> list:
    """Wire the states and report lookups; return the report updates the cascade makes."""
    from managers import db_manager  # noqa: PLC0415 - after the stub config is in place

    final_states = {StateEntityTypeEnum.PRODUCT.value: PUBLISHED, StateEntityTypeEnum.REPORT_ITEM.value: COMPLETED}
    reports = {3193: types.SimpleNamespace(id=3193, state_id=WORK_IN_PROGRESS), 3194: types.SimpleNamespace(id=3194, state_id=COMPLETED)}
    updates: list = []

    monkeypatch.setattr(db_manager.db, "session", _FakeSession())
    monkeypatch.setattr(StateManager, "is_cascade_states_enabled", staticmethod(lambda _user: True))
    monkeypatch.setattr(StateManager, "is_final_state", staticmethod(lambda state_id, entity_type: final_states[entity_type] == state_id))
    final_state = classmethod(lambda _cls, entity_type: types.SimpleNamespace(id=final_states[entity_type]))
    monkeypatch.setattr(StateDefinition, "get_final_state", final_state)
    monkeypatch.setattr(ReportItem, "find", classmethod(lambda _cls, report_item_id: reports.get(report_item_id)))
    monkeypatch.setattr(ReportItem, "update_report_item", classmethod(lambda _cls, *args: updates.append(args)))
    return updates


def _create(monkeypatch: pytest.MonkeyPatch, state_id: int) -> None:
    new_product = types.SimpleNamespace(
        state_id=state_id,
        report_items=[types.SimpleNamespace(id=3193), types.SimpleNamespace(id=3194)],
    )
    monkeypatch.setattr(product_module, "NewProductSchema", lambda: types.SimpleNamespace(load=lambda _data: new_product))
    Product.add_product({}, types.SimpleNamespace(id=1, name="Analyst"))


def test_a_product_created_published_completes_its_unfinished_reports(monkeypatch: pytest.MonkeyPatch, report_updates: list) -> None:
    _create(monkeypatch, PUBLISHED)

    assert [(report_id, data) for report_id, data, _user in report_updates] == [(3193, {"update": True, "state_id": COMPLETED})]


def test_a_product_created_in_progress_leaves_its_reports_alone(monkeypatch: pytest.MonkeyPatch, report_updates: list) -> None:
    _create(monkeypatch, WORK_IN_PROGRESS)

    assert report_updates == []
