"""Core decides which products a public-web node may have, not only the node.

The node is internet-facing. Its API key used to fetch every web-enabled published product -
TLP:AMBER and TLP:RED ones, those without a TLP that the site hides, those of webs other nodes
serve - with the author's login name, because only the node applied the TLP rule and the web
it asked for was never checked against the node.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import public_web
from flask import Flask
from managers import template_preview
from model.attribute import AttributeType

APP = Flask(__name__)


def _attribute(title: str, value: str, attribute_type: AttributeType | None = None) -> types.SimpleNamespace:
    definition = types.SimpleNamespace(type=attribute_type) if attribute_type else None
    return types.SimpleNamespace(value=value, attribute_group_item=types.SimpleNamespace(title=title, attribute=definition))


def _product(product_id: int, *tlps: str, preset: int = 1, webs: tuple[int, ...] = (1, 2)) -> types.SimpleNamespace:
    attributes = [_attribute("TLP", tlp, AttributeType.TLP) for tlp in tlps]
    item = types.SimpleNamespace(attributes=[_attribute("Description", "text"), *attributes])
    return types.SimpleNamespace(
        id=product_id,
        title=f"Product {product_id}",
        created=None,
        product_preset_id=preset,
        report_items=[item],
        shown_on_web=lambda web_id: web_id in webs,
    )


@pytest.fixture
def templates(monkeypatch: pytest.MonkeyPatch) -> list:
    """The public-web templates core holds; none means the built-in ones (TLP:CLEAR required)."""
    stored: list = []
    monkeypatch.setattr(public_web, "_preset_templates", lambda _product_preset_id: list(stored))
    return stored


@pytest.mark.parametrize(
    ("tlps", "public"),
    [
        (("CLEAR",), True),
        (("WHITE", " clear "), True),
        (("GREEN",), False),
        (("CLEAR", "RED"), False),
        (("AMBER+STRICT",), False),
        (("TLP:CLEAR",), False),
        (("unclassified",), False),
    ],
)
def test_every_tlp_must_be_public(templates: list, tlps: tuple[str, ...], *, public: bool) -> None:  # noqa: ARG001
    assert public_web.public_on_web(_product(1, *tlps), 1) is public


def test_a_product_without_tlp_follows_its_preset_s_template_for_the_web(templates: list) -> None:
    product = _product(1)
    assert public_web.public_on_web(product, 1) is False  # built-in: TLP:CLEAR required

    templates.append(types.SimpleNamespace(public_web_ids=[], require_tlp_clear=False))
    assert public_web.public_on_web(product, 1) is True

    templates.append(types.SimpleNamespace(public_web_ids=[2], require_tlp_clear=True))
    assert public_web.public_on_web(product, 1) is True
    assert public_web.public_on_web(product, 2) is False


@pytest.mark.usefixtures("templates")
def test_a_gcve_advisory_without_tlp_is_public_but_its_tlps_still_count() -> None:
    advisory = _product(1)
    advisory.product_preset = types.SimpleNamespace(is_gcve=True)
    assert public_web.public_on_web(advisory, 1) is True  # no template of its own: the built-in would hide it

    other = _product(2)
    other.product_preset = types.SimpleNamespace(is_gcve=False)
    assert public_web.public_on_web(other, 1) is False

    restricted = _product(3, "RED")
    restricted.product_preset = types.SimpleNamespace(is_gcve=True)
    assert public_web.public_on_web(restricted, 1) is False


@pytest.fixture
def node() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        name="node",
        enabled=True,
        webs=[types.SimpleNamespace(id=1), types.SimpleNamespace(id=2)],
        touch=lambda: None,
    )


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, templates: list) -> list:  # noqa: ARG001
    products = [_product(3, "CLEAR"), _product(2, "AMBER"), _product(1, "CLEAR", webs=(2,))]
    monkeypatch.setattr(public_web.Product, "get_published", classmethod(lambda _cls, *_args, **_kwargs: (products, len(products))))
    monkeypatch.setattr(public_web, "_serialize_product", lambda product, _language=None: {"id": product.id, "report_items": ["..."]})

    def find_published(product_id: int, web_id: int | None = None) -> types.SimpleNamespace | None:
        found = next((product for product in products if product.id == product_id), None)
        return found if found and (web_id is None or found.shown_on_web(web_id)) else None

    monkeypatch.setattr(public_web, "_find_published", find_published)
    return products


def _list(node: types.SimpleNamespace, query: str) -> tuple:
    with APP.test_request_context(f"/?{query}"):
        return public_web.PublicWebProducts.get.__wrapped__(public_web.PublicWebProducts(), public_web_node=node)


def _get(node: types.SimpleNamespace, product_id: int, query: str = "") -> tuple:
    with APP.test_request_context(f"/?{query}"):
        return public_web.PublicWebProduct.get.__wrapped__(public_web.PublicWebProduct(), product_id, public_web_node=node)


def test_the_listing_withholds_what_the_web_may_not_show(node: types.SimpleNamespace, published: list) -> None:  # noqa: ARG001
    body, status = _list(node, "web_id=1&full=1")

    assert status == HTTPStatus.OK
    assert body["total_count"] == 3
    assert body["items"] == [
        {"id": 3, "report_items": ["..."]},
        {"id": 2, "withheld": True, "report_items": []},
        {"id": 1, "report_items": ["..."]},
    ]


def test_a_node_cannot_ask_for_a_web_it_does_not_serve(node: types.SimpleNamespace, published: list) -> None:  # noqa: ARG001
    assert _list(node, "web_id=9&full=1")[1] == HTTPStatus.NOT_FOUND
    assert _get(node, 3, "web_id=9")[1] == HTTPStatus.NOT_FOUND


def test_a_withheld_product_is_not_found(node: types.SimpleNamespace, published: list) -> None:  # noqa: ARG001
    assert _get(node, 3, "web_id=1")[1] == HTTPStatus.OK
    assert _get(node, 2, "web_id=1")[1] == HTTPStatus.NOT_FOUND


def test_without_a_web_only_the_node_s_own_webs_count(node: types.SimpleNamespace, published: list) -> None:
    node.webs = [types.SimpleNamespace(id=1)]

    assert _get(node, 3)[1] == HTTPStatus.OK
    # Shown on web 2 only, which another node serves.
    assert _get(node, 1)[1] == HTTPStatus.NOT_FOUND
    assert published


def test_a_template_preview_pass_lets_the_node_render_a_withheld_product(
    node: types.SimpleNamespace,
    published: list,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Signed by core, not kept in Redis, where a node could have written a pass of its own.
    monkeypatch.setattr(template_preview, "redis_client", None)

    ticket = template_preview.issue_product_pass(2, 1)

    assert _get(node, 2, f"web_id=1&preview_ticket={ticket}")[1] == HTTPStatus.OK
    assert _get(node, 2, f"web_id=2&preview_ticket={ticket}")[1] == HTTPStatus.NOT_FOUND
    assert _get(node, 2, "web_id=1&preview_ticket=forged")[1] == HTTPStatus.NOT_FOUND
