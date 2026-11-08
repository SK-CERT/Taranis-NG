"""Preview a report template that is not saved yet: how a published product looks with it.

Core forwards the template dialog's state here (``POST /management/preview``): the template
(its target, source and TLP rule), a product, a web and a language, and which part to show:

* ``detail`` - the report page, inside the web's own page (branding, navigation, feedback);
* ``summary`` - the product's homepage entry, on the web's homepage;
* ``rss`` - the product's whole feed item: title, link and description, and the item's XML.

The product is fetched from core as for the site (core decides whether the web may show it),
and rendered by a renderer built for this one request: the web's stored templates with the
previewed one in place of the stored template of its target, and the built-ins switched off as
stored. Nothing is cached and nothing shared changes.

A custom template that fails is replaced by its built-in fallback, as on the site, and the
failure is reported (template, line, message) instead of only logged. Reasons the product would
not be shown on the web (no template for its items, its TLP, ...) come back as warnings.
"""

from __future__ import annotations

import base64
import mimetypes
import re
import traceback
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

from feedgen.feed import FeedGenerator
from flask import current_app, g, render_template, url_for
from jinja2 import TemplateSyntaxError
from lib.report.product import InvalidProductError, build_product, displayable, remove_link_references
from lib.report.renderer import ReportRenderer, templates_for_web
from lib.web import translate
from lib.web.site import SiteContext

if TYPE_CHECKING:
    from lib.web.cache import WebCache

VIEWS = ("detail", "summary", "rss")
_HEAD = re.compile(r"<head(\s[^>]*)?>", re.IGNORECASE)
_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
# An event handler attribute in a tag (onfocus="..."): script too.
_HANDLER = re.compile(r"""(<[a-zA-Z][^>]*?)\s+on[a-z]+\s*=\s*(?:"[^"]*"|'[^']*')""", re.IGNORECASE)


def _without_scripts(page: str) -> str:
    """The page without its scripts and event handlers.

    The preview runs none (the theme switch, Bootstrap's); left in, a browser only blocks them,
    and says so in its console.
    """
    page = _SCRIPT.sub("", page)
    while True:
        stripped = _HANDLER.sub(r"\1", page)
        if stripped == page:
            return page
        page = stripped


class PreviewError(Exception):
    """A preview that cannot be made, with the status to answer."""

    def __init__(self, message: str, status: HTTPStatus) -> None:
        """Keep the message and the status."""
        super().__init__(message)
        self.status = status


def _int(value: object, what: str) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        msg = f"Missing or invalid {what}"
        raise PreviewError(msg, HTTPStatus.BAD_REQUEST) from None


def _previewed_template(template: object) -> dict:
    """The template as the renderer takes it, from what core forwards."""
    if not isinstance(template, dict) or not isinstance(template.get("source"), str):
        msg = "Missing template"
        raise PreviewError(msg, HTTPStatus.BAD_REQUEST)
    product_preset_id = template.get("product_preset_id")
    report_item_type_id = template.get("report_item_type_id")
    if (product_preset_id is None) == (report_item_type_id is None):
        msg = "A template is for a product preset or for a report item type"
        raise PreviewError(msg, HTTPStatus.BAD_REQUEST)
    return {
        "id": "preview",
        "product_preset_id": product_preset_id,
        "report_item_type_id": report_item_type_id,
        "source": template["source"],
        "require_tlp_clear": bool(template.get("require_tlp_clear", True)),
        "public_web_ids": [],
    }


def _target(template: dict) -> tuple[str, int]:
    if template.get("product_preset_id") is not None:
        return ("product", template["product_preset_id"])
    return ("item", template["report_item_type_id"])


def _describe(name: str, error: Exception) -> dict:
    """A template failure for the preview: which template, on which line, and why."""
    line = error.lineno if isinstance(error, TemplateSyntaxError) else None
    if line is None:
        # A runtime error: Jinja maps the template's frames to its lines, named after the template.
        frames = [frame for frame in traceback.extract_tb(error.__traceback__) if frame.filename == name]
        line = frames[-1].lineno if frames else None
    return {"template": name, "line": line, "message": f"{type(error).__name__}: {error}"}


_LOCAL_ASSET = re.compile(r'(src|href)="(/static/([^"?#]+)|/branding/(logo|favicon|preview))(\?[^"]*)?"')
_STYLESHEET = re.compile(r'<link\s+rel="stylesheet"\s+href="/static/([^"?#]+\.css)(\?[^"]*)?"\s*/?>')


