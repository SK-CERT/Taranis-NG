"""The public feed's templates and its translation catalogs must agree.

public-web carries its own small i18n system - ``conf/i18n/{en,cs,sk}.json`` read
through ``translate_ui`` (the page, its ``interface`` section) and ``translate_report`` (a
report's own phrases, its ``report`` section) - entirely separate from the GUI's catalogs. Nothing checked
that the templates and those files matched, and two bugs of the same shape slipped in:
a key defined in all three catalogs that no template ever asked for
(``homepage_service_description``), and the Czech sentence hardcoded in its place, so
the page showed Czech whatever language was chosen.

These tests close that loop from both ends: every key the templates ask for exists,
every key the catalogs define is asked for, and no user-visible text is written
straight into a template. The built-in report templates (``shared.public_web_templates``)
count too: they ask for phrases with ``t("key")``, which looks in the ``report`` section
first and in ``interface`` second.
"""

import json
import re
from pathlib import Path

import pytest

from shared import public_web_templates

PUBLIC_WEB = Path(__file__).parents[1]
TEMPLATES = PUBLIC_WEB / "lib" / "web" / "templates"
REPORT_TEMPLATES = Path(public_web_templates.__file__).parent
CATALOGS = PUBLIC_WEB / "conf" / "i18n"
REFERENCE_LOCALE = "en"

# translate_ui("key") / translate_ui('key'), in templates and in Python.
TRANSLATE_CALL = re.compile(r"""translate_ui\(\s*['"]([^'"]+)['"]""")
# translate_report("key", report.language) / translate_report('key'): what each catalog section is asked for.
TRANSLATE_REPORT_CALL = re.compile(r"""translate_report\(\s*['"]([^'"]+)['"]""")
SECTION_CALLS = {"interface": TRANSLATE_CALL, "report": TRANSLATE_REPORT_CALL}
# t("key") / t('key'), in the report templates.
REPORT_TEMPLATE_CALL = re.compile(r"""\bt\(\s*['"]([^'"]+)['"]""")

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
    "(CVSS )",
    ", CVSS )",
    "[TLP: ]",
    "CWE- :",
    "CWE (CWE-416)",
    "CVE (CVE-2025-26399)",
    "Max",
    "(9.1, critical...)",
    "(Gitlab, Apple...)",
    # Syndication format, shown as the link's own name
    "RSS",
    "Atom",
    # Vendor and advisory-site names linked from a CVE
    "cve.org ,",
    "cwe.mitre.org",
    "NVD",
    "NVD ,",
    "GitHub ,",
    "CIRCL.LU ,",
    "Debian ,",
    "Ubuntu ,",
    "Red Hat ,",
    "SUSE",
}


def _catalog(locale: str, section: str = "interface") -> dict[str, str]:
    return json.loads((CATALOGS / f"{locale}.json").read_text(encoding="utf-8"))[section]


def _locales() -> list[str]:
    return sorted(path.stem for path in CATALOGS.glob("*.json"))


def _used_keys(section: str = "interface") -> set[str]:
    """Every key the application actually asks for from ``section``."""
    keys: set[str] = set()
    for path in [*TEMPLATES.rglob("*.html"), *(PUBLIC_WEB / "lib").rglob("*.py")]:
        keys |= set(SECTION_CALLS[section].findall(path.read_text(encoding="utf-8")))
    return {key.lower() for key in keys}


# Report phrases no built-in template asks for, kept for the custom templates in core that do: an
# instance whose vulnerability reports list affected systems with their versions (as the fixture
# instance's templates in fixtures/templates/ show) words them with these.
FOR_CUSTOM_TEMPLATES = {"in_versions", "original_version_format"}


def _report_template_keys() -> set[str]:
    """Every key the built-in report templates ask ``t()`` for."""
    keys: set[str] = set()
    for path in REPORT_TEMPLATES.glob("*.html"):
        keys |= set(REPORT_TEMPLATE_CALL.findall(path.read_text(encoding="utf-8")))
    return {key.lower() for key in keys}


def _bare_text(template: Path) -> set[str]:
    """Text a visitor would read that is neither markup, code, nor a substitution."""
    source = SCRIPT_OR_STYLE.sub(" ", template.read_text(encoding="utf-8"))
    source = HTML_TAG.sub(" ", JINJA.sub(" ", source))
    return {" ".join(line.split()) for line in source.splitlines() if HAS_WORD.search(line)}


