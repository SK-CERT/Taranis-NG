"""Presenters get the format a product is rendered in as ``product_format``.

Product types were renamed product formats. Presenter nodes are upgraded before core, so a node
still has to read the format from the keys an older core sends.
"""

from __future__ import annotations

from shared.schema.presenter import PresenterInputProductSchema

PRODUCT = {"title": "Bulletin", "description": "", "user": {"username": "analyst", "name": "Analyst"}, "id": "7"}


def test_the_format_is_read_from_its_keys() -> None:
    product = PresenterInputProductSchema().load({**PRODUCT, "product_format": "PDF", "product_format_description": "Printable"})
    assert (product.product_format, product.product_format_description) == ("PDF", "Printable")


def test_an_older_core_sends_the_format_as_a_product_type() -> None:
    product = PresenterInputProductSchema().load({**PRODUCT, "product_type": "PDF", "product_type_description": "Printable"})
    assert (product.product_format, product.product_format_description) == ("PDF", "Printable")
    assert not hasattr(product, "product_type")
