"""The public feed's templates and its translation catalogs must agree.

public-web carries its own small i18n system - ``conf/i18n/{en,cs,sk}.json`` read
through ``translate_ui`` - entirely separate from the GUI's catalogs. Nothing checked
that the templates and those files matched, and two bugs of the same shape slipped in:
a key defined in all three catalogs that no template ever asked for
(``homepage_service_description``), and the Czech sentence hardcoded in its place, so
the page showed Czech whatever language was chosen.

These tests close that loop from both ends: every key the templates ask for exists,
every key the catalogs define is asked for, and no user-visible text is written
straight into a template.
"""

import json
import re
from pathlib import Path

import pytest

PUBLIC_WEB = Path(__file__).parents[1]
TEMPLATES = PUBLIC_WEB / "lib" / "web" / "templates"
CATALOGS = PUBLIC_WEB / "conf" / "i18n"
REFERENCE_LOCALE = "en"

# translate_ui("key") / translate_ui('key'), in templates and in Python.
TRANSLATE_CALL = re.compile(r"""translate_ui\(\s*['"]([^'"]+)['"]""")

# Stripped before looking for stray text: script/style bodies are code, Jinja
# expressions are substitutions, and tags are markup.
SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.DOTALL | re.IGNORECASE)
JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)
HTML_TAG = re.compile(r"<[^>]*>", re.DOTALL)
HAS_WORD = re.compile(r"[A-Za-zÀ-ɏ]{2,}")

# Literals that are deliberately not translated: specification terminology, vendor and
# site names, and example values. These read the same in every language, so translating
# them would be wrong rather than merely unnecessary.
#
# Add to this list ONLY for another such literal. Real UI prose belongs in the catalogs -
# that is the mistake this test exists to catch.
ALLOWED_LITERALS = {
    # CVE/CWE/CVSS specification terms and the example values shown beside them
    "CVSS ( )",
    "CVSS:",
    "CWE- :",
    "CWE (CWE-416)",
    "CVE (CVE-2025-26399)",
    "Max",
    "(9.1, critical...)",
    "(Gitlab, Apple...)",
    # Syndication format, shown as the link's own name
    "RSS",
    # Vendor and advisory-site names linked from a CVE
    "cve.org ,",
    "cwe.mitre.org",
    "NVD ,",
    "GitHub ,",
    "CIRCL.LU ,",
    "Debian ,",
    "Ubuntu ,",
    "Red Hat ,",
    "SUSE",
    # Fragment of a paginated URL, not prose
    "/ page=",
}


def _catalog(locale: str) -> dict[str, str]:
    return json.loads((CATALOGS / f"{locale}.json").read_text(encoding="utf-8"))["interface"]


def _locales() -> list[str]:
    return sorted(path.stem for path in CATALOGS.glob("*.json"))


def _used_keys() -> set[str]:
    """Every key the application actually asks ``translate_ui`` for."""
    keys: set[str] = set()
    for path in [*TEMPLATES.rglob("*.html"), *(PUBLIC_WEB / "lib").rglob("*.py")]:
        keys |= set(TRANSLATE_CALL.findall(path.read_text(encoding="utf-8")))
    return {key.lower() for key in keys}


def _bare_text(template: Path) -> set[str]:
    """Text a visitor would read that is neither markup, code, nor a substitution."""
    source = SCRIPT_OR_STYLE.sub(" ", template.read_text(encoding="utf-8"))
    source = HTML_TAG.sub(" ", JINJA.sub(" ", source))
    return {" ".join(line.split()) for line in source.splitlines() if HAS_WORD.search(line)}


def test_the_application_asks_for_something() -> None:
    """Guards the regex itself: a silent zero would make every other test vacuous."""
    assert len(_used_keys()) > 10


@pytest.mark.parametrize("locale", _locales())
def test_every_key_the_templates_use_is_translated(locale: str) -> None:
    """A missing key renders as None, so the page shows a hole rather than a word."""
    missing = sorted(_used_keys() - set(_catalog(locale)))
    assert not missing, f"{locale}.json is missing {len(missing)} key(s) the templates ask for: {missing}"


def test_no_catalog_key_is_unreferenced() -> None:
    """An unused key means the template hardcoded the text instead - the original bug."""
    unused = sorted(set(_catalog(REFERENCE_LOCALE)) - _used_keys())
    assert not unused, (
        f"{len(unused)} key(s) defined but never asked for: {unused}. Either a template hardcodes the text, or the key is dead and should go."
    )


@pytest.mark.parametrize("locale", [loc for loc in _locales() if loc != REFERENCE_LOCALE])
def test_catalogs_do_not_drift_apart(locale: str) -> None:
    """Every catalogue holds the same key set, so no language quietly loses a phrase."""
    reference, other = set(_catalog(REFERENCE_LOCALE)), set(_catalog(locale))
    assert other == reference, (
        f"{locale}.json differs from {REFERENCE_LOCALE}.json - missing: {sorted(reference - other)}, extra: {sorted(other - reference)}"
    )


@pytest.mark.parametrize("locale", _locales())
def test_no_translation_is_blank(locale: str) -> None:
    """A blank value is worse than a missing one: it renders as nothing at all."""
    blank = sorted(key for key, value in _catalog(locale).items() if not str(value).strip())
    assert not blank, f"{locale}.json has blank translations: {blank}"


@pytest.mark.parametrize("template", sorted(TEMPLATES.rglob("*.html")), ids=lambda p: p.name)
def test_templates_hold_no_untranslated_prose(template: Path) -> None:
    """User-visible text belongs in the catalogs, not written into the markup.

    This is the check that would have caught the hardcoded Czech sentence on the
    homepage, and the English "at" beside each CVE link.
    """
    stray = sorted(_bare_text(template) - ALLOWED_LITERALS)
    assert not stray, (
        f"{template.name} contains text that is not translated: {stray}. "
        f"Move it into conf/i18n/*.json and render it with translate_ui(), or - if it is "
        f"a proper noun or specification term - add it to ALLOWED_LITERALS here."
    )
