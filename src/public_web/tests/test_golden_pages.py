"""The template-driven pages must look exactly like the hand-written ones did.

The golden files under ``golden/`` were recorded from the original, hardcoded
vulnerability templates before the move to configurable report templates. The
built-in vulnerability templates must keep reproducing them. Pages are compared as
a canonical token stream (tags, sorted attributes, whitespace-collapsed text), so
re-indenting a template or switching attribute quotes does not count as a change,
while any difference a visitor could see does.

Re-record (only when a visible change is intended): ``UPDATE_GOLDEN=1 pytest tests/test_golden_pages.py``.
Three later changes were edited in by hand instead, to keep the recordings: ``<html lang>``
names the page's language (it was always "cs"), a language picked with ``?lang=``
stays in the page's links, and the homepage and the report page have a language menu.
"""

from __future__ import annotations

import difflib
import os
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import pytest

GOLDEN = Path(__file__).parent / "golden"
UPDATE = os.environ.get("UPDATE_GOLDEN") == "1"

HTML_PAGES = {
    "homepage": "/",
    "homepage_search": "/?search=tomcat",
    "homepage_search_empty": "/?search=nothing-matches-this",
    "report_101": "/reports/101",
    "report_101_items_2": "/reports/101?items=2",
    "report_101_cs": "/reports/101?lang=cs",
    "report_102": "/reports/102",
}


def _collapse(text: str) -> str:
    return " ".join(text.split())


class _Canonical(HTMLParser):
    """Flatten HTML into comparable lines."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        rendered = " ".join(f'{name}="{_collapse(value or "")}"' for name, value in sorted(attrs))
        self.lines.append(f"<{tag} {rendered}>".replace(" >", ">"))

    def handle_endtag(self, tag: str) -> None:
        self.lines.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if text := _collapse(data):
            self.lines.append(text)


def canonical_html(html: str) -> list[str]:
    """The page as a list of tag/text lines, independent of formatting."""
    parser = _Canonical()
    parser.feed(html)
    parser.close()
    return parser.lines


def canonical_rss(xml: str) -> list[str]:
    """The feed's channel and items, without the build timestamp."""
    channel = ET.fromstring(xml).find("channel")  # noqa: S314 (our own output)
    lines = [f"{tag}: {_collapse(channel.findtext(tag) or '')}" for tag in ("title", "link", "description")]
    for item in channel.findall("item"):
        lines.extend(f"item.{tag}: {_collapse(item.findtext(tag) or '')}" for tag in ("title", "link", "guid"))
        # The description is plain text; its line breaks matter less than its words.
        lines.append(f"item.description: {_collapse(item.findtext('description') or '')}")
    return lines


def _compare(name: str, actual: str, canonical: callable, suffix: str) -> None:
    golden = GOLDEN / f"{name}.{suffix}"
    if UPDATE:
        GOLDEN.mkdir(exist_ok=True)
        golden.write_text(actual, encoding="utf-8")
        pytest.skip(f"recorded {golden.name}")
    expected = canonical(golden.read_text(encoding="utf-8"))
    got = canonical(actual)
    if expected != got:
        diff = "\n".join(difflib.unified_diff(expected, got, "golden", "rendered", lineterm="", n=3))
        pytest.fail(f"{name} differs from its golden file:\n{diff}")


@pytest.mark.parametrize(("name", "path"), HTML_PAGES.items(), ids=HTML_PAGES.keys())
def test_page_matches_golden(site_client, name: str, path: str) -> None:  # noqa: ANN001
    """Each page renders as it did before the templates became configurable."""
    response = site_client.client.get(path, headers={"Host": "localhost"})
    assert response.status_code == 200, response.text[:2000]
    _compare(name, response.text, canonical_html, "html")


def test_rss_matches_golden(site_client) -> None:  # noqa: ANN001
    """The RSS items keep their titles, links and plain-text descriptions."""
    response = site_client.client.get("/rss", headers={"Host": "localhost"})
    assert response.status_code == 200
    _compare("rss", response.text, canonical_rss, "xml")


def test_amber_report_is_not_served(site_client) -> None:  # noqa: ANN001
    """A product whose TLP is above CLEAR is never displayed, not even by direct URL."""
    response = site_client.client.get("/reports/103", headers={"Host": "localhost"})
    assert response.status_code == 404
    assert "Secret issue" not in response.text


