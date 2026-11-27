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


@pytest.fixture
def saved_product(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Saved product 7 in product preset 9, holding report 2 a colleague put there; the user may use presets 9 and 10."""
    stored = types.SimpleNamespace(id=7, product_preset_id=9, report_items=_items(1, 2))

    def find_preset(_cls: type, preset_id: object) -> types.SimpleNamespace | None:
        # Like the database, which casts the id it is given: " 9" finds preset 9 too.
        try:
            return types.SimpleNamespace(id=int(str(preset_id).strip()))
        except ValueError:
            return None

    def preset_allowed(_cls: type, preset_id: int, _user: object, **_kwargs: bool) -> bool:
        assert isinstance(preset_id, int)
        return preset_id in {9, 10}

    monkeypatch.setattr(publish.ProductPreset, "find", classmethod(find_preset))
    monkeypatch.setattr(publish.ProductPreset, "allowed_with_acl", classmethod(preset_allowed))
    monkeypatch.setattr(publish.Product, "find", classmethod(lambda _cls, product_id: stored if product_id == 7 else None))
    monkeypatch.setattr(publish.ReportItem, "find", classmethod(lambda _cls, report_item_id: types.SimpleNamespace(id=report_item_id)))
    monkeypatch.setattr(publish.log_manager, "store_user_auth_error_activity", lambda *_args: None)
    return stored


def _load(stored_id: object, *ids: int, product_preset_id: object = 9) -> HTTPStatus:
    payload = {"id": -1, "stored_id": stored_id, "product_preset_id": product_preset_id, "report_items": [{"id": item} for item in ids]}
    return publish.load_product(payload, ANALYST, "token")[1]


def test_the_form_of_a_saved_product_may_check_the_reports_it_already_holds(saved_product: types.SimpleNamespace) -> None:
    """The language check sends the form unsaved; a colleague's unreadable report already in the product stays usable."""
    assert _load(7, 1, 2) == HTTPStatus.OK
    assert _load(7, 1, 2, 4) == HTTPStatus.FORBIDDEN  # one it does not hold yet
    assert _load(8, 1, 2) == HTTPStatus.FORBIDDEN  # no such saved product
    assert _load("7", 1, 2) == HTTPStatus.FORBIDDEN

    saved_product.product_preset_id = 11  # a product the user may not use exempts nothing
    assert _load(7, 1, 2, product_preset_id=11) == HTTPStatus.FORBIDDEN


@pytest.mark.usefixtures("saved_product")
@pytest.mark.parametrize("product_preset_id", [9, "9"])
def test_the_kept_reports_go_out_through_the_saved_product_s_own_preset(product_preset_id: object) -> None:
    assert _load(7, 1, 2, product_preset_id=product_preset_id) == HTTPStatus.OK


@pytest.mark.usefixtures("saved_product")
@pytest.mark.parametrize("product_preset_id", [10, "10", " 9", "9 ", "09", "+9"])
def test_the_kept_reports_do_not_go_out_through_another_preset(product_preset_id: object) -> None:
    """Preset 10 is one the user may use: naming product 7 must not render its report 2 with 10's templates or channels.

    An id written otherwise than as preset 9's own is not taken for it, even where it would find it.
    """
    assert _load(7, 1, 2, product_preset_id=product_preset_id) == HTTPStatus.FORBIDDEN
    # The reports the user may read are fine in any preset they may use.
    assert _load(7, 1, product_preset_id=product_preset_id) == HTTPStatus.OK


@pytest.mark.usefixtures("saved_product")
@pytest.mark.parametrize("product_preset_id", [None, "", "nine", 9.0, True, [9], {"id": 9}])
def test_a_missing_or_garbage_preset_exempts_nothing(product_preset_id: object) -> None:
    assert publish._kept_report_items(7, product_preset_id, ANALYST) == set()
    assert publish._kept_report_items(7, 9, ANALYST) == {1, 2}
    # Such a form never gets as far as rendering the report.
    assert _load(7, 1, 2, product_preset_id=product_preset_id) in {HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND}


def _update(monkeypatch: pytest.MonkeyPatch, original: types.SimpleNamespace, product_preset_id: int, *ids: int) -> None:
    monkeypatch.setattr(Product, "find", classmethod(lambda _cls, _id: original))
    submitted = types.SimpleNamespace(product_preset_id=product_preset_id, report_items=_items(*ids))
    monkeypatch.setattr(product_module, "NewProductSchema", lambda: types.SimpleNamespace(load=lambda _data: submitted))
    Product.update_product(7, {"product_preset_id": product_preset_id, "report_items": [{"id": item} for item in ids]}, ANALYST)


def test_an_update_may_keep_an_unreadable_report_but_not_add_one(monkeypatch: pytest.MonkeyPatch) -> None:
    original = types.SimpleNamespace(state_id=1, product_preset_id=9, report_items=_items(2))

    with pytest.raises(ValueError, match="report item\\(s\\) 4 "):
        _update(monkeypatch, original, 9, 2, 4)

    assert original.report_items == _items(2)


def test_an_update_keeps_an_unreadable_report_only_in_the_product_s_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Moved to another preset, the kept report would be rendered by its templates and sent to its channels."""
    original = types.SimpleNamespace(state_id=1, product_preset_id=9, report_items=_items(2))

    with pytest.raises(ValueError, match="report item\\(s\\) 2 "):
        _update(monkeypatch, original, 10, 1, 2)

    assert (original.product_preset_id, original.report_items) == (9, _items(2))


def test_a_refused_update_publishes_no_gcve_or_cve_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """GCVE and CVE publication reach outside Taranis: the report check comes before them."""
    for name in ("_apply_cvd_product_rules", "check_gcve_records_kept", "publish_gcve_records", "publish_cve_records"):
        monkeypatch.setattr(Product, name, staticmethod(lambda *_args, name=name: pytest.fail(f"{name} ran before the refusal")))
    original = types.SimpleNamespace(state_id=1, product_preset_id=9, report_items=_items(2))

    with pytest.raises(ValueError, match="report item\\(s\\) 4 "):
        _update(monkeypatch, original, 9, 2, 4)
