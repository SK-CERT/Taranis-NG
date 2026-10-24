"""Rendering in a language: the fallback chain, templates, presenter input, the publish check and the public web.

Every text is looked up in the requested language, then English, then its own language; a
language that is the text's own gives the original. Keys, titles and raw constants never change:
translations arrive as extra fields. Models are built in memory; no database.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from api import public_web
from managers import content_language, content_localizer

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.attribute import Attribute, AttributeEnum  # noqa: E402 - after every mapper is registered
from model.report_item import ReportItem, ReportItemAttribute  # noqa: E402
from model.report_item_type import AttributeGroup, AttributeGroupItem, ReportItemType  # noqa: E402
from model.translation import ORIGIN_AI, ProductTranslation, ReportItemAttributeTranslation, ReportItemTranslation  # noqa: E402
from shared.schema.attribute import AttributeType  # noqa: E402


@pytest.mark.parametrize(
    ("requested", "source", "chain"),
    [
        ("sk", "cs", ["sk", "en", "cs"]),
        ("en", "cs", ["en", "cs"]),
        ("cs", "cs", ["cs", "en"]),
        (None, "cs", ["en", "cs"]),
        ("de", None, ["de", "en"]),
    ],
)
def test_the_chain_is_requested_english_source(requested: str | None, source: str | None, chain: list) -> None:
    assert content_localizer.language_chain(requested, source) == chain


def test_the_original_wins_in_its_own_language() -> None:
    translations = {"en": "Critical bug", "sk": "Kritická chyba v jadre"}

    assert content_localizer.resolve("cs", "cs", "Kritická chyba", translations.get) == ("Kritická chyba", "cs")
    assert content_localizer.resolve("sk", "cs", "Kritická chyba", translations.get) == ("Kritická chyba v jadre", "sk")
    assert content_localizer.resolve("de", "cs", "Kritická chyba", translations.get) == ("Critical bug", "en")
    assert content_localizer.resolve("de", "cs", "Kritická chyba", {}.get) == ("Kritická chyba", "cs")
    # An original of unknown language is only the last resort.
    assert content_localizer.resolve("cs", None, "Old report", translations.get) == ("Critical bug", "en")
    assert content_localizer.resolve("cs", None, "Old report", {}.get) == ("Old report", None)


def test_templates_follow_the_chain_and_inherit_what_a_language_leaves_out() -> None:
    defaults = {"TITLE_TEMPLATE_PATH": "t_cz.txt", "BODY_TEMPLATE_PATH": "b_cz.txt", "SENDER": "cert@example.test"}
    overrides = {"sk": {"BODY_TEMPLATE_PATH": "b_sk.txt"}, "en": {"BODY_TEMPLATE_PATH": "b_en.txt", "TITLE_TEMPLATE_PATH": "t_en.txt"}}

    params, language = content_localizer.resolve_language_templates(defaults, overrides, "cs", "sk")
    assert language == "sk"
    assert params == {"TITLE_TEMPLATE_PATH": "t_cz.txt", "BODY_TEMPLATE_PATH": "b_sk.txt", "SENDER": "cert@example.test"}

    assert content_localizer.resolve_language_templates(defaults, overrides, "cs", "cs") == (defaults, "cs")
    assert content_localizer.resolve_language_templates(defaults, overrides, "cs", "de")[1] == "en"
    assert content_localizer.resolve_language_templates(defaults, {}, None, "de") == (defaults, None)


def test_template_overrides_are_checked_against_the_presenter() -> None:
    keys = ["TITLE_TEMPLATE_PATH", "BODY_TEMPLATE_PATH"]

    assert content_language.clean_language_templates(
        {"sk": {"BODY_TEMPLATE_PATH": " b_sk.txt ", "TITLE_TEMPLATE_PATH": ""}, "cs": {}},
        keys,
    ) == {
        "sk": {"BODY_TEMPLATE_PATH": "b_sk.txt"},
    }
    with pytest.raises(ValueError, match="Not a template parameter of this presenter: SENDER"):
        content_language.clean_language_templates({"sk": {"SENDER": "x"}}, keys)
    with pytest.raises(ValueError, match="Unknown language code: cz"):
        content_language.clean_language_templates({"cz": {"BODY_TEMPLATE_PATH": "x"}}, keys)


def test_constant_translations_are_cleaned_and_none_means_not_sent() -> None:
    assert content_language.clean_enum_translations(None) is None
    assert content_language.clean_enum_translations({"cs": {"value": "Vysoká", "description": "", "x": "y"}}) == {"cs": {"value": "Vysoká"}}


# ---- presenter input -------------------------------------------------------------------


def _item(item_id: int, title: str, attribute_type: AttributeType, *, translate: bool = False, enums: tuple = ()) -> AttributeGroupItem:
    item = AttributeGroupItem(item_id, title, f"{title} help", item_id, 0, 1, item_id, None, None, translate=translate)
    attribute = Attribute(None, title, "", attribute_type, None, None, None, [])
    attribute.attribute_enums = [AttributeEnum(None, index, value, "", translations) for index, (value, translations) in enumerate(enums)]
    item.attribute = attribute
    item.translations = {"sk": {"title": f"{title} (sk)"}}
    return item


@pytest.fixture
def product() -> SimpleNamespace:
    """A Czech report with a translated text, a severity, ticked categories and a CVE, in a Czech product."""
    severity_enums = (("Vysoká", {"sk": {"value": "Vysoká (sk)"}, "en": {"value": "High"}}), ("Nízká", {}))
    category_enums = (("Síť", {"en": {"value": "Network"}}), ("Web", {"sk": {"value": "Web (sk)"}}))
    items = [
        _item(1, "Popis", AttributeType.TEXT, translate=True),
        _item(2, "Závažnost", AttributeType.ENUM, enums=severity_enums),
        _item(3, "Kategorie", AttributeType.MULTI_CHOICE, enums=category_enums),
        _item(4, "CVE", AttributeType.CVE),
    ]
    group = AttributeGroup(5, "Hlavní", "", None, "Sekce", 0, items, translations={"sk": {"title": "Hlavná", "section_title": "Sekcia"}})
    report_type = ReportItemType(None, "Vulnerability Report", "", [group], languages=["cs", "sk"], label_language="cs")
    report_type.id = 9
    report_type.translations = {"sk": {"title": "Správa o zraniteľnosti"}}
    values = ["Útočník může [#ab12cd]", "Vysoká", "Síť\nWeb", "CVE-2026-1"]
    attributes = []
    for attribute_id, (item, value) in enumerate(zip(items, values, strict=True), start=20):
        attribute = ReportItemAttribute(None, value, "", None, 0, None, item.id, item.title)
        attribute.id = attribute_id
        attribute.attribute_group_item = item
        attributes.append(attribute)
    report = ReportItem(7, None, "Kritická chyba", "ZRANITELNOST", None, None, [], [], attributes)
    report.report_item_type = report_type
    report.language = "cs"
    title_row = ReportItemTranslation(language="sk", field="title", value="", version=0)
    title_row.write("Kritická chyba (sk)", report.title, ORIGIN_AI, 1)
    report.translations.append(title_row)
    text_row = ReportItemAttributeTranslation(language="sk", value="", version=0)
    text_row.write("Útočník môže [#ab12cd]", attributes[0].value, ORIGIN_AI, 1)
    attributes[0].translations.append(text_row)
    product_title = ProductTranslation(language="sk", field="title", value="", version=0)
    product_title.write("Bulletin (sk)", "Bulletin", ORIGIN_AI, 1)
    parameter_values = [SimpleNamespace(parameter=SimpleNamespace(key="BODY_TEMPLATE_PATH"), value="b_cz.txt")]
    product_type = SimpleNamespace(
        language="cs",
        language_templates={"sk": {"BODY_TEMPLATE_PATH": "b_sk.txt"}},
        parameter_values=parameter_values,
    )
    return SimpleNamespace(
        title="Bulletin",
        language="cs",
        report_items=[report],
        title_translation_rows=[product_title],
        product_type=product_type,
    )


def _payload() -> dict:
    return {
        "product": {"title": "Bulletin"},
        "parameter_values": [{"parameter": {"key": "BODY_TEMPLATE_PATH"}, "value": "b_cz.txt"}],
        "reports": [
            {
                "id": 7,
                "title": "Kritická chyba",
                "title_prefix": "ZRANITELNOST",
                "attributes": [
                    {"id": 20, "value": "Útočník může [#ab12cd]"},
                    {"id": 21, "value": "Vysoká"},
                    {"id": 22, "value": "Síť\nWeb"},
                    {"id": 23, "value": "CVE-2026-1"},
                ],
            },
        ],
        "report_types": [
            {
                "id": 9,
                "title": "Vulnerability Report",
                "attribute_groups": [
                    {"id": 5, "title": "Hlavní", "attribute_group_items": [{"id": 1, "title": "Popis"}, {"id": 2, "title": "Závažnost"}]},
                ],
            },
        ],
    }


def test_presenter_input_in_slovak_keeps_keys_titles_and_raw_constants(product: SimpleNamespace) -> None:
    payload = content_localizer.localize_presenter_input(_payload(), "sk", product)
    content_localizer.localize_templates(payload, product.product_type, "sk")

    assert payload["product"] == {"title": "Bulletin (sk)", "language": "sk"}
    report = payload["reports"][0]
    assert report["title"] == "Kritická chyba (sk)"
    # No Slovak or English prefix: the original.
    assert report["title_prefix"] == "ZRANITELNOST"
    text, severity, categories, cve = report["attributes"]
    assert text["value"] == "Útočník môže [#ab12cd]"
    assert severity == {"id": 21, "value": "Vysoká", "value_label": "Vysoká (sk)"}
    # Network has no Slovak, so English; Web has Slovak.
    assert categories == {"id": 22, "value": "Síť\nWeb", "value_label": "Network\nWeb (sk)"}
    assert cve == {"id": 23, "value": "CVE-2026-1"}
    report_type = payload["report_types"][0]
    assert (report_type["title"], report_type["label"]) == ("Vulnerability Report", "Správa o zraniteľnosti")
    group = report_type["attribute_groups"][0]
    assert (group["title"], group["label"], group["section_label"]) == ("Hlavní", "Hlavná", "Sekcia")
    assert group["attribute_group_items"][0] == {"id": 1, "title": "Popis", "label": "Popis (sk)", "description_label": "Popis help"}
    assert payload["parameter_values"][0]["value"] == "b_sk.txt"


def test_presenter_input_in_its_own_language_is_the_original(product: SimpleNamespace) -> None:
    payload = content_localizer.localize_presenter_input(_payload(), "cs", product)
    content_localizer.localize_templates(payload, product.product_type, "cs")

    assert payload["product"]["title"] == "Bulletin"
    assert payload["reports"][0]["title"] == "Kritická chyba"
    assert payload["reports"][0]["attributes"][1]["value_label"] == "Vysoká"
    assert payload["parameter_values"][0]["value"] == "b_cz.txt"


def test_without_a_language_the_input_is_unchanged(product: SimpleNamespace) -> None:
    payload = content_localizer.localize_presenter_input(_payload(), None, product)

    assert payload == {**_payload(), "product": {"title": "Bulletin", "language": None}}


def test_an_unsaved_products_titles_come_from_the_form(product: SimpleNamespace) -> None:
    payload = content_localizer.localize_presenter_input(_payload(), "sk", product, {"sk": "Bulletin z formulára"})

    assert payload["product"]["title"] == "Bulletin z formulára"


def test_outdated_translations_are_skipped_when_asked(product: SimpleNamespace) -> None:
    report = product.report_items[0]
    report.title = "Kritická chyba v jádře"

    assert content_localizer.report_title(report, "title", "sk") == "Kritická chyba (sk)"
    assert content_localizer.report_title(report, "title", "sk", skip_outdated=True) == "Kritická chyba v jádře"


def test_a_presenter_without_templates_suits_every_language(product: SimpleNamespace) -> None:
    """A JSON product type has nothing that depends on a language, so nothing falls back."""
    indent = SimpleNamespace(parameter=SimpleNamespace(key="JSON_INDENT"), value="4")
    product.product_type = SimpleNamespace(language=None, language_templates={}, parameter_values=[indent])

    assert content_localizer.language_check(product, "sk")["template_language"] == "sk"
    assert content_localizer.language_check(product, "de")["template_language"] == "de"


def test_the_publish_check_names_what_falls_back(product: SimpleNamespace) -> None:
    report = product.report_items[0]
    report.attributes[0].value = "Útočník může cokoli [#ab12cd]"

    check = content_localizer.language_check(product, "sk")
    assert check["missing"] == []
    assert check["outdated"] == [{"report_item_id": 7, "title": "Kritická chyba", "field": "Popis"}]
    assert check["template_language"] == "sk"

    check = content_localizer.language_check(product, "de")
    assert check["missing"] == [{"id": 7, "title": "Kritická chyba"}]
    assert check["template_language"] == "cs"

    assert content_localizer.language_check(product, "cs")["missing"] == []


# ---- public web ------------------------------------------------------------------------

ADVISORY = "https://example.test/advisory"


@pytest.fixture
def published(product: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The fixture's product as the public web reads it: with an id, a cited link and no author."""
    # A report's own links come from the database; this one has none.
    monkeypatch.setattr(ReportItem, "links", property(lambda _report_item: []))
    product.id = 3
    product.description = "Souhrn [#ab12cd]"
    product.links = [{"key": "ab12cd", "url": ADVISORY}]
    product.created = None
    product.user = None
    return product


