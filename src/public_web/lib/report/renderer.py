"""Render products through the report templates.

Templates are looked up in two layers, custom ones (stored in core, edited in the GUI)
before the built-in ones shipped in ``shared.public_web_templates``. A custom template applies
to the webs it lists, or to every web when it lists none; each web renders with the ones that
apply to it (see :func:`templates_for_web`):

* product page - the custom template of the product's preset, else
  ``builtin/product_vulnerability.html`` for vulnerability reports, else
  ``builtin/product_base.html``;
* each report item (via ``render_item()``) - the custom template of the item's type,
  else ``builtin/item_vulnerability.html`` for the "Vulnerability Report" type Taranis
  creates, else ``builtin/item_generic.html``.

The built-ins public-web falls back on (``DEFAULTS``) can be switched off in core. Off, they
are skipped: a vulnerability report falls back on the base layout, an item on the next
built-in that is on, and an item left with none is not shown - the cache leaves it out of the
product (see :meth:`ReportRenderer.has_item_template`), and does not show a product left with
no item, nor one of a preset without a template of its own once the built-in one is off.

Custom templates run in an immutable sandbox with autoescaping: they cannot reach
Python internals, cannot modify the cached product data, and every value is escaped
unless a sanitizing filter says otherwise. A custom template that fails to render is
logged and replaced by the built-in one for that product or item, so one broken
template never takes a page down.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any

from jinja2 import ChoiceLoader, DictLoader
from jinja2.sandbox import ImmutableSandboxedEnvironment
from lib.logger import get_logger
from lib.report.filters import FILTERS
from lib.report.product import visible_links
from markupsafe import Markup
from shared.public_web_templates import BUILTIN_PREFIX, DEFAULTS, VULNERABILITY_TYPE, builtin_sources

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

logger = get_logger("report-templates", silent=True)

PRODUCT_BASE = "builtin/product_base.html"
PRODUCT_VULNERABILITY = "builtin/product_vulnerability.html"
ITEM_GENERIC = "builtin/item_generic.html"
ITEM_VULNERABILITY = "builtin/item_vulnerability.html"

_TAG = re.compile(r"<[^>]*>")


class ReportRenderer:
    """Renders products with one fixed set of custom templates (see :func:`get_renderer`)."""

    def __init__(self, templates: list[dict], disabled_builtins: Iterable[str] = ()) -> None:
        """Build the template environment for the given custom templates and switched-off built-ins (as served by core)."""
        # Only the built-ins public-web falls back on can be off; the bases are always there.
        self._disabled = frozenset(disabled_builtins) & frozenset(DEFAULTS)
        self._product_templates = {t["product_preset_id"]: t for t in templates if t.get("product_preset_id") is not None}
        self._item_templates = {t["report_item_type_id"]: t for t in templates if t.get("report_item_type_id") is not None}
        custom = {f"product/{product_preset_id}": t.get("source") or "" for product_preset_id, t in self._product_templates.items()}
        custom |= {f"item/{type_id}": t.get("source") or "" for type_id, t in self._item_templates.items()}
        self.env = ImmutableSandboxedEnvironment(
            loader=ChoiceLoader([DictLoader(custom), DictLoader(builtin_sources())]),
            autoescape=True,
        )
        self.env.filters.update(FILTERS)

    # -- resolution --------------------------------------------------------

    def has_product_template(self, product_preset_id: int | None) -> bool:
        """Whether the product preset has a report template of its own."""
        return product_preset_id in self._product_templates

    def require_tlp_clear(self, product_preset_id: int | None) -> bool:
        """Whether the product preset's products are hidden unless they carry a public TLP."""
        template = self._product_templates.get(product_preset_id)
        return True if template is None else bool(template.get("require_tlp_clear", True))

    def has_builtin_product_template(self) -> bool:
        """Whether products of a preset without a template of its own are shown (with the built-in one)."""
        return PRODUCT_VULNERABILITY not in self._disabled

    def _builtin_product(self, product: dict) -> str:
        """The built-in a product falls back on; the base layout cannot be switched off."""
        if product["is_vulnerability"] and PRODUCT_VULNERABILITY not in self._disabled:
            return PRODUCT_VULNERABILITY
        return PRODUCT_BASE

    def _builtin_items(self, item: dict) -> list[str]:
        """The built-ins an item falls back on, in order, that are on: the one for its type, then the generic one.

        The vulnerability template fits the "Vulnerability Report" type as Taranis creates it, so
        only a type of that title gets it; others - a renamed or extended copy, a type of one's own - get the
        generic one, unless they have a template of their own.
        """
        names = [ITEM_VULNERABILITY, ITEM_GENERIC] if item["type"] == VULNERABILITY_TYPE else [ITEM_GENERIC]
        return [name for name in names if name not in self._disabled]

    def product_template(self, product: dict) -> str:
        """The loader name of the template a product renders with."""
        product_preset_id = product["product_preset"]["id"]
        return f"product/{product_preset_id}" if product_preset_id in self._product_templates else self._builtin_product(product)

    def has_item_template(self, item: dict) -> bool:
        """Whether a report item can be shown: its type has a template, or a built-in it falls back on is on."""
        return self.item_template(item) is not None

    def item_template(self, item: dict) -> str | None:
        """The loader name of the template a report item renders with; None when it has none (its built-ins are off)."""
        type_id = item["type_id"]
        if type_id in self._item_templates:
            return f"item/{type_id}"
        return next(iter(self._builtin_items(item)), None)

    # -- rendering ---------------------------------------------------------

    def _render(self, names: list[str], context: dict[str, Any], what: str, *, last_resort: str | None = None) -> str:
        """Render the first template of ``names`` that works.

        The last one's errors propagate (a built-in that fails is a bug), unless there is a
        ``last_resort`` to return instead when every one fails.
        """
        for name in names if last_resort is not None else names[:-1]:
            try:
                return self.env.get_template(name).render(context)
            except Exception:
                logger.exception("Report template %s failed for %s.", name, what)
        if last_resort is not None:
            return last_resort
        return self.env.get_template(names[-1]).render(context)

    def render(
        self,
        product: dict,
        view: str = "detail",
        *,
        selected_items: list[int] | None = None,
        translate: Callable[[str, str | None], str] | None = None,
        lang: str = "en",
        site: dict | None = None,
    ) -> Markup:
        """Render one part (``view``: detail, summary or rss) of a product's page.

        For ``rss`` use :meth:`render_text`, which returns plain text.

        ``translate(key, language)`` gives a phrase in a language (None: the page's). A template's
        ``t()`` asks for the language the part it renders is shown in - the product's, or each
        report item's - so a report's own phrases read in its language. The homepage entry
        (``summary``) belongs to the page, so its phrases are in the page's language.
        """

        def phrases(language: str | None) -> Callable[[str], str]:
            if translate is None:
                return lambda key: key
            return lambda key: translate(key, language)

        context: dict[str, Any] = {
            "view": view,
            "product": product,
            "data": {"product": product, "report_items": product["report_items"]},
            "links": product["links"],
            "visible_links": visible_links(product, selected_items),
            "selected_items": selected_items or [],
            "lang": lang,
            "site": site or {},
            "t": phrases(None if view == "summary" else product.get("language")),
        }

        def render_item(item: dict, index: int | None = None) -> Markup:
            item_context = {**context, "item": item, "index": index, "t": phrases(item.get("language"))}
            names = list(dict.fromkeys(name for name in [self.item_template(item), *self._builtin_items(item)] if name))
            # With the built-ins it falls back on switched off, an item whose template fails (or that
            # has none) is left out rather than taking the page down.
            last_resort = None if names and names[-1].startswith(BUILTIN_PREFIX) else ""
            rendered = self._render(names, item_context, f"item {item.get('uuid')}", last_resort=last_resort)
            return Markup(rendered)  # noqa: S704 (autoescaped template output)

        context["render_item"] = render_item
        names = list(dict.fromkeys([self.product_template(product), self._builtin_product(product)]))
        return Markup(self._render(names, context, f"product {product['id']}"))  # noqa: S704 (autoescaped template output)

    def render_text(self, product: dict, **kwargs: Any) -> str:  # noqa: ANN401
        """Render a product's RSS text: tags stripped, entities decoded, lines trimmed."""
        rendered = html.unescape(_TAG.sub("", str(self.render(product, "rss", **kwargs))))
        lines = [line.strip() for line in rendered.splitlines()]
        # Template indentation leaves blank runs; keep at most one blank line between paragraphs.
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def templates_for_web(templates: list[dict], web_id: int | None) -> list[dict]:
    """The custom templates a web renders with.

    For each product preset and report item type, the template that lists the web, else the one
    that lists none (every web). Core never lets two templates of a target claim the same web.
    A core from before templates could be for chosen webs sends no ``public_web_ids``: every
    template is then for every web.
    """
    chosen: dict[tuple[str, int], dict] = {}
    for template in templates:
        web_ids = template.get("public_web_ids") or []
        if web_ids and web_id not in web_ids:
            continue
        if template.get("product_preset_id") is not None:
            target = ("product", template["product_preset_id"])
        elif template.get("report_item_type_id") is not None:
            target = ("item", template["report_item_type_id"])
        else:
            continue
        current = chosen.get(target)
        if current is None or (web_ids and not current.get("public_web_ids")):
            chosen[target] = template
    return list(chosen.values())


# One renderer per web, built for its templates. A renderer compiles its templates as they are
# first used, so keeping it across requests keeps them compiled.
_cached: dict[int | None, tuple[tuple, ReportRenderer]] = {}


def get_renderer(templates: list[dict], disabled_builtins: Iterable[str] = (), web_id: int | None = None) -> ReportRenderer:
    """A renderer for a web (None: no web in particular), reused while its templates stay the same.

    ``templates`` are all the custom templates; the web's are picked by :func:`templates_for_web`.
    A changed template set (after a cache reset) builds a new renderer.
    """
    own = templates_for_web(templates, web_id)
    disabled = tuple(sorted(disabled_builtins))
    key = (
        tuple(
            (t.get("id"), t.get("product_preset_id"), t.get("report_item_type_id"), t.get("source"), t.get("require_tlp_clear")) for t in own
        ),
        disabled,
    )
    cached = _cached.get(web_id)
    if cached is None or cached[0] != key:
        cached = _cached[web_id] = (key, ReportRenderer(own, disabled))
    return cached[1]