def _self_contained(page: str, web_id: int, cache: WebCache) -> str:
    """The page with the node's own stylesheet and images inlined.

    The preview shows in the GUI, whose browser may not reach the web's hostname (a web being set
    up, an internal name): the page must not depend on it for its look.
    """
    static = Path(current_app.static_folder or "")

    def stylesheet(match: re.Match) -> str:
        path = (static / match.group(1)).resolve()
        if static.resolve() not in path.parents or not path.is_file():
            return match.group(0)
        return f"<style>{path.read_text(encoding='utf-8')}</style>"

    def asset(match: re.Match) -> str:
        attribute, static_name, kind = match.group(1), match.group(3), match.group(4)
        if kind:
            image = cache.get_web_image(web_id, kind)
            if image is None:
                return match.group(0)
            data, mime_type = image
        else:
            path = (static / static_name).resolve()
            if static.resolve() not in path.parents or not path.is_file():
                return match.group(0)
            data, mime_type = path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return f'{attribute}="data:{mime_type};base64,{base64.b64encode(data).decode("ascii")}"'

    return _LOCAL_ASSET.sub(asset, _STYLESHEET.sub(stylesheet, page))


def _with_base(page: str, base: str) -> str:
    """The page with a ``<base>``, so its styles, images and links resolve against the web, not the GUI."""
    tag = f'<base href="{base}/" target="_blank">'
    match = _HEAD.search(page)
    return page[: match.end()] + tag + page[match.end() :] if match else tag + page


def render_preview(payload: dict, cache: WebCache) -> dict:
    """Render the preview core asked for.

    Args:
        payload: ``{"template", "product_id", "web_id", "language", "view"}``.
        cache: The site's cache (webs, stored templates, and the client to core).

    Returns:
        dict: ``{"view", "html"}`` (detail, summary) or ``{"view", "rss": {title, link, description},
            "xml"}``, with ``errors`` and ``warnings``.

    Raises:
        PreviewError: For a request that cannot be served.
    """
    view = payload.get("view") if payload.get("view") in VIEWS else "detail"
    previewed = _previewed_template(payload.get("template"))
    web_id = _int(payload.get("web_id"), "web")
    product_id = _int(payload.get("product_id"), "product")

    web = next((web for web in cache.get_webs() if web.get("id") == web_id), None)
    if web is None:
        msg = f"Web {web_id} is not served by this node"
        raise PreviewError(msg, HTTPStatus.NOT_FOUND)
    probe = SiteContext(web, "")
    language = payload.get("language") if payload.get("language") in probe.languages else probe.default_language
    # As a visitor sees it: links carry ?lang= only for a language other than the web's default.
    site = SiteContext(web, language, chosen=language != probe.default_language)
    g.site = site

    data = cache.client.get_product(product_id, web_id, language)
    if data is None:
        msg = f"Product {product_id} is not published to this web"
        raise PreviewError(msg, HTTPStatus.NOT_FOUND)

    stored = cache.get_report_templates()
    target = _target(previewed)
    own = [template for template in templates_for_web(stored["items"], web_id) if _target(template) != target]
    errors: list[dict] = []

    def failed(name: str, _what: str, error: Exception) -> None:
        if name.startswith(("product/", "item/")):
            errors.append(_describe(name, error))

    renderer = ReportRenderer([*own, previewed], stored["disabled_builtins"], on_error=failed)
    try:
        product = build_product(data, renderer.has_item_template)
    except InvalidProductError as error:
        raise PreviewError(str(error), HTTPStatus.UNPROCESSABLE_ENTITY) from error

    warnings = []
    if product["items_left_out"]:
        warnings.append(f"{product['items_left_out']} report item(s) have no template to show them and are left out")
    preset_id = product["product_preset"]["id"]
    shown, reason = displayable(
        product,
        vulnerability_only=not renderer.has_product_template(preset_id),
        require_tlp_clear=renderer.require_tlp_clear(preset_id),
    )
    if not shown:
        warnings.append(f"The web would not show this product: {reason}")

    options = {
        "selected_items": [],
        "translate": translate,
        "lang": site.language,
        "site": {"content": site.content, "metadata": site.metadata, "hostname": site.hostname, "language": site.language},
    }
    result: dict = {"view": view, "errors": errors, "warnings": warnings, "language": site.language}
    if view == "rss":
        link = site.hostname + url_for("reports.show", report_id=product["id"])
        description = remove_link_references(renderer.render_text(product, **options), product["links"])
        feed = FeedGenerator()
        feed.title(site.metadata.get("rss_title", "") or "Preview")
        feed.description(site.metadata.get("rss_description", "") or "Preview")
        feed.link(href=site.hostname)
        entry = feed.add_entry()
        entry.title(product["title"])
        entry.link(href=link)
        entry.description(description)
        entry.guid(link, permalink=True)
        xml = feed.rss_str(pretty=True).decode("utf-8")
        item = re.search(r"<item>.*</item>", xml, re.DOTALL)
        result["rss"] = {"title": product["title"], "link": link, "description": description}
        result["xml"] = item.group(0) if item else xml
        return result

    if view == "summary":
        summary = renderer.render(product, "summary", **options)
        page = render_template("homepage.html", entries=[(product, summary)], search_arg=None, page=1, pages=1, warning_seen="1")
    else:
        detail = renderer.render(product, "detail", **options)
        page = render_template(
            "report.html",
            report=product,
            detail=detail,
            items=[],
            feedback_q=site.feedback_questions,
            warning_seen="1",
        )
    result["html"] = _with_base(_self_contained(_without_scripts(page), web_id, cache), site.hostname)
    return result
