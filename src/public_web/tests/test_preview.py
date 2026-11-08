"""Previewing a report template that is not saved yet (``POST /management/preview``).

Core forwards the template dialog's state; the node renders a published product with it, inside
the web's own page, and says what went wrong in the template instead of only logging it.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import SimpleNamespace


def _auth() -> dict[str, str]:
    """Core's request header: the node's key, whichever an earlier test configured."""
    from lib import config  # noqa: PLC0415 (after conftest set the environment)

    return {"Authorization": f"ApiKey {config.taranis_api_key()}"}


BASE_PRODUCT_TEMPLATE = '{% extends "builtin/product_base.html" %}{% block header %}<p id="mine">{{ product.title }}</p>{% endblock %}'


def _preview(site_client: SimpleNamespace, **payload: object) -> tuple[dict, int]:
    body = {"web_id": 1, "product_id": 101, "language": "en", "view": "detail", **payload}
    body.setdefault("template", {"product_preset_id": 10, "source": BASE_PRODUCT_TEMPLATE, "require_tlp_clear": True})
    response = site_client.client.post("/management/preview", json=body, headers=_auth())
    return response.get_json(), response.status_code


def test_the_report_page_renders_with_the_unsaved_template(site_client: SimpleNamespace) -> None:
    body, status = _preview(site_client)

    assert status == HTTPStatus.OK
    assert body["errors"] == []
    assert '<p id="mine">' in body["html"]
    # Inside the web's own page, with its styles and links resolving against the web.
    assert '<base href="https://localhost/"' in body["html"]
    assert "</html>" in body["html"]


def test_the_page_brings_its_own_styles_and_images(site_client: SimpleNamespace) -> None:
    # The GUI's browser may not reach the web's hostname: the page must not need it to look right.
    body, _status = _preview(site_client)

    assert "/static/styles.css" not in body["html"]
    assert "<script" not in body["html"]
    assert "onfocus=" not in body["html"]
    assert "<style>" in body["html"]
    assert 'href="data:image/' in body["html"]  # the favicon


def test_scripts_and_event_handlers_are_left_out() -> None:
    from lib.web.preview import _without_scripts  # noqa: PLC0415 (after conftest set the environment)

    page = '<p onclick="a()" class="x" ONMOUSEOVER=\'b()\'>on="kept" text</p><script src="s.js"></script><SCRIPT>\nc()\n</SCRIPT>'

    assert _without_scripts(page) == '<p class="x">on="kept" text</p>'


def test_the_stored_templates_stay_as_they_are(site_client: SimpleNamespace) -> None:
    before = site_client.client.get("/reports/101", headers={"Host": "localhost"}).get_data(as_text=True)

    _preview(site_client)

    after = site_client.client.get("/reports/101", headers={"Host": "localhost"}).get_data(as_text=True)
    assert 'id="mine"' not in after
    assert before == after


def test_a_failing_template_is_reported_with_its_line_and_replaced_by_the_built_in(site_client: SimpleNamespace) -> None:
    broken = '{% extends "builtin/product_base.html" %}\n{% block header %}\n{{ product.title.upper(1, 2, 3) }}\n{% endblock %}'

    body, status = _preview(site_client, template={"product_preset_id": 10, "source": broken})

    assert status == HTTPStatus.OK
    (error,) = body["errors"]
    assert (error["template"], error["line"]) == ("product/10", 3)
    assert "TypeError" in error["message"]
    assert body["html"]  # the built-in page instead


def test_an_item_template_is_previewed_in_the_items_of_the_product(site_client: SimpleNamespace) -> None:
    body, status = _preview(site_client, template={"report_item_type_id": 2, "source": '<div class="item-preview">{{ item.name }}</div>'})

    assert status == HTTPStatus.OK
    assert body["html"].count('class="item-preview"') == 2


def test_the_homepage_entry_renders_on_the_homepage(site_client: SimpleNamespace) -> None:
    body, status = _preview(site_client, view="summary")

    assert status == HTTPStatus.OK
    assert "Critical" in body["html"]


def test_the_whole_feed_item(site_client: SimpleNamespace) -> None:
    body, status = _preview(site_client, view="rss")

    assert status == HTTPStatus.OK
    assert body["rss"]["title"].startswith("Critical")
    assert body["rss"]["link"].startswith("https://localhost/reports/101")
    assert body["rss"]["description"]
    assert body["xml"].startswith("<item>")
    assert "<title>" in body["xml"]


def test_a_product_the_web_would_not_show_is_previewed_with_a_warning(site_client: SimpleNamespace) -> None:
    # Amber: never on a public web.
    body, status = _preview(site_client, product_id=103)

    assert status == HTTPStatus.OK
    assert any("would not show" in warning for warning in body["warnings"])


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"web_id": 99}, HTTPStatus.NOT_FOUND),
        ({"product_id": 999}, HTTPStatus.NOT_FOUND),
        ({"template": {"source": "x"}}, HTTPStatus.BAD_REQUEST),
        ({"web_id": "x"}, HTTPStatus.BAD_REQUEST),
    ],
)
def test_what_cannot_be_previewed(site_client: SimpleNamespace, payload: dict, status: int) -> None:
    body, answered = _preview(site_client, **payload)

    assert answered == status
    assert body["error"]


def test_only_core_may_ask(site_client: SimpleNamespace) -> None:
    response = site_client.client.post("/management/preview", json={})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
