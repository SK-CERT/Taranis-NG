"""A product carries only report items its author may read.

Products took report items by id with no report-item ACL check: whoever could publish with one
product preset could put any report item into a product - and read it back whole through the
preview, the language check or the publication - whatever its report type's ACL said.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import publish
from model import product as product_module
from model.product import Product, refused_report_items
from model.report_item import ReportItem

READABLE = {1, 3}
ANALYST = types.SimpleNamespace(id=5, name="Analyst")


@pytest.fixture(autouse=True)
def _acl(monkeypatch: pytest.MonkeyPatch) -> None:
    def allowed(_cls: type, report_item_id: int, _user: object, *, see: bool, access: bool, modify: bool) -> bool:
        assert (see, access, modify) == (False, True, False)
        return report_item_id in READABLE

    monkeypatch.setattr(ReportItem, "allowed_with_acl", classmethod(allowed))


def _items(*ids: int) -> list:
    return [types.SimpleNamespace(id=report_item_id) for report_item_id in ids]


def test_report_items_the_user_may_not_read_are_named() -> None:
    assert refused_report_items([*_items(4, 1, 2), None], ANALYST) == [2, 4]
    assert refused_report_items(_items(1, 3), ANALYST) == []


def test_items_already_in_the_product_are_not_asked_about() -> None:
    assert refused_report_items(_items(1, 2, 4), ANALYST, kept={2}) == [4]


def test_a_system_update_has_no_user_to_refuse() -> None:
    assert refused_report_items(_items(2), None) == []


def test_a_new_product_with_an_unreadable_report_is_not_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded = types.SimpleNamespace(report_items=_items(1, 2))
    monkeypatch.setattr(product_module, "NewProductSchema", lambda: types.SimpleNamespace(load=lambda _data: loaded))
    monkeypatch.setattr(product_module.db.session, "add", lambda _row: pytest.fail("nothing may be stored"))

    with pytest.raises(ValueError, match="report item"):
        Product.add_product({"report_items": [{"id": 1}, {"id": 2}]}, ANALYST)


def test_an_unsaved_product_does_not_render_an_unreadable_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(publish.ProductPreset, "find", classmethod(lambda _cls, _id: types.SimpleNamespace(id=9)))
    monkeypatch.setattr(publish.ReportItem, "find", classmethod(lambda _cls, report_item_id: types.SimpleNamespace(id=report_item_id)))
    monkeypatch.setattr(publish.log_manager, "store_user_auth_error_activity", lambda *_args: None)

    body, status, product, _translations = publish.load_product(
        {"id": -1, "product_preset_id": 9, "report_items": [{"id": 1}, {"id": 2}]},
        ANALYST,
        "token",
    )

    assert status == HTTPStatus.FORBIDDEN
    assert product is None
    assert "2" in body["error"]


def test_the_form_of_a_saved_product_may_check_the_reports_it_already_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    """The language check sends the form unsaved; a colleague's unreadable report already in the product stays usable."""
    stored = types.SimpleNamespace(id=7, product_preset_id=9, report_items=_items(1, 2))
    monkeypatch.setattr(publish.ProductPreset, "find", classmethod(lambda _cls, _id: types.SimpleNamespace(id=9)))
    monkeypatch.setattr(publish.ProductPreset, "allowed_with_acl", classmethod(lambda _cls, preset_id, *_args, **_kwargs: preset_id == 9))
    monkeypatch.setattr(publish.Product, "find", classmethod(lambda _cls, product_id: stored if product_id == 7 else None))
    monkeypatch.setattr(publish.ReportItem, "find", classmethod(lambda _cls, report_item_id: types.SimpleNamespace(id=report_item_id)))
    monkeypatch.setattr(publish.log_manager, "store_user_auth_error_activity", lambda *_args: None)

    def load(stored_id: object, *ids: int) -> HTTPStatus:
        payload = {"id": -1, "stored_id": stored_id, "product_preset_id": 9, "report_items": [{"id": item} for item in ids]}
        return publish.load_product(payload, ANALYST, "token")[1]

    assert load(7, 1, 2) == HTTPStatus.OK
    assert load(7, 1, 2, 4) == HTTPStatus.FORBIDDEN  # one it does not hold yet
    assert load(8, 1, 2) == HTTPStatus.FORBIDDEN  # no such saved product
    assert load("7", 1, 2) == HTTPStatus.FORBIDDEN

    stored.product_preset_id = 10  # a product the user may not use exempts nothing
    assert load(7, 1, 2) == HTTPStatus.FORBIDDEN


def test_an_update_may_keep_an_unreadable_report_but_not_add_one(monkeypatch: pytest.MonkeyPatch) -> None:
    original = types.SimpleNamespace(state_id=1, report_items=_items(2))
    monkeypatch.setattr(Product, "find", classmethod(lambda _cls, _id: original))
    submitted = types.SimpleNamespace(report_items=_items(2, 4))
    monkeypatch.setattr(product_module, "NewProductSchema", lambda: types.SimpleNamespace(load=lambda _data: submitted))

    with pytest.raises(ValueError, match="report item\\(s\\) 4 "):
        Product.update_product(7, {"report_items": [{"id": 2}, {"id": 4}]}, ANALYST)

    assert original.report_items == _items(2)