def test_the_public_web_shows_a_language_and_keeps_what_it_compares(published: SimpleNamespace) -> None:
    feed = public_web._serialize_product(published, "sk")

    assert (feed["title"], feed["language"], feed["available_languages"]) == ("Bulletin (sk)", "sk", ["cs", "sk"])
    # The product's description is not translated.
    assert feed["description"] == "Souhrn [1]"
    report = feed["report_items"][0]
    assert (report["title"], report["title_prefix"]) == ("Kritická chyba (sk)", "ZRANITELNOST")
    assert (report["type"], report["type_label"]) == ("Vulnerability Report", "Správa o zraniteľnosti")
    text, severity, network, web, cve = report["attributes"]
    # A translated text has its citations rendered like the original.
    assert (text["key"], text["value"], text["label"]) == ("popis", "Útočník môže [1]", "Popis (sk)")
    assert severity == {
        "key": "závažnost",
        "type": "ENUM",
        "value": "Vysoká (sk)",
        "source_value": "Vysoká",
        "description": "",
        "label": "Závažnost (sk)",
    }
    # Network has no Slovak, so English; each ticked value is an entry of its own.
    assert [(entry["value"], entry["source_value"]) for entry in (network, web)] == [("Network", "Síť"), ("Web (sk)", "Web")]
    assert cve == {"key": "cve", "type": "CVE", "value": "CVE-2026-1", "description": "", "label": "CVE (sk)"}


