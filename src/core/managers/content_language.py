"""Languages of report content: validation of language codes and of label translations.

Content languages are ISO 639-1 codes (``en``, ``cs``, ``sk`` ...), the same list the
``CONTENT_DEFAULT_LANGUAGE`` setting offers. A report is written in one of them and its report
type lists the others it is translated into.

Only text attributes are translated per report; everything else (numbers, dates, CVEs, choice
constants ...) is the same in every language.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pycountry

if TYPE_CHECKING:
    from collections.abc import Iterable

# Attribute types whose values a report translates (when the report type ticks Translate).
TRANSLATABLE_TYPES = ("STRING", "TEXT", "RICH_TEXT")
# Rich text holds HTML, which a translation must keep intact.
HTML_TYPES = ("RICH_TEXT",)

# The labels of a report type that have language variants, per level.
TYPE_LABEL_FIELDS = ("title", "description")
GROUP_LABEL_FIELDS = ("title", "description", "section_title")
ITEM_LABEL_FIELDS = ("title", "description")


def is_language(code: object) -> bool:
    """Tell whether ``code`` is an ISO 639-1 language code.

    Args:
        code (object): The candidate.

    Returns:
        bool: True for a known two-letter code, in lower case.
    """
    if not isinstance(code, str) or len(code) != 2 or code != code.lower():  # noqa: PLR2004 - ISO 639-1 codes are two letters
        return False
    try:
        return pycountry.languages.get(alpha_2=code) is not None
    except KeyError:  # older pycountry raises instead of returning None
        return False


def language_name(code: str | None) -> str:
    """The English name of a language, for prompts and messages.

    Args:
        code (str | None): ISO 639-1 code.

    Returns:
        str: The name ("Czech"), the code itself when unknown, or "the source language" for None.
    """
    if not code:
        return "the source language"
    try:
        language = pycountry.languages.get(alpha_2=code)
    except KeyError:
        language = None
    return language.name if language is not None else code


def clean_language(code: object) -> str | None:
    """Validate one language code; empty means "not set".

    Args:
        code (object): The submitted value.

    Returns:
        str | None: The code, or None when nothing was given.

    Raises:
        ValueError: If a value was given that is not an ISO 639-1 code.
    """
    if code is None or code == "":
        return None
    if not is_language(code):
        msg = f"Unknown language code: {code}"
        raise ValueError(msg)
    return code


def clean_languages(codes: Iterable[object] | None) -> list[str]:
    """Validate a list of language codes, keeping their order and dropping repeats.

    Args:
        codes (Iterable[object] | None): The submitted codes.

    Returns:
        list[str]: The codes.

    Raises:
        ValueError: If one of them is not an ISO 639-1 code.
    """
    result: list[str] = []
    for code in codes or []:
        language = clean_language(code)
        if language is not None and language not in result:
            result.append(language)
    return result


def clean_label_translations(translations: object, fields: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """Validate label variants, ``{language: {field: text}}``, keeping only known fields and texts.

    Args:
        translations (object): The submitted variants.
        fields (tuple[str, ...]): The label fields this level has.

    Returns:
        dict[str, dict[str, str]]: The variants without empty texts and without empty languages.

    Raises:
        ValueError: If the shape is wrong or a language is not an ISO 639-1 code.
    """
    if translations is None:
        return {}
    if not isinstance(translations, dict):
        msg = "Label translations must map languages to texts"
        raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
    result: dict[str, dict[str, str]] = {}
    for code, texts in translations.items():
        language = clean_language(code)
        if language is None or not isinstance(texts, dict):
            continue
        kept = {field: text for field, text in texts.items() if field in fields and isinstance(text, str) and text.strip()}
        if kept:
            result[language] = kept
    return result


# Fields of a choice constant (attribute_enum) that have language variants.
ENUM_TRANSLATION_FIELDS = ("value", "description")

# Attribute types whose constants have language variants.
CONSTANT_TYPES = ("RADIO", "ENUM", "MULTI_CHOICE")

# Presenter parameters holding a template path end with this; only they vary per language.
TEMPLATE_SUFFIX = ("_TEMPLATE_PATH", "_FILE_NAME")


def clean_enum_translations(translations: object) -> dict[str, dict[str, str]] | None:
    """Validate the language variants of a choice constant, ``{language: {value, description}}``.

    Args:
        translations (object): The submitted variants; None when the client sent none.

    Returns:
        dict[str, dict[str, str]] | None: The variants without empty texts, or None for "not sent".

    Raises:
        ValueError: If the shape is wrong or a language is not an ISO 639-1 code.
    """
    if translations is None:
        return None
    return clean_label_translations(translations, ENUM_TRANSLATION_FIELDS)


def clean_language_templates(templates: object, template_keys: Iterable[str]) -> dict[str, dict[str, str]]:
    """Validate a product type's per-language templates, ``{language: {PARAM_TEMPLATE_PATH: path}}``.

    Args:
        templates (object): The submitted overrides.
        template_keys (Iterable[str]): The template parameters the presenter has.

    Returns:
        dict[str, dict[str, str]]: The overrides without empty paths and without empty languages.

    Raises:
        ValueError: If the shape is wrong, a language is not an ISO 639-1 code, or a key is not
            one of the presenter's template parameters.
    """
    if templates is None:
        return {}
    if not isinstance(templates, dict):
        msg = "Language templates must map languages to template paths"
        raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
    allowed = set(template_keys)
    result: dict[str, dict[str, str]] = {}
    for code, paths in templates.items():
        language = clean_language(code)
        if language is None:
            continue
        if not isinstance(paths, dict):
            msg = "Language templates must map languages to template paths"
            raise ValueError(msg)  # noqa: TRY004 - callers report ValueError as a bad request
        unknown = sorted(key for key in paths if key not in allowed)
        if unknown:
            msg = f"Not a template parameter of this presenter: {', '.join(unknown)}"
            raise ValueError(msg)
        kept = {key: path.strip() for key, path in paths.items() if isinstance(path, str) and path.strip()}
        if kept:
            result[language] = kept
    return result
