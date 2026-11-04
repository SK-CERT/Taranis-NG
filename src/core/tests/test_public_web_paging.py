"""A public-web node can load every published product, a page at a time.

The list endpoint says how many products are published in all and, with ``full``, serves each
product of the page whole, so a node needs a few requests instead of one per product.
"""

from __future__ import annotations

import types

import pytest
from api import public_web
from flask import Flask

NODE = types.SimpleNamespace(name="node", touch=lambda: None)


@pytest.fixture
def listed(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Call the list endpoint with a query string; returns its body and what it asked the model for."""
    asked: dict = {}
    products = [types.SimpleNamespace(id=product_id, title=f"Bulletin {product_id}", created=None) for product_id in (9, 8)]

    def get_published(_cls: type, limit: int, web_id: int | None = None, offset: int = 0, with_content: bool = False) -> tuple[list, int]:
        asked.update(limit=limit, web_id=web_id, offset=offset, with_content=with_content)
        return products, 812

    monkeypatch.setattr(public_web.Product, "get_published", classmethod(get_published))
    monkeypatch.setattr(public_web, "_serialize_product", lambda product, language: {"id": product.id, "language": language})

    def _listed(query: str) -> tuple[dict, dict]:
        with Flask(__name__).test_request_context(f"/api/v1/public-web/products{query}"):
            body, _status = public_web.PublicWebProducts.get.__wrapped__(public_web.PublicWebProducts(), public_web_node=NODE)
        return body, asked

    return _listed


def test_a_page_says_how_many_products_are_published_in_all(listed) -> None:  # noqa: ANN001
    body, asked = listed("?limit=2&offset=40&web_id=1")

    assert body == {
        "total_count": 812,
        "items": [{"id": 9, "title": "Bulletin 9", "created": None}, {"id": 8, "title": "Bulletin 8", "created": None}],
    }
    assert asked == {"limit": 2, "web_id": 1, "offset": 40, "with_content": False}


def test_full_serves_each_product_whole_in_the_language_asked_for(listed) -> None:  # noqa: ANN001
    body, asked = listed("?limit=100&offset=100&web_id=1&full=1&lang=cs")

    assert body["items"] == [{"id": 9, "language": "cs"}, {"id": 8, "language": "cs"}]
    assert asked["with_content"] is True


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", {"limit": 50, "offset": 0}),
        ("?limit=1000&offset=-5", {"limit": 200, "offset": 0}),
        ("?limit=x&offset=y", {"limit": 50, "offset": 0}),
    ],
)
def test_a_page_is_bounded(listed, query: str, expected: dict) -> None:  # noqa: ANN001
    _body, asked = listed(query)

    assert {key: asked[key] for key in expected} == expected


def test_a_language_that_is_not_one_shows_the_products_as_written(listed) -> None:  # noqa: ANN001
    body, _asked = listed("?full=true&lang=../x")

    assert {item["language"] for item in body["items"]} == {None}
