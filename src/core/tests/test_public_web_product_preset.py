"""A public-web node sees a published product only where its product preset puts it.

The product preset decides whether its products appear on the public web at all, and on which
webs (none listed: every web). A product can be limited to some of those (none: every one).
"""

from __future__ import annotations

import types

import pytest
from api import public_web
from model.product import Product
from model.product_preset import ProductPreset
from model.public_web import PublicWeb

PUBLISHED = 4


def _web(web_id: int) -> PublicWeb:
    web = PublicWeb(node_id=1, name=f"web {web_id}")
    web.id = web_id
    return web


def _product_preset(*, enabled: bool, targets: list[int]) -> ProductPreset:
    product_preset = ProductPreset("Advisory", public_web_enabled=enabled)
    product_preset.public_webs = [_web(web_id) for web_id in targets]
    return product_preset


def _product(state_id: int, product_preset: ProductPreset, own: tuple[int, ...] = (), *, on_web: bool = True) -> types.SimpleNamespace:
    product = types.SimpleNamespace(state_id=state_id, product_preset=product_preset, public_web_ids=list(own), public_web_enabled=on_web)
    product.shown_on_web = types.MethodType(Product.shown_on_web, product)
    return product


@pytest.fixture
def find(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Look a product up through the endpoint helper, with the product and states stubbed."""

    def _find(product: object | None, web_id: int | None) -> object | None:
        monkeypatch.setattr(public_web.Product, "find", classmethod(lambda _cls, _id: product))
        monkeypatch.setattr(
            public_web.StateDefinition,
            "get_by_name",
            classmethod(lambda _cls, _name: types.SimpleNamespace(id=PUBLISHED)),
        )
        return public_web._find_published(7, web_id)

    return _find


@pytest.mark.parametrize(
    ("enabled", "targets", "web_id", "visible"),
    [
        (True, [], 1, True),
        (True, [], None, True),
        (True, [1], 1, True),
        (True, [1], 3, False),
        (False, [], 1, False),
        (False, [], None, False),
    ],
)
def test_the_product_preset_decides_the_webs(find, enabled: bool, targets: list[int], web_id: int | None, visible: bool) -> None:  # noqa: ANN001
    product = _product(PUBLISHED, _product_preset(enabled=enabled, targets=targets))

    assert (find(product, web_id) is product) is visible


@pytest.mark.parametrize(
    ("targets", "own", "web_id", "visible"),
    [
        ([], [3], 3, True),
        ([], [3], 1, False),
        ([1, 3], [3], 3, True),
        ([1, 3], [3], 1, False),
        # Limited to a web its product preset no longer shows: on none.
        ([1], [3], 3, False),
        ([1], [3], 1, False),
        ([], [3], None, True),
    ],
)
def test_a_product_can_be_left_out_of_some_webs(find, targets: list[int], own: list[int], web_id: int | None, visible: bool) -> None:  # noqa: ANN001
    product = _product(PUBLISHED, _product_preset(enabled=True, targets=targets), tuple(own))

    assert (find(product, web_id) is product) is visible


@pytest.mark.parametrize("web_id", [1, 3, None])
def test_a_product_kept_off_the_public_web_is_on_no_web(find, web_id: int | None) -> None:  # noqa: ANN001
    product = _product(PUBLISHED, _product_preset(enabled=True, targets=[]), on_web=False)

    assert find(product, web_id) is None


def test_an_unpublished_product_stays_hidden(find) -> None:  # noqa: ANN001
    product = _product(PUBLISHED + 1, _product_preset(enabled=True, targets=[]))

    assert find(product, 1) is None
    assert find(None, 1) is None
