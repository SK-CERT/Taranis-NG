"""The translation status of a report or product in each of its languages, as built-in tags.

For each language an item can be read in besides its own, the fields that count are those with
something to translate: a report's name, its prefix and its translatable fields (when not empty),
a product's title. The status is the first that applies:

1. ``translation_missing`` - none of them has a translation;
2. ``translation_outdated`` - a translation was made from an earlier original;
3. ``translation_partial`` - some field has no translation yet;
4. ``translation_ai`` - everything is translated and current, and AI made some of it;
5. ``translation_done``.

An item whose own language is not set has no translation status, only ``language_not_set``,
under the key ``""``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from model.tag import (
    LANGUAGE_NOT_SET,
    TRANSLATION_AI,
    TRANSLATION_DONE,
    TRANSLATION_MISSING,
    TRANSLATION_OUTDATED,
    TRANSLATION_PARTIAL,
)
from model.translation import ORIGIN_AI, TITLE_FIELDS

if TYPE_CHECKING:
    from collections.abc import Iterable

    from model.product import Product
    from model.report_item import ReportItem
    from model.translation import TranslationMixin

# The key the status of an item without a language is under.
NO_LANGUAGE = ""


def status_of(fields: Iterable[tuple[str | None, TranslationMixin | None]]) -> str:
    """The status of one language from its fields: each field's original and its translation row.

    Args:
        fields (Iterable[tuple[str | None, TranslationMixin | None]]): Original text and translation row
            (or None) of every field that counts.

    Returns:
        str: A ``translation_*`` key.
    """
    fields = list(fields)
    present = [(original, row) for original, row in fields if row is not None and row.value]
    if not present:
        return TRANSLATION_MISSING
    if any(row.is_outdated(original) for original, row in present):
        return TRANSLATION_OUTDATED
    if len(present) < len(fields):
        return TRANSLATION_PARTIAL
    if any(row.origin == ORIGIN_AI for _original, row in present):
        return TRANSLATION_AI
    return TRANSLATION_DONE


def _report_fields(report_item: ReportItem, language: str) -> list[tuple[str | None, TranslationMixin | None]]:
    titles = {row.field: row for row in report_item.translations if row.language == language}
    fields = [(getattr(report_item, field), titles.get(field)) for field in TITLE_FIELDS if getattr(report_item, field)]
    for attribute in report_item.attributes:
        group_item = attribute.attribute_group_item
        if group_item is None or not group_item.is_translated or not attribute.value:
            continue
        row = next((row for row in attribute.translations if row.language == language), None)
        fields.append((attribute.value, row))
    return fields


def report_status(report_item: ReportItem) -> dict[str, str]:
    """The status of a report in each language of its type besides its own.

    Args:
        report_item (ReportItem): The report.

    Returns:
        dict[str, str]: Language to status key, or ``{"": "language_not_set"}``.
    """
    if not report_item.language:
        return {NO_LANGUAGE: LANGUAGE_NOT_SET}
    return {language: status_of(_report_fields(report_item, language)) for language in report_item.variant_languages()}


def product_languages(product: Product) -> list[str]:
    """The languages a product can be rendered in besides its own: those of its reports' types.

    Args:
        product (Product): The product.

    Returns:
        list[str]: ISO 639-1 codes, in the order the reports name them.
    """
    languages: list[str] = []
    for report_item in product.report_items:
        for language in report_item.type_languages:
            if language != product.language and language not in languages:
                languages.append(language)
    return languages


def product_status(product: Product) -> dict[str, str]:
    """The status of a product's title in each of its languages besides its own.

    Args:
        product (Product): The product.

    Returns:
        dict[str, str]: Language to status key, or ``{"": "language_not_set"}``.
    """
    if not product.language:
        return {NO_LANGUAGE: LANGUAGE_NOT_SET}
    rows = {row.language: row for row in product.title_translation_rows if row.field == "title"}
    return {language: status_of([(product.title, rows.get(language))]) for language in product_languages(product)}
