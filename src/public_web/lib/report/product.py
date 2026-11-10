"""Turn a product served by core into the data report templates are rendered with.

Core's public-web API serves a product as product info plus report items, each with
a flat list of attributes (``{"key", "value", "description", ...}``). ``build_product``
reshapes that into plain dicts - plain so they are safe in the template sandbox,
picklable for the cache, and usable with Jinja's ``selectattr``/``map``. Each item's
``attrs`` follows the presenter templates' convention (attribute title lowercased with
underscores; one value or a list), so a presenter template's logic carries over.

Link citations arrive numbered: core renders them to ``[1]``, ``[2]``... and serves
``links``, the product's sources those numbers index (the product's own links first,
then each item's). Nothing is renumbered here.

A product may be shown in a language other than it was written in (``language``). Its
texts then arrive translated, and a choice constant arrives as its translation
(``value``) with the constant itself in ``source_value``. ``attrs`` keeps the constants as
written, as presenter templates get them, so what a template compares (and the TLP this
module decides on) is the same in every language; ``attrs_display`` and ``fields`` hold
what to show.

A report item public-web has no template for (its type has none of its own, and the
built-ins it could fall back on are switched off in core) is left out of the product: of its
blocks, its RSS text, its search and the links only it cites. Its TLP still counts.

No report item type has a role of its own: every item is one of the product's items, in order.
A page that wants one item apart - an introduction above the others, say - does so in a
custom product template.

This module also decides whether a product may be shown at all (``displayable``).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lib.report import fix_spaces, format_iso_date, get_cvss_severity
from lib.report.vulnerability import cvss_score

if TYPE_CHECKING:
    from collections.abc import Callable

VULNERABILITY_TYPE_PREFIX = "Vulnerability Report"
# A "[n]" citation of the product's links in a text.
CITATION = re.compile(r"\[(\d+)\]")

TLP_ORDER = {
    "WHITE": 0,
    "CLEAR": 1,
    "GREEN": 2,
    "AMBER": 3,
    "AMBER+STRICT": 4,
    "RED": 5,
}
# TLP:WHITE is TLP 1.0's name for what TLP 2.0 calls CLEAR: unlimited disclosure.
PUBLIC_TLPS = ("CLEAR", "WHITE")


class InvalidProductError(ValueError):
    """The data core served is not a product (it lacks its id or title)."""


def _values(item: dict, key: str) -> list[str]:
    return [attribute["value"] for attribute in item["attributes"] if attribute["key"] == key and attribute["value"] is not None]


def _links(item: dict) -> list[str]:
    """The item's links: the values of its LINK attributes."""
    return [attribute["value"] for attribute in item["attributes"] if attribute["type"] == "LINK" and attribute["value"]]


def _shape_attrs(attributes: list[dict], field: str = "source_value") -> dict[str, Any]:
    """Group attributes by key into the presenter-compatible ``attrs`` mapping.

    One value where the attribute group item allows a single occurrence, a list where
    it allows more, a list for multiple-choice values, and ``{value: description}``
    for CWE keys (as presenter templates expect). Attributes served by an older core
    carry no ``multiple`` flag; those become a list only when there is more than one value.
    ``field`` picks the constants as written (``source_value``) or as shown (``value``).
    """
    grouped: dict[str, list[dict]] = {}
    for attribute in attributes:
        grouped.setdefault(attribute["key"], []).append(attribute)

    attrs: dict[str, Any] = {}
    for key, entries in grouped.items():
        values = [entry[field] for entry in entries if entry[field] is not None]
        if key.startswith("cwe"):
            attrs[key] = {entry[field]: entry["description"] for entry in entries if entry[field] is not None}
        elif any(entry["type"] == "MULTI_CHOICE" for entry in entries):
            attrs[key] = values
        else:
            multiple = entries[0]["multiple"]
            if multiple is None:
                multiple = len(values) > 1
            attrs[key] = values if multiple else (values[0] if values else None)
    return attrs


def _fields(attributes: list[dict]) -> list[dict]:
    """One entry per attribute key, in attribute order, with all its values.

    The values are under ``value_list``, not ``values``: in a template ``field.values``
    would find the dict's own ``values()`` method before the key.
    """
    fields: dict[str, dict] = {}
    for attribute in attributes:
        field = fields.setdefault(
            attribute["key"],
            {"key": attribute["key"], "label": attribute["label"], "group": attribute["group"], "type": attribute["type"], "value_list": []},
        )
        if attribute["value"] not in (None, ""):
            field["value_list"].append(attribute["value"])
    return list(fields.values())