def test_the_application_asks_for_something() -> None:
    """Guards the regexes themselves: a silent zero would make every other test vacuous."""
    # The report's phrases come mostly from the report templates; the page asks for a few.
    assert len(_used_keys("interface")) > 10
    assert _used_keys("report")
    assert len(_report_template_keys()) > 10


@pytest.mark.parametrize("section", SECTION_CALLS)
@pytest.mark.parametrize("locale", _locales())
def test_every_key_the_templates_use_is_translated(locale: str, section: str) -> None:
    """A missing key renders as None, so the page shows a hole rather than a word."""
    missing = sorted(_used_keys(section) - set(_catalog(locale, section)))
    assert not missing, f"{locale}.json is missing {len(missing)} {section} key(s) the templates ask for: {missing}"


@pytest.mark.parametrize("locale", _locales())
def test_every_key_the_report_templates_use_is_translated(locale: str) -> None:
    """``t()`` falls back to the key itself, so a missing phrase shows as its key."""
    known = set(_catalog(locale, "report")) | set(_catalog(locale))
    missing = sorted(_report_template_keys() - known)
    assert not missing, f"{locale}.json is missing {len(missing)} key(s) the report templates ask for: {missing}"


@pytest.mark.parametrize("section", SECTION_CALLS)
def test_no_catalog_key_is_unreferenced(section: str) -> None:
    """An unused key means the template hardcoded the text instead - the original bug."""
    unused = sorted(set(_catalog(REFERENCE_LOCALE, section)) - _used_keys(section) - _report_template_keys() - FOR_CUSTOM_TEMPLATES)
    assert not unused, (
        f"{len(unused)} {section} key(s) defined but never asked for: {unused}. "
        "Either a template hardcodes the text, or the key is dead and should go."
    )


@pytest.mark.parametrize("section", SECTION_CALLS)
@pytest.mark.parametrize("locale", [loc for loc in _locales() if loc != REFERENCE_LOCALE])
def test_catalogs_do_not_drift_apart(locale: str, section: str) -> None:
    """Every catalogue holds the same key set, so no language quietly loses a phrase."""
    reference, other = set(_catalog(REFERENCE_LOCALE, section)), set(_catalog(locale, section))
    assert other == reference, (
        f"{locale}.json differs from {REFERENCE_LOCALE}.json in {section} - "
        f"missing: {sorted(reference - other)}, extra: {sorted(other - reference)}"
    )


@pytest.mark.parametrize("locale", _locales())
def test_every_catalog_names_the_languages_offered(locale: str) -> None:
    """A report shown in another language says which; every language with a catalog has a name."""
    names = json.loads((CATALOGS / f"{locale}.json").read_text(encoding="utf-8"))["languages"]
    assert sorted(names) == _locales()
    assert all(str(name).strip() for name in names.values())


@pytest.mark.parametrize("section", SECTION_CALLS)
@pytest.mark.parametrize("locale", _locales())
def test_no_translation_is_blank(locale: str, section: str) -> None:
    """A blank value is worse than a missing one: it renders as nothing at all."""
    blank = sorted(key for key, value in _catalog(locale, section).items() if not str(value).strip())
    assert not blank, f"{locale}.json has blank translations: {blank}"


@pytest.mark.parametrize("template", sorted([*TEMPLATES.rglob("*.html"), *REPORT_TEMPLATES.glob("*.html")]), ids=lambda p: p.name)
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


def test_the_phrases_kept_for_custom_templates_are_asked_for_by_one() -> None:
    """Kept only while some custom template asks for them: the fixture instance's do."""
    asked = set()
    for path in (PUBLIC_WEB / "tests" / "fixtures" / "templates").glob("*.html"):
        asked |= set(REPORT_TEMPLATE_CALL.findall(path.read_text(encoding="utf-8")))
    assert asked >= FOR_CUSTOM_TEMPLATES
    assert not FOR_CUSTOM_TEMPLATES & _report_template_keys(), "a built-in asks for it now; drop it from FOR_CUSTOM_TEMPLATES"
