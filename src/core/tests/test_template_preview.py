"""Previewing a report template before it is saved: core checks it, picks the web and product, asks the node."""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from api import config as config_api
from app import _install_security_headers
from flask import Flask
from flask_restful import Api
from managers import template_preview

if TYPE_CHECKING:
    from flask.testing import FlaskClient

SOURCE = '{% extends "builtin/product_base.html" %}'


class _FakeRedis:
    """The few commands the page tickets use."""

    def __init__(self) -> None:
        self.values: dict[str, str | int] = {}
        self.ttl: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int) -> None:
        self.values[key], self.ttl[key] = value, ex

    def get(self, key: str) -> str | int | None:
        return self.values.get(key)

    def incr(self, key: str) -> int:
        views = int(self.values.get(key, 0)) + 1
        self.values[key] = views
        return views

    def expire(self, key: str, seconds: int) -> None:
        self.ttl[key] = seconds

    def delete(self, *keys: str) -> None:
        for key in keys:
            self.values.pop(key, None)


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(template_preview, "redis_client", fake)
    return fake


def _web(
    web_id: int,
    *,
    enabled: bool = True,
    node_enabled: bool = True,
    api_url: str = "http://node",
    languages: list | None = None,
) -> object:
    node = types.SimpleNamespace(name=f"node {web_id}", enabled=node_enabled, api_url=api_url, api_key="k")
    config = {"languages": languages or ["en", "cs"], "default_language": "en"}
    return types.SimpleNamespace(id=web_id, name=f"Web {web_id}", enabled=enabled, node=node, config=config)


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, redis: _FakeRedis) -> types.SimpleNamespace:
    state = types.SimpleNamespace(
        webs=[_web(1, node_enabled=False), _web(2), _web(3)],
        products=[types.SimpleNamespace(id=42, title="Newest", created=None), types.SimpleNamespace(id=41, title="Older", created=None)],
        sent=[],
        answer=({"view": "detail", "html": "<html></html>", "errors": [], "warnings": []}, HTTPStatus.OK),
        listed=[],
        redis=redis,
    )
    monkeypatch.setattr(template_preview, "_all_webs", lambda: list(state.webs))
    monkeypatch.setattr(
        template_preview.db,
        "session",
        types.SimpleNamespace(get=lambda _model, web_id: next((web for web in state.webs if web.id == web_id), None)),
    )

    def published(_limit: int, **filters: object) -> tuple[list, int]:
        state.listed.append(filters)
        return list(state.products), len(state.products)

    monkeypatch.setattr(template_preview.Product, "get_published", staticmethod(published))

    class FakeApi:
        def __init__(self, api_url: str, api_key: str) -> None:
            self.api_url, self.api_key = api_url, api_key

        def preview(self, payload: dict) -> tuple[dict, HTTPStatus]:
            state.sent.append(payload)
            return state.answer

    monkeypatch.setattr(template_preview, "PublicWebApi", FakeApi)
    return state


def test_an_invalid_template_is_refused_before_any_node_is_asked(world: types.SimpleNamespace) -> None:
    body, status = template_preview.preview({"template": {"product_preset_id": 5, "source": "{% if %}"}})

    assert status == HTTPStatus.BAD_REQUEST
    assert body["invalid"] is True
    assert "line 1" in body["error"]
    assert world.sent == []


def test_a_template_must_say_what_it_is_for(world: types.SimpleNamespace) -> None:
    _body, status = template_preview.preview({"template": {"source": SOURCE}})

    assert status == HTTPStatus.BAD_REQUEST
    assert world.sent == []


def test_the_newest_product_of_the_target_on_the_first_web_that_can_preview(world: types.SimpleNamespace) -> None:
    body, status = template_preview.preview({"template": {"product_preset_id": 5, "source": SOURCE}, "view": "rss"})

    assert status == HTTPStatus.OK
    # Web 1's node is switched off: web 2 renders it.
    (sent,) = world.sent
    assert (sent["web_id"], sent["product_id"], sent["view"]) == (2, 42, "rss")
    assert sent["template"] == {"product_preset_id": 5, "report_item_type_id": None, "source": SOURCE, "require_tlp_clear": True}
    assert world.listed == [{"web_id": 2, "product_preset_id": 5, "report_item_type_id": None}]
    assert (body["web_id"], body["product_id"]) == (2, 42)