def _build_item(data: dict) -> dict:
    attributes = []
    for position, attribute in enumerate(data.get("attributes") or []):
        key = (attribute.get("key") or "").strip()
        order = attribute.get("order")
        attributes.append(
            {
                "key": key,
                "label": attribute.get("label") or key.replace("_", " ").capitalize(),
                "group": attribute.get("group") or "",
                "type": attribute.get("attribute_type") or "",
                "multiple": attribute.get("multiple"),
                "value": attribute.get("value"),
                "source_value": attribute.get("source_value", attribute.get("value")),
                "description": attribute.get("description"),
                "_order": (tuple(order) if isinstance(order, list) else (), position),
            },
        )
    # Order by the report item type's layout; attributes of one key keep their order.
    attributes.sort(key=lambda attribute: attribute["_order"])
    for attribute in attributes:
        del attribute["_order"]

    return {
        "name": fix_spaces(data.get("title") or ""),
        "name_prefix": data.get("title_prefix") or "",
        "uuid": data.get("uuid"),
        # The type's title as written, which the templates compare; its name in the language shown.
        "type": data.get("type") or "",
        "type_label": data.get("type_label") or data.get("type") or "",
        "type_id": data.get("type_id"),
        "type_description": data.get("type_description") or "",
        # The language the item is shown in, which its labels and constants follow; None when
        # core knows none (or was asked for none).
        "language": data.get("language"),
        # How much of what is shown the AI translated ("unreviewed", "reviewed" or None), and
        # the language the item was written in.
        "ai_translation": data.get("ai_translation"),
        "original_language": data.get("original_language"),
        "created": data.get("created"),
        "last_updated": data.get("last_updated"),
        "attributes": attributes,
    }


def _tlp(item: dict) -> str | None:
    """The item's TLP as written, never as shown in a language."""
    for attribute in item["attributes"]:
        if (attribute["type"] == "TLP" or attribute["key"] == "tlp") and attribute["source_value"]:
            return str(attribute["source_value"]).strip().upper()
    return None


def build_product(data: dict, shown: Callable[[dict], bool] | None = None) -> dict:
    """Build the template data for one product as served by core.

    Args:
        data: The product as core serves it.
        shown: Whether a report item can be shown (public-web has a template for it); the
            others are left out, though their TLP still counts. Every item is shown without it.

    Raises:
        InvalidProductError: When the product has no id or title.
    """
    if data.get("id") is None or not data.get("title"):
        msg = "Product id or title is missing"
        raise InvalidProductError(msg)

    every_item = [_build_item(item) for item in data.get("report_items") or []]
    for item in every_item:
        item["attrs"] = _shape_attrs(item["attributes"])
        item["attrs_display"] = _shape_attrs(item["attributes"], "value")
        item["fields"] = _fields(item["attributes"])
    items = [item for item in every_item if shown is None or shown(item)]
    left_out = [item for item in every_item if not any(item is kept for kept in items)]
    description = fix_spaces(data.get("description") or "")

    # The product's sources as core numbered them: "[n]" in any text is links[n - 1]. Those only
    # left-out items cite are hidden, keeping the numbers of the others.
    links = [link for link in data.get("links") or [] if link]
    cited = {link for item in items for link in _links(item)} | set(_cited_by(description, links))
    hidden_links = [link for link in dict.fromkeys(link for item in left_out for link in _links(item)) if link not in cited]

    # Every item's TLP decides whether the product may be shown, those left out too.
    tlps = [tlp for item in every_item if (tlp := _tlp(item))]
    scores = [score for item in items if (score := cvss_score(_first(item, "cvss"))) is not None]
    user = data.get("user") or {}
    preset = data.get("product_preset") or {}

    return {
        "id": data["id"],
        "title": fix_spaces(data["title"]),
        "description": description,
        # The same as description, under the name templates written before used.
        "lead": description,
        "created": data.get("created"),
        "published": _published(data.get("created")),
        "author": user.get("name"),
        "author_username": user.get("username"),
        # What the product is published as; its report template is the product preset's.
        "product_preset": {"id": preset.get("id"), "title": preset.get("title") or ""},
        # The language it is shown in; None when core knows none (or was asked for none).
        "language": data.get("language"),
        # Read, in part, from an AI translation: "unreviewed" when some of it nobody has
        # reviewed yet, "reviewed" when a person reviewed all of it, None when none of it is.
        "ai_translation": data.get("ai_translation"),
        # The language it was written in, for the link to the original.
        "original_language": data.get("original_language"),
        "report_items": items,
        # The same as report_items: the items the page lists (?items= counts them from 1).
        "body_items": items,
        "links": links,
        # How many report items were left out for want of a template, and the links only they cite.
        "items_left_out": len(left_out),
        "hidden_links": hidden_links,
        "max_tlp": max(tlps, key=lambda tlp: TLP_ORDER.get(tlp, 1)) if tlps else None,
        "max_cvss": max(scores) if scores else None,
        # What the product is, whichever of its items are shown.
        "is_vulnerability": any(item["type"].startswith(VULNERABILITY_TYPE_PREFIX) for item in every_item),
    }


