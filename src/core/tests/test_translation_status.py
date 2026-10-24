"""The translation status of reports and products per language, and the SQL filters that find them.

The status is the first that applies: missing, outdated, partly translated, translated by AI and
not reviewed, done. An item whose language is not set has only "language not set". The filters
must say the same as the status, so they are compiled and read here; running them needs a
database. Models are built in memory.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from managers import translation_status
from sqlalchemy.dialects import postgresql

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.attribute import Attribute  # noqa: E402 - after every mapper is registered
from model.product import Product  # noqa: E402
from model.report_item import ReportItem, ReportItemAttribute  # noqa: E402
from model.report_item_type import AttributeGroup, AttributeGroupItem, ReportItemType  # noqa: E402
from model.tag import (  # noqa: E402
    LANGUAGE_NOT_SET,
    TRANSLATION_AI,
    TRANSLATION_DONE,
    TRANSLATION_MISSING,
    TRANSLATION_OUTDATED,
    TRANSLATION_PARTIAL,
)
from model.translation import ORIGIN_AI, ORIGIN_MANUAL, ProductTranslation, ReportItemAttributeTranslation, ReportItemTranslation  # noqa: E402
from shared.schema.attribute import AttributeType  # noqa: E402


def _report(prefix: str = "") -> ReportItem:
    """A Czech report with a translatable description, a note that is not translated, and empty text."""
    items = []
    for item_id, (title, attribute_type, translate) in enumerate(
        [("Description", AttributeType.TEXT, True), ("Note", AttributeType.TEXT, False), ("Impact", AttributeType.TEXT, True)],
        start=1,
    ):
        item = AttributeGroupItem(item_id, title, "", item_id, 0, 1, item_id, None, None, translate=translate)
        item.attribute = Attribute(None, title, "", attribute_type, None, None, None, [])
        items.append(item)
    group = AttributeGroup(None, "Main", "", None, None, 0, items)
    report_type = ReportItemType(None, "Vulnerability", "", [group], languages=["cs", "en", "sk"])
    attributes = []
    for attribute_id, (item, value) in enumerate(zip(items, ["Útočník může", "interní", ""], strict=True), start=10):
        attribute = ReportItemAttribute(None, value, "", None, 0, None, item.id, item.title)
        attribute.id = attribute_id
        attribute.attribute_group_item = item
        attributes.append(attribute)
    report = ReportItem(7, None, "Kritická chyba", prefix, None, None, [], [], attributes)
    report.report_item_type = report_type
    report.language = "cs"
    return report


def _title(report: ReportItem, language: str, origin: str = ORIGIN_MANUAL, field: str = "title") -> ReportItemTranslation:
    row = ReportItemTranslation(language=language, field=field, value="", version=0)
    row.write(f"{field} ({language})", getattr(report, field), origin, 1)
    report.translations.append(row)
    return row


def _value(report: ReportItem, language: str, origin: str = ORIGIN_MANUAL) -> ReportItemAttributeTranslation:
    description = report.attributes[0]
    row = ReportItemAttributeTranslation(language=language, value="", version=0)
    row.write(f"Popis ({language})", description.value, origin, 1)
    description.translations.append(row)
    return row


def test_a_language_with_nothing_translated_is_missing() -> None:
    assert translation_status.report_status(_report()) == {"en": TRANSLATION_MISSING, "sk": TRANSLATION_MISSING}


def test_the_name_and_the_translatable_fields_with_a_value_count() -> None:
    report = _report()
    _title(report, "en")
    # Only the name: the description still waits; the note and the empty field do not count.
    assert translation_status.report_status(report)["en"] == TRANSLATION_PARTIAL
    _value(report, "en")
    assert translation_status.report_status(report)["en"] == TRANSLATION_DONE


def test_a_prefix_counts_when_there_is_one() -> None:
    report = _report(prefix="VULN")
    _title(report, "sk")
    _value(report, "sk")
    assert translation_status.report_status(report)["sk"] == TRANSLATION_PARTIAL
    _title(report, "sk", field="title_prefix")
    assert translation_status.report_status(report)["sk"] == TRANSLATION_DONE


def test_outdated_wins_over_partial_and_ai_over_done() -> None:
    report = _report()
    _title(report, "en", origin=ORIGIN_AI)
    _value(report, "en")
    assert translation_status.report_status(report)["en"] == TRANSLATION_AI

    report.title = "Kritická chyba v jádře"
    report.attributes[0].translations.clear()
    # The name's translation is outdated and the description has none: outdated says more.
    assert translation_status.report_status(report)["en"] == TRANSLATION_OUTDATED


def test_a_report_of_no_language_has_no_status_per_language() -> None:
    report = _report()
    report.language = None

    assert translation_status.report_status(report) == {"": LANGUAGE_NOT_SET}


def _product() -> Product:
    product = Product(-1, "Bulletin", "", 2, None, [], [])
    product.language = "cs"
    product.report_items = [_report()]
    return product


def test_a_products_status_is_its_titles_in_the_languages_of_its_reports_types() -> None:
    product = _product()
    row = ProductTranslation(language="sk", field="title", value="", version=0)
    row.write("Bulletin (sk)", product.title, ORIGIN_AI, 1)
    product.title_translation_rows.append(row)

    assert translation_status.product_status(product) == {"en": TRANSLATION_MISSING, "sk": TRANSLATION_AI}

    product.title = "Weekly bulletin"
    assert translation_status.product_status(product)["sk"] == TRANSLATION_OUTDATED
    product.language = None
    assert translation_status.product_status(product) == {"": LANGUAGE_NOT_SET}


def test_the_list_payloads_carry_tags_and_status() -> None:
    report = _report()

    assert report.tag_ids == []
    assert report.translation_status == {"en": TRANSLATION_MISSING, "sk": TRANSLATION_MISSING}


def _compiled(condition: object) -> tuple[str, list]:
    """The SQL of a condition and the values it binds."""
    compiled = condition.compile(dialect=postgresql.dialect())
    return str(compiled), list(compiled.params.values())


def test_the_report_filters_compare_the_stored_fingerprint_with_the_current_text() -> None:
    needs, needs_values = _compiled(ReportItem.translation_condition("sk", needs=True))
    unreviewed, unreviewed_values = _compiled(ReportItem.translation_condition("sk", needs=False))

    # Same SHA-256 of the UTF-8 text as model/translation.py's source_hash.
    assert "encode(sha256(convert_to(coalesce(report_item.title, " in needs
    assert "report_item_type_1.languages @> " in needs
    assert "report_item.language != " in needs
    assert "NOT (EXISTS" in needs
    assert ["sk"] in needs_values
    assert "UTF8" in needs_values
    assert ORIGIN_AI in unreviewed_values
    assert ORIGIN_AI not in needs_values
    assert "NOT (EXISTS" not in unreviewed


def test_the_product_filters_look_at_the_title() -> None:
    needs, needs_values = _compiled(Product.translation_condition("en", needs=True))

    assert "encode(sha256(convert_to(coalesce(product.title, " in needs
    assert "NOT (EXISTS" in needs
    assert ["en"] in needs_values
    assert ORIGIN_AI in _compiled(Product.translation_condition("en", needs=False))[1]


class _Query:
    """Records the conditions a list filter adds."""

    def __init__(self) -> None:
        self.conditions: list = []

    def filter(self, condition: object) -> _Query:
        self.conditions.append(condition)
        return self


def test_the_list_filters_take_tags_and_one_translation_filter() -> None:
    query = ReportItem._filter_tags_and_translation(_Query(), {"tags": [3, 5], "translation": "needs", "translation_language": "sk"})
    (tags, tag_values), (translation, _values) = (_compiled(condition) for condition in query.conditions)
    assert "report_item_tag.tag_id IN" in tags
    assert [3, 5] in tag_values
    assert "sha256" in translation

    not_set = ReportItem._filter_tags_and_translation(_Query(), {"translation": "not_set"})
    assert [_compiled(condition)[0] for condition in not_set.conditions] == ["report_item.language IS NULL"]
    assert Product._filter_tags_and_translation(_Query(), {}).conditions == []