def test_the_public_web_passes_over_outdated_translations(published: SimpleNamespace) -> None:
    report_item = published.report_items[0]
    report_item.title = "Kritická chyba v jádře"
    report_item.attributes[0].value = "Útočník může cokoli [#ab12cd]"

    feed = public_web._serialize_product(published, "sk")

    report = feed["report_items"][0]
    assert report["title"] == "Kritická chyba v jádře"
    assert report["attributes"][0]["value"] == "Útočník může cokoli [1]"
    # Nothing current in Slovak is left, so the reports are shown in Czech.
    assert (feed["language"], feed["available_languages"]) == ("cs", ["cs"])


def test_without_a_language_the_public_web_gets_the_product_as_written(published: SimpleNamespace) -> None:
    feed = public_web._serialize_product(published)

    assert "language" not in feed
    assert "available_languages" not in feed
    assert feed["title"] == "Bulletin"
    report = feed["report_items"][0]
    assert report["title"] == "Kritická chyba"
    assert "type_label" not in report
    assert report["attributes"][1] == {"key": "závažnost", "type": "ENUM", "value": "Vysoká", "description": ""}


def test_reports_of_no_known_language_are_shown_without_naming_one(published: SimpleNamespace) -> None:
    report_item = published.report_items[0]
    report_item.language = None
    report_item.translations.clear()
    report_item.attributes[0].translations.clear()
    published.language = None

    feed = public_web._serialize_product(published, "sk")

    assert (feed["language"], feed["available_languages"]) == (None, [])
    assert feed["report_items"][0]["title"] == "Kritická chyba"


def test_the_shown_language_follows_the_chain_through_what_is_available() -> None:
    assert content_localizer.shown_language("sk", "cs", ["cs", "sk"]) == "sk"
    assert content_localizer.shown_language("de", "cs", ["cs", "en", "sk"]) == "en"
    # The original rather than another translation.
    assert content_localizer.shown_language("de", "cs", ["cs", "sk"]) == "cs"
    assert content_localizer.shown_language("de", None, ["sk"]) == "sk"
    assert content_localizer.shown_language("de", None, []) is None
