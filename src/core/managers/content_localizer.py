"""Rendering report content in a language: the fallback chain, templates, and presenter input.

Every text is looked up in the requested language, then English, then the language it was written
in. A language that *is* the one the text was written in gives the text itself, so an English
translation never replaces the original. A source whose language is not set is only the last
resort. The public web passes over English (``via_english=False``): there the language asked for is
the page's, picked by the visitor, so a report not translated into it stays as written.

What templates and the public web compare - attribute keys, the report type's title, the raw value
of a choice constant - never changes: translations arrive as extra fields (``value_label``,
``label``, ``description_label``, ``section_label``) next to the originals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from managers import content_language
from model.translation import PRODUCT_FIELDS, TITLE_FIELDS

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from model.product import Product
    from model.report_item import ReportItem

FALLBACK_LANGUAGE = "en"


def language_chain(requested: str | None, source: str | None, *, via_english: bool = True) -> list[str]:
    """The languages to look in, in order: requested, English, the source.

    Args:
        requested (str | None): The language asked for.
        source (str | None): The language the text is written in, if known.
        via_english (bool): Look in English before the source; off, only the two.

    Returns:
        list[str]: The chain without repeats and without unknown languages.
    """
    chain: list[str] = []
    for language in (requested, FALLBACK_LANGUAGE if via_english else None, source):
        if language and language not in chain:
            chain.append(language)
    return chain


def resolve(
    requested: str | None,
    source: str | None,
    original: str | None,
    lookup: Callable[[str], str | None],
    *,
    via_english: bool = True,
) -> tuple[str, str | None]:
    """The text to show for ``requested``, and the language it is in.

    Args:
        requested (str | None): The language asked for.
        source (str | None): The language ``original`` is written in, if known.
        original (str | None): The text as written.
        lookup (Callable[[str], str | None]): The usable translation into a language, or None.
        via_english (bool): Fall back to English before the original (see :func:`language_chain`).

    Returns:
        tuple[str, str | None]: The text, and its language (None for an original of unknown language).
    """
    for language in language_chain(requested, source, via_english=via_english):
        if language == source:
            return original or "", source
        translated = lookup(language)
        if translated:
            return translated, language
    return original or "", source


def _row_lookup(rows: list, source: str | None, *, skip_outdated: bool, field: str | None = None) -> Callable[[str], str | None]:
    """A lookup over translation rows (of one field, when given)."""

    def lookup(language: str) -> str | None:
        for row in rows:
            if row.language != language or (field is not None and row.field != field) or not row.value:
                continue
            if skip_outdated and row.is_outdated(source):
                return None
            return row.value
        return None

    return lookup


def _label_lookup(translations: Mapping[str, Mapping[str, str]] | None, field: str) -> Callable[[str], str | None]:
    return lambda language: (translations or {}).get(language, {}).get(field) or None


def report_title(report_item: ReportItem, field: str, requested: str | None, *, skip_outdated: bool = False, via_english: bool = True) -> str:
    """The report's name or name prefix in ``requested`` (see the module's fallback rule).

    Args:
        report_item (ReportItem): The report.
        field (str): "title" or "title_prefix".
        requested (str | None): The language asked for.
        skip_outdated (bool): Pass over translations whose source changed since.
        via_english (bool): Fall back to English before the original.

    Returns:
        str: The text.
    """
    original = getattr(report_item, field)
    lookup = _row_lookup(report_item.translations, original, skip_outdated=skip_outdated, field=field)
    return resolve(requested, report_item.language, original, lookup, via_english=via_english)[0]


def attribute_value(
    report_item: ReportItem,
    attribute: object,
    requested: str | None,
    *,
    skip_outdated: bool = False,
    via_english: bool = True,
) -> str:
    """A translatable attribute's value in ``requested``; other attributes keep their value.

    Args:
        report_item (ReportItem): The report the value belongs to.
        attribute (ReportItemAttribute): The value.
        requested (str | None): The language asked for.
        skip_outdated (bool): Pass over translations whose source changed since.
        via_english (bool): Fall back to English before the original.

    Returns:
        str: The text.
    """
    group_item = attribute.attribute_group_item
    if group_item is None or not group_item.is_translated:
        return attribute.value
    lookup = _row_lookup(attribute.translations, attribute.value, skip_outdated=skip_outdated)
    return resolve(requested, report_item.language, attribute.value, lookup, via_english=via_english)[0]


def constant_label(
    value: str | None,
    constants: Mapping[str, Mapping],
    requested: str | None,
    source: str | None,
    *,
    via_english: bool = True,
) -> str | None:
    """The label of a choice constant in ``requested``; MULTI_CHOICE values are newline-joined.

    Args:
        value (str | None): The stored value (one constant, or several joined by newlines).
        constants (Mapping[str, Mapping]): Constant value -> its translations ``{language: {"value": ...}}``.
        requested (str | None): The language asked for.
        source (str | None): The language the constants are written in (the report type's label language).
        via_english (bool): Fall back to English before the original.

    Returns:
        str | None: The label(s), joined like the value; None for no value.
    """
    if value is None:
        return None
    parts = value.split("\n")
    labels = [
        resolve(requested, source, part, _label_lookup(constants.get(part, {}), "value"), via_english=via_english)[0] if part else part
        for part in parts
    ]
    return "\n".join(labels)


def label(
    translations: Mapping[str, Mapping[str, str]] | None,
    field: str,
    original: str | None,
    requested: str | None,
    source: str | None,
    *,
    via_english: bool = True,
) -> str:
    """A report type label (name, description, section title) in ``requested``.

    Args:
        translations (Mapping[str, Mapping[str, str]] | None): The level's label variants.
        field (str): Which label.
        original (str | None): The label as written.
        requested (str | None): The language asked for.
        source (str | None): The language the labels are written in, if stated.
        via_english (bool): Fall back to English before the original.

    Returns:
        str: The label.
    """
    return resolve(requested, source, original, _label_lookup(translations, field), via_english=via_english)[0]


def product_text(
    product: Product,
    field: str,
    requested: str | None,
    translations: Mapping[str, Mapping[str, str]] | None = None,
    *,
    skip_outdated: bool = False,
    via_english: bool = True,
) -> tuple[str, str | None]:
    """The product's title or description in ``requested`` and the language it is in.

    Args:
        product (Product): The product.
        field (str): ``title`` or ``description``.
        requested (str | None): The language asked for.
        translations (Mapping[str, Mapping[str, str]] | None): Texts per language and field of a
            product not saved yet; a saved one uses its stored translations.
        skip_outdated (bool): Pass over translations whose source changed since.
        via_english (bool): Fall back to English before the original.

    Returns:
        tuple[str, str | None]: The text and its language.
    """
    original = getattr(product, field) or ""
    if translations is not None:
        return resolve(
            requested,
            product.language,
            original,
            lambda language: (translations.get(language) or {}).get(field) or None,
            via_english=via_english,
        )
    lookup = _row_lookup(product.translation_rows, original, skip_outdated=skip_outdated, field=field)
    return resolve(requested, product.language, original, lookup, via_english=via_english)


def report_languages(report_item: ReportItem) -> list[str]:
    """The languages a report can be read in: its own, and those it has a current translation into.

    These are the translations the public web shows, which passes over those whose source changed
    since.

    Args:
        report_item (ReportItem): The report.

    Returns:
        list[str]: Sorted ISO 639-1 codes; empty when the report has no language set.
    """
    languages: set[str] = set()
    if report_item.language:
        languages.add(report_item.language)
    languages.update(row.language for row in report_item.translations if row.value and not row.is_outdated(getattr(report_item, row.field)))
    languages.update(
        row.language
        for attribute in report_item.attributes
        if attribute.attribute_group_item is not None and attribute.attribute_group_item.is_translated
        for row in attribute.translations
        if row.value and not row.is_outdated(attribute.value)
    )
    return sorted(languages)


def available_languages(product: Product) -> list[str]:
    """The languages a product's reports can be read in, for readers choosing one (the public web).

    The product's title alone does not make a language available.

    Args:
        product (Product): The product.

    Returns:
        list[str]: Sorted ISO 639-1 codes; empty when no report has a language set.
    """
    return sorted({language for report_item in product.report_items for language in report_languages(report_item)})


def shown_language(requested: str | None, source: str | None, available: list[str], *, via_english: bool = True) -> str | None:
    """The language a product or a report is shown in when ``requested``: the first of the chain it is available in.

    Args:
        requested (str | None): The language asked for.
        source (str | None): The product's or report's own language, if set.
        available (list[str]): What :func:`available_languages` or :func:`report_languages` gives.
        via_english (bool): Prefer English to the source (see :func:`language_chain`).

    Returns:
        str | None: The language, or None when no language of the content is known.
    """
    chain = language_chain(requested, source, via_english=via_english)
    return next((language for language in chain if language in available), available[0] if available else None)


def resolve_language_templates(
    default_params: Mapping[str, str],
    language_templates: Mapping[str, Mapping[str, str]] | None,
    default_language: str | None,
    requested: str | None,
    translatable_keys: Iterable[str],
) -> tuple[dict[str, str], str | None]:
    """The template paths to render ``requested`` with, and the language they are written for.

    The chain is requested, English, then the default set. The default set counts as
    ``default_language`` when that is stated. Template paths and file-name templates vary; an
    override missing a value inherits the default one. Only parameters marked translatable can be
    overridden.

    Args:
        default_params (Mapping[str, str]): The product type's parameters (key -> value).
        language_templates (Mapping[str, Mapping[str, str]] | None): Overrides per language.
        default_language (str | None): The language of the default templates, if stated.
        requested (str | None): The language rendered.
        translatable_keys (Iterable[str]): Parameter keys enabled for language-specific values.

    Returns:
        tuple[dict[str, str], str | None]: The parameters to use, and the templates' language.
    """
    params = dict(default_params)
    allowed = set(translatable_keys)
    for language in language_chain(requested, None):
        if language == default_language:
            return params, default_language
        overrides = (language_templates or {}).get(language)
        if overrides:
            params.update({key: path for key, path in overrides.items() if key in allowed and path})
            return params, language
    return params, default_language


def constants_of(report_types: Iterable) -> dict[int, dict[str, Mapping]]:
    """Group item id -> {constant value -> its translations}, for the choice attributes of ``report_types``."""
    constants: dict[int, dict[str, Mapping]] = {}
    for report_type in report_types:
        for group in report_type.attribute_groups:
            for item in group.attribute_group_items:
                attribute = item.attribute
                if attribute is None or attribute.type is None or attribute.type.name not in content_language.CONSTANT_TYPES:
                    continue
                constants[item.id] = {enum.value: enum.translations or {} for enum in attribute.attribute_enums}
    return constants


def localize_presenter_input(
    payload: dict,
    language: str | None,
    product: Product,
    product_translations: Mapping[str, Mapping[str, str]] | None = None,
) -> dict:
    """Put a dumped presenter input in ``language``, keeping every key and raw value.

    - The product's title and description and the reports' names, prefixes and translatable texts
      are replaced by their translations (free text is never compared in templates).
    - Choice constants keep their raw value and gain ``value_label``.
    - Report types, groups and items keep their titles and gain ``label`` / ``description_label``
      (and ``section_label`` for groups).
    - The product gains ``language``.

    Args:
        payload (dict): ``PresenterInputSchema().dump()`` of the product.
        language (str | None): The language to render; None leaves the content as written.
        product (Product): The product the payload was made from (saved or not).
        product_translations (Mapping[str, Mapping[str, str]] | None): Texts per language and field
            of a product not saved yet.

    Returns:
        dict: The payload, changed in place.
    """
    payload.setdefault("product", {})["language"] = language
    if not language:
        return payload

    for field in PRODUCT_FIELDS:
        payload["product"][field] = product_text(product, field, language, product_translations)[0]

    report_types = {item.report_item_type.id: item.report_item_type for item in product.report_items if item.report_item_type}
    constants = constants_of(report_types.values())
    reports = {report_item.id: report_item for report_item in product.report_items}

    for report_data in payload.get("reports") or []:
        report_item = reports.get(report_data.get("id"))
        if report_item is None:
            continue
        for field in TITLE_FIELDS:
            report_data[field] = report_title(report_item, field, language)
        label_language = report_item.report_item_type.label_language if report_item.report_item_type else None
        attributes = {attribute.id: attribute for attribute in report_item.attributes}
        for attribute_data in report_data.get("attributes") or []:
            attribute = attributes.get(attribute_data.get("id"))
            if attribute is None:
                continue
            attribute_data["value"] = attribute_value(report_item, attribute, language)
            item_constants = constants.get(attribute.attribute_group_item_id)
            if item_constants is not None:
                attribute_data["value_label"] = constant_label(attribute.value, item_constants, language, label_language)

    for type_data in payload.get("report_types") or []:
        report_type = report_types.get(type_data.get("id"))
        if report_type is None:
            continue
        source = report_type.label_language
        type_data["label"] = label(report_type.translations, "title", report_type.title, language, source)
        type_data["description_label"] = label(report_type.translations, "description", report_type.description, language, source)
        groups = {group.id: group for group in report_type.attribute_groups}
        for group_data in type_data.get("attribute_groups") or []:
            group = groups.get(group_data.get("id"))
            if group is None:
                continue
            group_data["label"] = label(group.translations, "title", group.title, language, source)
            group_data["description_label"] = label(group.translations, "description", group.description, language, source)
            group_data["section_label"] = label(group.translations, "section_title", group.section_title, language, source)
            items = {item.id: item for item in group.attribute_group_items}
            for item_data in group_data.get("attribute_group_items") or []:
                item = items.get(item_data.get("id"))
                if item is None:
                    continue
                item_data["label"] = label(item.translations, "title", item.title, language, source)
                item_data["description_label"] = label(item.translations, "description", item.description, language, source)
    return payload


def localize_templates(payload: dict, product_type: object, language: str | None) -> str | None:
    """Swap the template paths in a dumped presenter input for those of ``language``.

    Args:
        payload (dict): The dumped presenter input.
        product_type (ProductType): The product type rendering it.
        language (str | None): The language rendered.

    Returns:
        str | None: The language of the templates used.
    """
    values = payload.get("parameter_values") or []
    defaults = {value["parameter"]["key"]: value.get("value") for value in values if value.get("parameter")}
    translatable_keys = [parameter["key"] for value in values if (parameter := value.get("parameter")) and parameter.get("translate")]
    params, template_language = resolve_language_templates(
        defaults,
        product_type.language_templates,
        product_type.language,
        language,
        translatable_keys,
    )
    for value in values:
        key = (value.get("parameter") or {}).get("key")
        if key in params:
            value["value"] = params[key]
    return template_language


def language_check(product: Product, language: str | None) -> dict:
    """What rendering ``product`` in ``language`` will fall back on, for the publish notices.

    Args:
        product (Product): The product (saved or not).
        language (str | None): The language to render.

    Returns:
        dict: ``missing`` - reports with nothing in that language (English or the original will
            be shown); ``outdated`` - translations whose source changed since, per report and
            field; ``template_language`` - the language of the templates that will be used (None:
            the default ones, whose language is not set; the language itself when the presenter
            uses no templates, as JSON does, since nothing then depends on a language).
    """
    missing: list[dict] = []
    outdated: list[dict] = []
    for report_item in product.report_items:
        if not language or language == report_item.language:
            continue
        rows = [row for row in report_item.translations if row.language == language]
        attribute_rows = [
            (attribute, row)
            for attribute in report_item.attributes
            if attribute.attribute_group_item is not None and attribute.attribute_group_item.is_translated
            for row in attribute.translations
            if row.language == language
        ]
        if not rows and not attribute_rows:
            missing.append({"id": report_item.id, "title": report_item.title})
            continue
        outdated.extend(
            {"report_item_id": report_item.id, "title": report_item.title, "field": row.field}
            for row in rows
            if row.value and row.is_outdated(getattr(report_item, row.field))
        )
        outdated.extend(
            {"report_item_id": report_item.id, "title": report_item.title, "field": attribute.attribute_group_item.title}
            for attribute, row in attribute_rows
            if row.value and row.is_outdated(attribute.value)
        )

    product_type = product.product_type
    template_language = None
    if product_type is not None:
        defaults = {value.parameter.key: value.value for value in product_type.parameter_values if value.parameter}
        translatable_keys = [value.parameter.key for value in product_type.parameter_values if value.parameter and value.parameter.translate]
        if translatable_keys:
            template_language = resolve_language_templates(
                defaults,
                product_type.language_templates,
                product_type.language,
                language,
                translatable_keys,
            )[1]
        else:
            template_language = language
    return {"missing": missing, "outdated": outdated, "template_language": template_language}