def _first(item: dict | None, key: str) -> str | None:
    values = _values(item, key) if item else []
    return values[0] if values else None


def _published(created: str | None) -> str:
    try:
        return format_iso_date(created)
    except ValueError:
        return ""


def displayable(product: dict, *, vulnerability_only: bool, require_tlp_clear: bool = True) -> tuple[bool, str]:
    """Decide whether a product may appear on a public web.

    Args:
        product: As built by :func:`build_product`.
        vulnerability_only: The product's preset has no report template of its own,
            so the product is shown only if it is a vulnerability report, as public-web
            always did.
        require_tlp_clear: From the product preset's template; a product with no TLP
            at all is shown only when this is False. Any TLP found must be public.

    Returns:
        (bool, str): Whether to show it, and why not.
    """
    if vulnerability_only and not product["is_vulnerability"]:
        return False, "not a vulnerability report, and its product preset has no report template"
    tlp = product["max_tlp"]
    if tlp is None:
        if require_tlp_clear or vulnerability_only:
            return False, "no TLP, and its product preset requires TLP:CLEAR"
        return True, ""
    if tlp not in PUBLIC_TLPS:
        return False, f"TLP {tlp} must not be published"
    return True, ""


def _cited_by(text: str, links: list[str]) -> list[str]:
    """The links a text cites as "[n]"."""
    numbers = {int(number) for number in CITATION.findall(text or "")}
    return [links[number - 1] for number in sorted(numbers) if 1 <= number <= len(links)]


def visible_links(product: dict, selected_items: list[int] | None) -> list[str | None]:
    """The product's links, with those not used by the selected items replaced by None.

    ``selected_items`` are 1-based positions in ``body_items`` (the page's ``?items=``).
    The links the product's description cites always stay, as the description does; those
    only left-out items cite never show. Hidden links become None rather than disappearing,
    so the remaining ones keep the numbers the text refers to.
    """
    links = product["links"]
    if not selected_items:
        hidden = set(product.get("hidden_links") or ())
        return [None if link in hidden else link for link in links] if hidden else links
    shown = set(_cited_by(product["description"], links))
    for position, item in enumerate(product["body_items"], start=1):
        if position in selected_items:
            shown.update(_links(item))
    return [link if link in shown else None for link in links]


def _keyword_texts(product: dict) -> list[str]:
    """What a search looks through, lowercased."""
    texts: list[object] = [
        product["title"],
        product["description"],
        product["id"],
        f"[TLP:{product['max_tlp']}] " if product["max_tlp"] else None,
        product["author"],
        product["published"],
        product["max_cvss"],
        get_cvss_severity(product["max_cvss"]),
    ]
    for item in product["report_items"]:
        texts.append(item["name"])
        for attribute in item["attributes"]:
            texts.append(attribute["value"])
            if attribute["key"].startswith("cwe") and attribute["value"]:
                texts.append(f"CWE-{attribute['value']}")
    return [str(text).lower() for text in texts if text is not None]


def matches_keyword(product: dict, keyword: str) -> bool:
    """Whether the keyword occurs anywhere a reader would look for it.

    The texts are gathered once per product and kept with it: a search goes through every
    published product.
    """
    texts = product.get("_keyword_texts")
    if texts is None:
        texts = product["_keyword_texts"] = _keyword_texts(product)
    needle = keyword.lower().strip()
    return any(needle in text for text in texts)


def remove_link_references(text: str, links: list[str | None]) -> str:
    """Remove the link references ([1], [2]...) from a plain text (the RSS description)."""
    for i, _ in enumerate(links, start=1):
        text = text.replace(f" [{i}]", "").replace(f"[{i}]", "")
    return text
