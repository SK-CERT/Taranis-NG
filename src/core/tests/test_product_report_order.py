"""A product keeps its reports in the order it lists them.

The link rows carry a position: the relationship loads the reports by it, and saving a product
writes the order its list has, a reorder of reports it already had included.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.product import Product, ProductReportItem  # noqa: E402 - after every mapper is registered


class _Session:
    """Records the flushes and statements store_report_order makes."""

    def __init__(self) -> None:
        self.calls: list = []

    def flush(self) -> None:
        self.calls.append("flush")

    def execute(self, statement: object, rows: list | None = None) -> None:
        self.calls.append((statement, rows))


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> _Session:
    from managers import db_manager  # noqa: PLC0415 - after the stub config is in place

    fake = _Session()
    monkeypatch.setattr(db_manager.db, "session", fake)
    return fake


def _product(product_id: int, *report_item_ids: int) -> SimpleNamespace:
    return SimpleNamespace(id=product_id, report_items=[SimpleNamespace(id=report_item_id) for report_item_id in report_item_ids])


def test_reports_load_by_their_position_then_their_id() -> None:
    sqlalchemy.orm.configure_mappers()

    order_by = Product.report_items.property.order_by
    assert [column.name for column in order_by] == ["position", "report_item_id"]
    assert {column.table.name for column in order_by} == {"product_report_item"}


def test_the_position_is_a_column_every_row_has() -> None:
    position = ProductReportItem.__table__.c.position

    assert not position.nullable
    assert position.server_default.arg == "0"


def test_the_order_of_the_list_is_stored(session: _Session) -> None:
    Product.store_report_order(_product(7, 31, 12, 25))

    flush, (statement, rows) = session.calls
    assert flush == "flush"
    assert statement.is_update
    assert statement.table.name == "product_report_item"
    assert rows == [
        {"product_id": 7, "report_item_id": 31, "position": 0},
        {"product_id": 7, "report_item_id": 12, "position": 1},
        {"product_id": 7, "report_item_id": 25, "position": 2},
    ]


def test_a_report_listed_twice_keeps_its_first_place(session: _Session) -> None:
    Product.store_report_order(_product(7, 12, 31, 12))

    _flush, (_statement, rows) = session.calls
    assert [(row["report_item_id"], row["position"]) for row in rows] == [(12, 0), (31, 1)]


def test_a_product_without_reports_writes_nothing(session: _Session) -> None:
    Product.store_report_order(_product(7))

    assert session.calls == []
