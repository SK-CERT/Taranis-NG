"""The filters report templates can use.

Report templates are written by administrators in the GUI and render values that
come from collected sources, so every filter here must cope with missing values
(Jinja passes ``Undefined`` for an absent attribute) and must never mark untrusted
text as safe without sanitizing it first.

``bleach`` is imported lazily, so the renderer (and its tests) work in environments
that have only jinja2, markupsafe and cvss.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from jinja2 import is_undefined
from lib.report import capitalize, fix_spaces, format_iso_date, get_cvss_severity
from lib.report.vulnerability import affected_system, cvss_score, ymd_date
from markupsafe import Markup
from shared.jinja_filters import filter_regex_replace, filter_strfdate, filter_tlp_color, filter_truncate_on_symbol

SAFE_URL_SCHEMES = ("http", "https", "mailto")
RICH_TEXT_TAGS = [
    "a", "b", "blockquote", "br", "code", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i",
    "li", "ol", "p", "pre", "s", "span", "strong", "sub", "sup", "table", "tbody", "td", "th",
    "thead", "tr", "u", "ul",
]  # fmt: skip


def _missing(value: Any) -> bool:  # noqa: ANN401
    return value is None or is_undefined(value)


def single(value: Any) -> Any:  # noqa: ANN401
    """The attribute's value, or its first value when it holds several; None if absent."""
    if _missing(value):
        return None
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    if isinstance(value, dict):
        return next(iter(value), None)
    return value


def as_list(value: Any) -> list:  # noqa: ANN401
    """The attribute's values as a list, however many there are (CWE maps give their keys)."""
    if _missing(value):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        return list(value)
    return [value]


def fix_spaces_filter(value: Any) -> Any:  # noqa: ANN401
    """Collapse runs of spaces and trim; anything that is not text passes through."""
    return fix_spaces(value) if isinstance(value, str) else (None if _missing(value) else value)


def capitalize_first(value: Any) -> Any:  # noqa: ANN401
    """Upper-case only the first letter (Jinja's ``capitalize`` also lowercases the rest)."""
    return capitalize(value) if isinstance(value, str) else (None if _missing(value) else value)


def link_refs(text: Any, links: list[str] | None) -> Any:  # noqa: ANN401
    """Turn [1], [2]... references into links to the product's Links list.

    Returns plain text with ``<a>`` tags in it: always pipe the result into ``clean``.
    """
    if _missing(text) or not text:
        return text
    text = str(text)
    for index, link in enumerate(links or [], start=1):
        text = text.replace(f"[{index}]", f"<a href='{link}' style='text-decoration: none;'>[{index}]</a>")
    return text


def clean(text: Any) -> Markup:  # noqa: ANN401
    """Escape all HTML except ``<a>`` links (as produced by ``link_refs``)."""
    if _missing(text):
        return Markup("")
    from bleach import clean as bleach_clean  # noqa: PLC0415 (optional at import time)
    from bleach import css_sanitizer  # noqa: PLC0415

    sanitizer = css_sanitizer.CSSSanitizer(allowed_css_properties=["text-decoration"])
    # Safe because bleach has removed everything but <a href style>, which is what's rendered.
    return Markup(bleach_clean(str(text), tags=["a"], attributes=["href", "style"], css_sanitizer=sanitizer))  # noqa: S704


def clean_rich(text: Any) -> Markup:  # noqa: ANN401
    """Keep basic formatting (paragraphs, lists, emphasis, tables, links) of rich text; escape the rest."""
    if _missing(text):
        return Markup("")
    from bleach import clean as bleach_clean  # noqa: PLC0415 (optional at import time)

    # Safe because bleach has removed every tag and attribute not in the allow lists.
    return Markup(  # noqa: S704
        bleach_clean(str(text), tags=RICH_TEXT_TAGS, attributes={"a": ["href", "title"]}, protocols=list(SAFE_URL_SCHEMES)),
    )


def safe_url(value: Any) -> str:  # noqa: ANN401
    """The URL if it is http(s), mailto or relative; empty otherwise (no ``javascript:``)."""
    if _missing(value) or not value:
        return ""
    url = str(value).strip()
    scheme = urlsplit(url).scheme.lower()
    return url if not scheme or scheme in SAFE_URL_SCHEMES else ""


def cvss_severity(score: Any) -> str | None:  # noqa: ANN401
    """Critical/High/Medium/Low/None for a CVSS score or vector."""
    return get_cvss_severity(cvss_score(single(score)))


def iso_date(value: Any) -> str:  # noqa: ANN401
    """An ISO 8601 date or datetime as 'D. M. YYYY'; empty when it is not one."""
    try:
        return format_iso_date(None if _missing(value) else str(value))
    except ValueError:
        return ""


def _none_if_missing(function):  # noqa: ANN001, ANN202
    def wrapper(value: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        return None if _missing(value) else function(value, *args, **kwargs)

    wrapper.__doc__ = function.__doc__
    return wrapper


FILTERS = {
    "affected_system": lambda value: affected_system(None if _missing(value) else str(value)),
    "as_list": as_list,
    "capitalize_first": capitalize_first,
    "clean": clean,
    "clean_rich": clean_rich,
    "cvss_score": lambda value: cvss_score(single(value)),
    "cvss_severity": cvss_severity,
    "fix_spaces": fix_spaces_filter,
    "iso_date": iso_date,
    "link_refs": link_refs,
    "regex_replace": _none_if_missing(filter_regex_replace),
    "safe_url": safe_url,
    "single": single,
    "strfdate": filter_strfdate,
    "tlp_color": filter_tlp_color,
    "truncate_on_symbol": _none_if_missing(filter_truncate_on_symbol),
    "ymd_date": lambda value: ymd_date(None if _missing(value) else str(value)),
}