def test_the_page_comes_back_as_a_url_of_its_own(world: types.SimpleNamespace) -> None:
    # Inline (srcdoc) it took the GUI's policy, which blocks the web's stylesheets.
    body, status = template_preview.preview({"template": {"product_preset_id": 5, "source": SOURCE}})

    assert status == HTTPStatus.OK
    assert "html" not in body
    prefix = "/config/public-web-templates/preview/"
    assert body["page_url"].startswith(prefix)
    assert template_preview.take_page(body["page_url"].removeprefix(prefix)) == "<html></html>"
    assert set(world.redis.ttl.values()) == {template_preview.PAGE_TTL_SECONDS}


def test_a_page_has_a_few_views_then_it_is_gone(redis: _FakeRedis) -> None:
    token = template_preview.store_page("<p>page</p>")

    seen = [template_preview.take_page(token) for _ in range(template_preview.PAGE_MAX_VIEWS)]

    assert seen == ["<p>page</p>"] * template_preview.PAGE_MAX_VIEWS
    assert template_preview.take_page(token) is None
    assert template_preview.take_page(token) is None
    assert template_preview.take_page("not-a-ticket") is None
    assert redis.values == {}


@pytest.fixture
def page_client() -> FlaskClient:
    """The page route as core serves it: its resource under core's header hook."""
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(config_api.PublicWebTemplatePreviewPage, "/api/v1/config/public-web-templates/preview/<string:token>")
    _install_security_headers(app)
    return app.test_client()


@pytest.mark.usefixtures("redis")
def test_the_page_lets_the_web_s_styles_load_and_only_the_gui_frame_it(page_client: FlaskClient) -> None:
    token = template_preview.store_page("<html><body>page</body></html>")

    response = page_client.get(f"/api/v1/config/public-web-templates/preview/{token}")

    assert response.status_code == HTTPStatus.OK
    assert response.mimetype == "text/html"
    assert response.get_data(as_text=True) == "<html><body>page</body></html>"
    csp = response.headers["Content-Security-Policy"]
    assert "style-src 'unsafe-inline' https://cdn.jsdelivr.net" in csp
    assert "font-src data: https://cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'self'" in csp
    assert "script-src" not in csp  # default-src 'none': no script runs
    assert "X-Frame-Options" not in response.headers  # frame-ancestors decides
    # The GUI's COEP lets in only a frame that declares one too; the sandboxed frame has an
    # opaque origin, which Firefox holds against "same-origin".
    assert response.headers["Cross-Origin-Embedder-Policy"] == "require-corp"
    assert response.headers["Cross-Origin-Resource-Policy"] == "cross-origin"
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.usefixtures("redis")
def test_a_gone_page_says_so(page_client: FlaskClient) -> None:
    response = page_client.get("/api/v1/config/public-web-templates/preview/unknown")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "render it again" in response.get_data(as_text=True)
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_the_template_s_own_web_comes_first(world: types.SimpleNamespace) -> None:
    template_preview.preview({"template": {"report_item_type_id": 7, "source": "<p></p>", "public_web_ids": [3]}, "product_id": 41})

    assert (world.sent[0]["web_id"], world.sent[0]["product_id"]) == (3, 41)


def test_no_preview_without_a_node_to_render_it(world: types.SimpleNamespace) -> None:
    body, status = template_preview.preview({"template": {"product_preset_id": 5, "source": SOURCE}, "web_id": 1})

    assert status == HTTPStatus.CONFLICT
    assert "switched off" in body["error"]
    assert world.sent == []


def test_no_product_to_show(world: types.SimpleNamespace) -> None:
    world.products = []

    body, status = template_preview.preview({"template": {"product_preset_id": 5, "source": SOURCE}})

    assert status == HTTPStatus.NOT_FOUND
    assert "No published product" in body["error"]


def test_a_node_that_cannot_be_reached(world: types.SimpleNamespace) -> None:
    world.answer = ({"error": "Connection refused"}, HTTPStatus.SERVICE_UNAVAILABLE)

    body, status = template_preview.preview({"template": {"product_preset_id": 5, "source": SOURCE}})

    assert status == HTTPStatus.BAD_GATEWAY
    assert "could not be reached" in body["error"]


@pytest.mark.usefixtures("world")
def test_the_options_list_every_web_and_the_products_for_the_chosen_one() -> None:
    offered = template_preview.options(None, 7, None, [3])

    assert [(web["id"], web["unavailable"]) for web in offered["webs"]] == [(1, "Its public-web node is switched off"), (2, None), (3, None)]
    assert offered["web_id"] == 3
    assert [product["id"] for product in offered["products"]] == [42, 41]
    assert offered["webs"][1]["languages"] == ["en", "cs"]
