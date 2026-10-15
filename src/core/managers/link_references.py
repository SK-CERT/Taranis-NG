"""Stable link references: link keys, citation tokens and their rendering to numbered output.

Text in reports and products cites a link by the link's stable key, written as a token such as
``[#k3f9a2]``. The key is stored with the link itself - in the ``value_description`` of a LINK
attribute value, or as ``key`` of a product link - so inserting, moving or deleting links never
changes what a citation points at.

Tokens never leave core. Everything handed to presenters or public-web nodes is rendered to plain
``[n]`` numbers, which index one merged, de-duplicated list of URLs: the product's own links
first, then the links of each report in report order. Equal URLs share one number.
"""

from __future__ import annotations

import re
import secrets
import string
from typing import TYPE_CHECKING, Any

from shared.log_manager import logger
from shared.schema.attribute import AttributeType

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

LINK_KEY_ALPHABET = string.ascii_lowercase + string.digits
LINK_KEY_LENGTH = 6
# Generated keys are LINK_KEY_LENGTH long; any length in this range is accepted.
LINK_KEY_RE = re.compile(r"[a-z0-9]{4,12}")

# A citation token, with the single space in front of it so that a token whose link is gone can
# be dropped without leaving a double space behind.
LINK_TOKEN_RE = re.compile(rf"( ?)\[#({LINK_KEY_RE.pattern})\]")

# Attribute types whose text may cite links.
CITING_TYPES = frozenset({AttributeType.STRING.name, AttributeType.TEXT.name, AttributeType.RICH_TEXT.name})


def generate_link_key(taken: Collection[str] = ()) -> str:
    """Return a new random link key that is not in ``taken``."""
    while True:
        key = "".join(secrets.choice(LINK_KEY_ALPHABET) for _ in range(LINK_KEY_LENGTH))
        if key not in taken:
            return key


def normalize_links(links: Iterable[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    """Clean a product's link list.

    URLs are trimmed and links without one are dropped. Every remaining link gets a key: one that
    is missing or already used by an earlier link is replaced by a fresh key.
    """
    result: list[dict[str, str]] = []
    taken: set[str] = set()
    for link in links or []:
        url = str(link.get("url") or "").strip()
        if not url:
            continue
        key = str(link.get("key") or "")
        if not LINK_KEY_RE.fullmatch(key) or key in taken:
            key = generate_link_key(taken)
        taken.add(key)
        result.append({"key": key, "url": url})
    return result


class ReferenceIndex:
    """The merged, numbered list of sources of one product.

    Attributes:
        urls: The de-duplicated URLs in citation-number order (``urls[0]`` is ``[1]``).
    """

    def __init__(self) -> None:
        """Create an empty index."""
        self.urls: list[str] = []
        self._number_by_url: dict[str, int] = {}
        self._number_by_key: dict[str, int] = {}

    def add(self, key: str | None, url: str | None) -> int | None:
        """Register a link and return its number, or None for a link without URL.

        A URL that is already listed keeps its number. The first link registering a key owns it
        product-wide, which is how the product description resolves the keys of report links.
        """
        url = (url or "").strip()
        if not url:
            return None
        number = self._number_by_url.get(url)
        if number is None:
            self.urls.append(url)
            number = len(self.urls)
            self._number_by_url[url] = number
        if key:
            self._number_by_key.setdefault(key, number)
        return number

    def render(self, text: str | None, local: Mapping[str, int] | None = None) -> str | None:
        """Replace the citation tokens in ``text`` with their ``[n]`` numbers.

        A key is looked up in ``local`` (the citing report's own links) first and product-wide
        second. A token whose link no longer exists is dropped.
        """
        if not text:
            return text

        def replace(match: re.Match) -> str:
            space, key = match.groups()
            number = (local or {}).get(key) or self._number_by_key.get(key)
            if number is None:
                logger.warning(f"Dropping a citation of the unknown link key '{key}'")
                return ""
            return f"{space}[{number}]"

        return LINK_TOKEN_RE.sub(replace, text)


def build_index(product_links: Iterable[Mapping[str, Any]] | None, reports: Iterable[Iterable[tuple]]) -> tuple[ReferenceIndex, list[dict]]:
    """Number the product links, then the links of each report.

    Args:
        product_links: The product's own links as ``{"key", "url"}`` mappings.
        reports: For every report, its ``(key, url)`` link pairs in display order.

    Returns:
        The index, and for every report a mapping of its own link keys to their numbers.
    """
    index = ReferenceIndex()
    for link in product_links or []:
        index.add(link.get("key"), link.get("url"))
    local_numbers = []
    for links in reports:
        local: dict[str, int] = {}
        for key, url in links:
            number = index.add(key, url)
            if key and number is not None:
                local.setdefault(key, number)
        local_numbers.append(local)
    return index, local_numbers


def render_presenter_input(payload: dict, product_links: Iterable[Mapping[str, Any]] | None) -> dict:
    """Render the citations of a dumped presenter input in place and return it.

    ``payload`` is what ``PresenterInputSchema().dump()`` produced - plain data, never the
    database objects, which must not be modified. Citing attribute values and the product
    description get their ``[n]`` numbers, LINK values are trimmed (empty ones are left out) and
    ``product.links`` becomes the merged list of URLs that those numbers index.
    """
    attribute_types = {}
    # Where a group item sits in the report form; links are numbered in the order shown there.
    form_positions = {}
    for report_type in payload.get("report_types") or []:
        for group in report_type.get("attribute_groups") or []:
            for group_item in group.get("attribute_group_items") or []:
                attribute_types[group_item.get("id")] = (group_item.get("attribute") or {}).get("type")
                form_positions[group_item.get("id")] = (group.get("index") or 0, group_item.get("index") or 0)

    def attribute_type(attribute: dict) -> str | None:
        return attribute_types.get(attribute.get("attribute_group_item_id"))

    def form_position(attribute: dict) -> tuple:
        return (*form_positions.get(attribute.get("attribute_group_item_id"), (0, 0)), attribute.get("id") or 0)

    reports = payload.get("reports") or []
    report_links = []
    for report in reports:
        attributes = []
        link_attributes = []
        for attribute in report.get("attributes") or []:
            if attribute_type(attribute) == AttributeType.LINK.name:
                attribute["value"] = (attribute.get("value") or "").strip()
                if not attribute["value"]:
                    continue
                link_attributes.append(attribute)
            attributes.append(attribute)
        report["attributes"] = attributes
        link_attributes.sort(key=form_position)
        report_links.append([(attribute.get("value_description"), attribute["value"]) for attribute in link_attributes])

    index, local_numbers = build_index(product_links, report_links)

    for report, local in zip(reports, local_numbers, strict=True):
        for attribute in report["attributes"]:
            if attribute_type(attribute) in CITING_TYPES:
                attribute["value"] = index.render(attribute.get("value"), local)

    product = payload.get("product")
    if product is not None:
        product["links"] = list(index.urls)
        product["description"] = index.render(product.get("description"))
    return payload
