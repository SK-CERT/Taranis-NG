"""Preview a public-web report template before it is saved.

The template is rendered by a public-web node, the same code that serves the webs, so the preview
shows exactly what a web would: the product inside the web's own page, with its branding and
language. Core checks the source first (a syntax error needs no node), picks the web and the
product, and forwards the request to the web's node.

A built-in template (read-only) is previewed too: the node renders the product with the
built-ins alone, every one of them on, so the product shows what that built-in makes of it.

Nothing works without a node that can be reached: the web's node must be switched on and have
an API URL.
"""

from __future__ import annotations

import functools
import json
import uuid
from http import HTTPStatus

from managers.cache_manager import redis_client
from managers.db_manager import db
from model.product import Product
from model.public_web import PublicWeb
from model.public_web_template import TemplateValidationError, validate_source
from model.report_item_type import ReportItemType
from remote.public_web_api import PublicWebApi
from shared.public_web_templates import VULNERABILITY_TYPE, builtin_sources

from shared import public_web_script

PRODUCTS_LISTED = 50
VIEWS = ("detail", "summary", "rss")
BUILTINS = frozenset(builtin_sources())

# Which report item types a built-in shows, rendered with the built-ins alone: the vulnerability
# item template the "Vulnerability Report" type, the generic one any other, the vulnerability
# product layout a product holding a vulnerability report. The others (the base layout, the
# macros) show in every product.
_BUILTIN_TYPES = {
    "builtin/item_vulnerability.html": lambda title: title == VULNERABILITY_TYPE,
    "builtin/item_generic.html": lambda title: title != VULNERABILITY_TYPE,
    "builtin/product_vulnerability.html": lambda title: title.startswith(VULNERABILITY_TYPE),
}

