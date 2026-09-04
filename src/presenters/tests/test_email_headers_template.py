"""Tests for the shipped mail headers template.

This renders the real ``templates/email_headers_template.txt`` through the real presenter
environment and the real parser, so it covers the whole path an operator gets out of the
box: attribute values on several report items becoming headers on one e-mail.
"""

from base64 import b64decode
from pathlib import Path

import pytest
from presenters.base_presenter import BasePresenter
from shared.mail_headers import parse_header_block

TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"
TEMPLATE = str(TEMPLATES_ROOT / "email_headers_template.txt")


@pytest.fixture(autouse=True)
def _templates_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the template sandbox at the repo, not the container's /app/templates."""
    monkeypatch.setattr(BasePresenter, "JINJA_TEMPLATES_ROOT", str(TEMPLATES_ROOT))


def headers_for(product: dict, report_items: list[dict]) -> list[dict[str, str]]:
    """Render the shipped template for a product and parse the result."""
    data = {"product": product, "report_items": report_items}
    rendered = b64decode(BasePresenter.render_jinja(data, TEMPLATE)).decode("UTF-8")
    return parse_header_block(rendered)


def item(**attrs: object) -> dict:
    """Build one report item the way to_template_data leaves it."""
    return {"name": "Report", "type": "Vulnerability Report", "attrs": attrs}


def value_of(headers: list[dict[str, str]], name: str) -> str | None:
    """Return the single value of a header, or None when it was not emitted."""
    values = [h["value"] for h in headers if h["name"] == name]
    return values[0] if values else None


def test_a_product_with_no_attributes_emits_no_headers() -> None:
    # Nothing to say means nothing on the wire - no empty "X-Report-Category:".
    assert headers_for({"title": "Test"}, [item()]) == []


def test_values_of_several_report_items_land_in_one_header() -> None:
    items = [item(report_category=["Ransomware", "Phishing"]), item(report_category="Supply Chain")]

    assert value_of(headers_for({"title": "Test"}, items), "X-Report-Category") == "Ransomware, Phishing, Supply Chain"


def test_the_same_value_on_two_report_items_is_listed_once() -> None:
    items = [item(report_category="Ransomware"), item(report_category="Ransomware")]

    assert value_of(headers_for({"title": "Test"}, items), "X-Report-Category") == "Ransomware"


def test_report_type_is_emitted_independently_of_category() -> None:
    headers = headers_for({"title": "Test"}, [item(report_type="Advisory")])

    assert [(h["name"], h["value"]) for h in headers] == [("X-Report-Type", "Advisory")]


def test_max_cvss_is_emitted_when_the_product_has_one() -> None:
    assert value_of(headers_for({"title": "Test", "max_cvss": 9.8}, [item()]), "X-Report-Max-CVSS") == "9.8"


def test_max_cvss_of_none_emits_nothing_rather_than_the_string_none() -> None:
    # get_max_cvss returns None when vulnerability reports carry no CVSS score, and Jinja
    # stringifies that as "None". Shipping "X-Report-Max-CVSS: None" would be a bug.
    headers = headers_for({"title": "Test", "max_cvss": None}, [item(report_category="Ransomware")])

    assert value_of(headers, "X-Report-Max-CVSS") is None
    assert "None" not in str(headers)


def test_max_cvss_absent_from_the_product_emits_nothing() -> None:
    # product.max_cvss is only set at all for products containing a Vulnerability Report.
    assert value_of(headers_for({"title": "Test"}, [item(report_category="Ransomware")]), "X-Report-Max-CVSS") is None


def test_a_newline_in_an_attribute_cannot_add_a_recipient() -> None:
    # End to end through the real template: the analyst's payload stays inside its value.
    items = [item(report_category="Ransomware\nBcc: attacker@evil.test")]
    headers = headers_for({"title": "Test"}, items)

    assert not [h for h in headers if h["name"].lower() == "bcc"]
    assert value_of(headers, "X-Report-Category") == "Ransomware Bcc: attacker@evil.test"
