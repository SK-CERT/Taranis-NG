"""The product detail endpoint must mark its report items accessible.

``Product.get_json`` (the product *list*) sets ``see``/``access``/``modify`` on
every report item it returns, and the GUI relies on that: a report card only
opens the report detail dialog when ``card.access === true``. When the edit
dialog started loading the product through ``GET /publish/products/<id>``
instead of reusing the list row, those flags disappeared - marshmallow simply
omits an attribute the model does not carry - and clicking a report item inside
an existing product silently did nothing. These tests pin the flags onto the
detail payload.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING

import pytest
from model.product import Product

if TYPE_CHECKING:
    from collections.abc import Callable


class _FakeSession:
    """A ``db.session`` stand-in that answers a single primed ``get``."""

    def __init__(self, product: object | None) -> None:
        self._product = product
        self.requested: list = []

    def get(self, model: type, primary_key: object) -> object | None:
        """Record the lookup and hand back the primed product."""
        self.requested.append((model, primary_key))
        return self._product


def _report_item(item_id: int, title: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(id=item_id, uuid=f"uuid-{item_id}", title=title, title_prefix="")


def _product(report_items: list) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id=7,
        title="Weekly report",
        description="",
        product_type_id=3,
        state_id=2,
        public_webs=[types.SimpleNamespace(id=11), types.SimpleNamespace(id=12)],
        report_items=report_items,
    )


@pytest.fixture
def primed_session(monkeypatch: pytest.MonkeyPatch) -> Callable[[object | None], _FakeSession]:
    """Point ``Product``'s db session at a product the test supplies."""

    def _prime(product: object | None) -> _FakeSession:
        from managers import db_manager  # noqa: PLC0415 - after the stub config is in place

        session = _FakeSession(product)
        monkeypatch.setattr(db_manager.db, "session", session)
        return session

    return _prime


def test_detail_marks_report_items_accessible(primed_session: Callable[[object | None], _FakeSession]) -> None:
    """Every report item in the detail payload carries the ACL status flags."""
    primed_session(_product([_report_item(1, "First"), _report_item(2, "Second")]))

    detail = Product.get_detail_json(7)

    assert [item["title"] for item in detail["report_items"]] == ["First", "Second"]
    for item in detail["report_items"]:
        assert item["see"] is True
        assert item["access"] is True
        assert item["modify"] is True


def test_detail_still_reports_public_web_targeting(primed_session: Callable[[object | None], _FakeSession]) -> None:
    """The public-web ids keep being derived from the product's webs."""
    primed_session(_product([]))

    detail = Product.get_detail_json(7)

    assert detail["public_web_ids"] == [11, 12]
    assert detail["report_items"] == []


def test_detail_of_a_missing_product_is_empty(primed_session: Callable[[object | None], _FakeSession]) -> None:
    """A product id nobody owns dumps to an empty payload instead of raising."""
    primed_session(None)

    assert Product.get_detail_json(404) == {}