def test_a_product_preset_without_a_template_shows_vulnerability_reports_only(site_client) -> None:  # noqa: ANN001
    """The disinformation product's preset has no report template, so it stays hidden."""
    homepage = site_client.client.get("/", headers={"Host": "localhost"}).text
    assert "Disinformation overview" not in homepage
    assert site_client.client.get("/reports/201", headers={"Host": "localhost"}).status_code == 404


def test_a_product_preset_template_shows_its_other_products(site_client) -> None:  # noqa: ANN001
    """Giving the product preset a report template is what puts non-vulnerability products on the web."""
    site_client.fake.templates = [
        {
            "id": 1,
            "name": "Disinformation",
            "product_preset_id": 20,
            "report_item_type_id": None,
            "source": '{% extends "builtin/product_base.html" %}',
            "require_tlp_clear": True,
        },
    ]

    response = site_client.client.get("/reports/201", headers={"Host": "localhost"})

    assert response.status_code == 200
    assert "Disinformation overview" in response.text


def test_canonical_form_ignores_formatting_only() -> None:
    """Guards the canonicalizer itself: formatting differences compare equal, content does not."""
    assert canonical_html("<p class='a  b'>\n  x   y </p>") == canonical_html('<p class="a b">x y</p>')
    assert canonical_html("<p>x</p>") != canonical_html("<p>y</p>")


def test_with_the_builtin_product_template_off_only_presets_with_their_own_are_shown(site_client) -> None:  # noqa: ANN001
    """Switched off in core, the built-in vulnerability report template no longer puts products on the web."""
    site_client.fake.disabled_builtins = ["builtin/product_vulnerability.html"]
    site_client.fake.templates = [
        {
            "id": 1,
            "name": "Disinformation",
            "product_preset_id": 20,
            "report_item_type_id": None,
            "source": '{% extends "builtin/product_base.html" %}',
            "require_tlp_clear": True,
        },
    ]

    homepage = site_client.client.get("/", headers={"Host": "localhost"}).text

    assert "OpenSSL denial of service" not in homepage
    assert "Disinformation overview" in homepage
    assert site_client.client.get("/reports/102", headers={"Host": "localhost"}).status_code == 404


def test_a_product_none_of_whose_items_has_a_template_is_not_shown(site_client) -> None:  # noqa: ANN001
    """Every built-in off: the preset's own template is not enough while none of the product's items has one."""
    site_client.fake.disabled_builtins = [
        "builtin/product_vulnerability.html",
        "builtin/item_vulnerability.html",
        "builtin/item_generic.html",
    ]
    site_client.fake.templates = [
        {
            "id": 1,
            "name": "Vulnerability bulletin",
            "product_preset_id": 10,
            "report_item_type_id": None,
            "source": '{% extends "builtin/product_vulnerability.html" %}',
            "require_tlp_clear": True,
        },
    ]

    assert site_client.client.get("/reports/101", headers={"Host": "localhost"}).status_code == 404

    # A template for the vulnerability items brings the product back.
    site_client.fake.templates.append(
        {
            "id": 2,
            "name": "Vulnerability",
            "product_preset_id": None,
            "report_item_type_id": 2,
            "source": "<section>{{ item.name }}</section>",
            "require_tlp_clear": True,
        },
    )
    site_client.cache.clear()

    page = site_client.client.get("/reports/101", headers={"Host": "localhost"})
    assert page.status_code == 200
    assert "<section>Apache Tomcat information disclosure</section>" in page.text
    assert "Several vulnerabilities were published" in page.text


def test_a_template_for_chosen_webs_applies_to_those_webs_only(site_client) -> None:  # noqa: ANN001
    """The disinformation preset has a template for the second web only: the first web shows its vulnerability reports alone."""
    site_client.fake.templates = [
        {
            "id": 1,
            "name": "Disinformation",
            "product_preset_id": 20,
            "report_item_type_id": None,
            "source": '{% extends "builtin/product_base.html" %}',
            "require_tlp_clear": True,
            "public_web_ids": [2],
        },
    ]

    assert site_client.client.get("/reports/201", headers={"Host": "localhost"}).status_code == 404
    page = site_client.client.get("/reports/201", headers={"Host": "disinfo.localhost"})
    assert page.status_code == 200
    assert "Disinformation overview" in page.text
