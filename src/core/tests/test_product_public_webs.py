"""A product can be left out of some of its product preset's webs.

The product preset says which webs its products appear on (its own, else every web); the edit
form offers those as ``web_choices``. A product stores the ones it is limited to, none meaning
every one, and an edit that leaves them out keeps them.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model import product as product_model  # noqa: E402 - after every mapper is registered
from model import product_preset as product_preset_model  # noqa: E402
from model.product_preset import ProductPreset  # noqa: E402
from model.public_web import PublicWeb  # noqa: E402

WEBS = {1: "Cyberfeed", 3: "Archive"}


def _web(web_id: int) -> PublicWeb:
    web = PublicWeb(node_id=1, name=WEBS[web_id])
    web.id = web_id
    return web


@pytest.fixture(autouse=True)
def _webs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(PublicWeb, "find", classmethod(lambda _cls, web_id: _web(web_id) if web_id in WEBS else None))


def _loaded(**fields: object) -> product_model.Product:
    payload = {"id": -1, "title": "Bulletin", "description": "", "product_preset_id": 2, "state_id": None, "report_items": []}
    return product_model.NewProductSchema().load({**payload, **fields})


def test_a_product_stores_the_webs_it_is_limited_to() -> None:
    product = _loaded(public_web_ids=[3, 3, 9])

    assert product.public_web_ids == [3]
    assert product.public_webs_given is True


def test_an_edit_without_webs_keeps_the_stored_ones() -> None:
    assert _loaded().public_webs_given is False
    assert _loaded(public_web_ids=[]).public_webs_given is True


def test_a_product_can_be_kept_off_the_public_web() -> None:
    kept_off = _loaded(public_web_enabled=False)

    assert (kept_off.public_web_enabled, kept_off.public_web_enabled_given) == (False, True)
    assert product_model.ProductPresentationSchema().dump(kept_off)["public_web_enabled"] is False
    # A new product is on it; an edit that does not say keeps what is stored.
    assert (_loaded().public_web_enabled, _loaded().public_web_enabled_given) == (True, False)


def test_the_list_shows_which_webs_a_product_is_limited_to() -> None:
    product = _loaded(public_web_ids=[3, 1])

    assert product_model.ProductPresentationSchema().dump(product)["public_web_ids"] == [1, 3]


def test_a_product_preset_offers_its_own_webs_else_every_web(monkeypatch: pytest.MonkeyPatch) -> None:
    every_web = SimpleNamespace(query=SimpleNamespace(all=lambda: [_web(1), _web(3)]))
    monkeypatch.setattr(product_preset_model, "PublicWeb", every_web)
    product_preset = ProductPreset("Advisory", public_web_enabled=True)

    assert product_preset.web_choices == [{"id": 3, "name": "Archive"}, {"id": 1, "name": "Cyberfeed"}]
    product_preset.public_webs = [_web(1)]
    assert product_preset.web_choices == [{"id": 1, "name": "Cyberfeed"}]
    product_preset.public_web_enabled = False
    assert product_preset.web_choices == []
