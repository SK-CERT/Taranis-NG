"""Shared public-web web helpers: language resolution, translations, and HTML sanitization."""

from bleach import clean, css_sanitizer
from flask import g
from lib import config
from lib.report.vulnerability_report import VulnerabilityReport
from markupsafe import Markup


def current_language() -> str:
    """The language chosen for the current request.

    See ``lib/web/site.py``; falls back to the shipped default language outside
    of a request context.
    """
    site = getattr(g, "site", None)
    return site.language if site is not None else config.default_language()


def translate_report(report: VulnerabilityReport, key: str) -> str:  # noqa: ARG001
    """Get the phrase for ``key`` from the ``report`` section of the conf/i18n translations.

    Uses the language chosen for the current request.
    """
    return config.get_translations(current_language())["report"].get(key.lower())


def translate_ui(key: str) -> str:
    """Get the phrase for ``key`` from the ``interface`` section of conf/i18n.

    Uses the language chosen for the current request.
    """
    return config.get_translations(current_language())["interface"].get(key.lower())


def transform_link_references(text: str, links: list[str]) -> str:
    """Transforms references to links ([1], [2]...) to <a>...</a>."""
    for i, link in enumerate(links, start=1):
        text = text.replace(f"[{i}]", f"<a href='{link}' style='text-decoration: none;'>[{i}]</a>")
    return text


def do_clean(text: str) -> str:
    """Strip all HTML tags except ``<a>`` to prevent XSS.

    The description comes from an external source (Taranis), so it cannot be
    trusted. A CSS sanitizer is needed to allow the ``style`` attribute.
    """
    sanitizer = css_sanitizer.CSSSanitizer(allowed_css_properties=["text-decoration"])
    # Safe because warning tags are removed by bleach, which is what's being rendered.
    return Markup(clean(text, tags=["a"], attributes=["href", "style"], css_sanitizer=sanitizer))  # noqa: S704