# A rendered page is kept briefly under a random ticket and served from its own URL, with a
# Content-Security-Policy made for it: shown inline (srcdoc) it took the GUI's policy, which
# does not let the web's stylesheets and fonts load from the CDN the public web uses. The only
# script it runs is the web's page script (colour mode, language menu), allowed by its hash
# (shared.public_web_script).
PAGE_TTL_SECONDS = 600
PAGE_MAX_VIEWS = 5
PAGE_URL = "/config/public-web-templates/preview/{token}"
PAGE_HEADERS = {
    "Content-Security-Policy": (
        f"default-src 'none'; script-src {public_web_script.SCRIPT_HASH}; "
        "style-src 'unsafe-inline' https://cdn.jsdelivr.net; font-src data: https://cdn.jsdelivr.net; "
        "img-src data: https:; base-uri https: http:; form-action 'none'; frame-ancestors 'self'"
    ),
    # The GUI embeds it under its own COEP, which a framed document must also declare. Its frame
    # is sandboxed, so the page loads into an opaque origin: Firefox blocks it as cross-origin
    # under "same-origin". Who may frame it is frame-ancestors' to say (X-Frame-Options is left
    # out: browsers ignore it beside frame-ancestors, and Firefox says so in the console).
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "cross-origin",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def _page_key(token: str) -> str:
    return f"template-preview:{token}"


def store_page(html: str) -> str:
    """Keep a rendered page for a while; returns its ticket."""
    token = str(uuid.uuid4())
    redis_client.set(_page_key(token), json.dumps({"html": html}), ex=PAGE_TTL_SECONDS)
    return token


def take_page(token: str) -> str | None:
    """The page of a ticket, while it lasts and has views left (the frame, a reload, a new tab)."""
    key = _page_key(token)
    cached = redis_client.get(key)
    if not cached:
        return None
    views = redis_client.incr(f"{key}:views")
    if views == 1:
        redis_client.expire(f"{key}:views", PAGE_TTL_SECONDS)
    if views > PAGE_MAX_VIEWS:
        redis_client.delete(key, f"{key}:views")
        return None
    return json.loads(cached)["html"]


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _unavailable(web: PublicWeb) -> str | None:
    """Why a web cannot preview (its node switched off, or with no API URL); None when it can."""
    if not web.enabled:
        return "The web is switched off"
    if web.node is None or not web.node.enabled:
        return "Its public-web node is switched off"
    if not web.node.api_url:
        return "Its public-web node has no API URL"
    return None


def _web_entry(web: PublicWeb) -> dict:
    config = web.config or {}
    languages = config.get("languages") if isinstance(config.get("languages"), list) else []
    default = config.get("default_language") or (languages[0] if languages else None)
    return {
        "id": web.id,
        "name": web.name or str(web.id),
        "node": web.node.name if web.node is not None else "",
        "unavailable": _unavailable(web),
        "languages": languages or ([default] if default else []),
        "default_language": default,
    }


def _all_webs() -> list[PublicWeb]:
    return PublicWeb.query.order_by(db.asc(PublicWeb.name), db.asc(PublicWeb.id)).all()


def _choose_web(web_id: int | None, preferred: list[int]) -> PublicWeb | None:
    """The web asked for; else the first of ``preferred`` (the template's webs) that can preview; else any."""
    if web_id is not None:
        return db.session.get(PublicWeb, web_id)
    webs = _all_webs()
    ordered = [web for web in webs if web.id in preferred] + [web for web in webs if web.id not in preferred]
    return next((web for web in ordered if _unavailable(web) is None), ordered[0] if ordered else None)


def _target(template: dict) -> tuple[int | None, int | None]:
    return _int_or_none(template.get("product_preset_id")), _int_or_none(template.get("report_item_type_id"))


def _products(web: PublicWeb, product_preset_id: int | None, report_item_type_id: int | None) -> list[Product]:
    """The published products the template applies to that the web shows, newest first."""
    products, _total = Product.get_published(
        PRODUCTS_LISTED,
        web_id=web.id,
        product_preset_id=product_preset_id,
        report_item_type_id=report_item_type_id,
    )
    return products


def _type_titles() -> list[tuple[int, str]]:
    return [(type_id, title or "") for type_id, title in db.session.query(ReportItemType.id, ReportItemType.title).all()]


def _builtin_products(web: PublicWeb, builtin: str) -> list[Product]:
    """The published products the web shows that show the built-in (see ``_BUILTIN_TYPES``), newest first."""
    matches = _BUILTIN_TYPES.get(builtin)
    type_ids = None if matches is None else [type_id for type_id, title in _type_titles() if matches(title)]
    products, _total = Product.get_published(PRODUCTS_LISTED, web_id=web.id, report_item_type_ids=type_ids)
    return products


def options(
    product_preset_id: int | None,
    report_item_type_id: int | None,
    web_id: int | None,
    preferred: list[int],
    builtin: str | None = None,
) -> dict:
    """What the preview can show: every web (and whether it can preview), and the products for the chosen one.

    The products are those the template applies to, or with ``builtin``, those that show that built-in.

    Returns:
        dict: ``{"webs": [...], "web_id": int | None, "products": [{"id", "title", "created"}]}``.
    """
    webs = _all_webs()
    web = _choose_web(web_id, preferred)
    if web is None or (builtin is not None and builtin not in BUILTINS):
        products = []
    elif builtin is not None:
        products = _builtin_products(web, builtin)
    else:
        products = _products(web, product_preset_id, report_item_type_id)
    return {
        "webs": [_web_entry(entry) for entry in webs],
        "web_id": web.id if web is not None else None,
        "products": [
            {"id": product.id, "title": product.title, "created": product.created.isoformat() if product.created else None}
            for product in products
        ],
    }


def preview(data: dict) -> tuple[dict, HTTPStatus]:
    """Render the template of the dialog, or a built-in one, through the web's node.

    Args:
        data: ``{"template": {"product_preset_id" | "report_item_type_id", "source",
            "require_tlp_clear", "public_web_ids"}, "web_id", "language", "product_id", "view"}``,
            or ``{"builtin": "builtin/<file>", ...}`` for a built-in; without a product, the
            newest one the template applies to (the built-in shows in).

    Returns:
        (dict, HTTPStatus): The node's answer (see public_web/lib/web/preview.py) with the web and
            product shown, or why there is nothing to show.
    """
    builtin = data.get("builtin")
    if builtin is not None:
        if builtin not in BUILTINS:
            return {"error": "There is no such built-in template"}, HTTPStatus.BAD_REQUEST
        rendered: dict = {"builtin": builtin}
        preferred: list[int] = []
        listing = functools.partial(_builtin_products, builtin=builtin)
    else:
        template = data.get("template") if isinstance(data.get("template"), dict) else {}
        product_preset_id, report_item_type_id = _target(template)
        if (product_preset_id is None) == (report_item_type_id is None):
            return {"error": "Choose what the template is for"}, HTTPStatus.BAD_REQUEST
        source = template.get("source") if isinstance(template.get("source"), str) else ""
        try:
            validate_source(source, product_template=product_preset_id is not None)
        except TemplateValidationError as error:
            return {"error": str(error), "invalid": True}, HTTPStatus.BAD_REQUEST
        rendered = {
            "template": {
                "product_preset_id": product_preset_id,
                "report_item_type_id": report_item_type_id,
                "source": source,
                "require_tlp_clear": bool(template.get("require_tlp_clear", True)),
            },
        }
        preferred = [web_id for web_id in (_int_or_none(value) for value in template.get("public_web_ids") or []) if web_id is not None]
        listing = functools.partial(_products, product_preset_id=product_preset_id, report_item_type_id=report_item_type_id)

    web = _choose_web(_int_or_none(data.get("web_id")), preferred)
    if web is None:
        return {"error": "There is no public web to preview on"}, HTTPStatus.NOT_FOUND
    reason = _unavailable(web)
    if reason:
        return {"error": f"{reason}: no preview without a public-web node to render it"}, HTTPStatus.CONFLICT

    product_id = _int_or_none(data.get("product_id"))
    if product_id is None:
        products = listing(web)
        if not products:
            return {"error": "No published product on this web that the template applies to"}, HTTPStatus.NOT_FOUND
        product_id = products[0].id

    view = data.get("view") if data.get("view") in VIEWS else "detail"
    payload = {
        **rendered,
        "web_id": web.id,
        "product_id": product_id,
        "language": data.get("language") if isinstance(data.get("language"), str) else None,
        "view": view,
    }
    body, status = PublicWebApi(web.node.api_url, web.node.api_key).preview(payload)
    if status == HTTPStatus.SERVICE_UNAVAILABLE:
        return {"error": f"The public-web node could not be reached: {body.get('error', '')}"}, HTTPStatus.BAD_GATEWAY
    if not isinstance(body, dict):
        body = {"error": "The public-web node gave no preview"}
    if status == HTTPStatus.OK and isinstance(body.get("html"), str):
        # Served from its own URL with its own policy (see PAGE_HEADERS), not inline.
        page = body.pop("html")
        body["page_url"] = PAGE_URL.format(token=store_page(page))
    return {**body, "web_id": web.id, "product_id": product_id}, status
