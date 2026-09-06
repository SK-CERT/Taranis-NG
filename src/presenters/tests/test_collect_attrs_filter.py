"""Tests for the Jinja filters that feed the mail headers template.

``collect_attrs`` is what turns "several report items in one product, each with its own
values" into a single header value. It runs against the *rendered* input data, where every
presenter object has already been flattened into plain dicts by
``BasePresenter.to_template_data`` -- so the fixtures here are literal dicts, exactly as in
``test_default_vulnerability_template.py``. That is deliberate: an implementation reaching
for ``getattr`` passes nothing else and fails here.
"""

from base64 import b64decode

from presenters.base_presenter import BasePresenter
from presenters.jinja_filters import filter_collect_attrs, filter_header_value


def render(template: str, data: dict) -> str:
    """Render a template string through the real presenter environment."""
    return b64decode(BasePresenter.render_jinja(data, None, template_string=template)).decode("UTF-8")


def item(**attrs: object) -> dict:
    """Build one report item the way to_template_data leaves it."""
    return {"name": "Report", "type": "Vulnerability Report", "attrs": attrs}


# --- the attribute value shapes ----------------------------------------------------


def test_scalar_value_is_collected() -> None:
    # An attribute group item with max_occurrence == 1 stores a bare string.
    assert filter_collect_attrs([item(report_category="Ransomware")], "report_category") == ["Ransomware"]


def test_list_value_is_collected() -> None:
    # Any other max_occurrence stores a list, one entry per value row.
    assert filter_collect_attrs([item(report_category=["Ransomware", "Phishing"])], "report_category") == ["Ransomware", "Phishing"]


def test_dict_value_yields_its_keys() -> None:
    # The cwe* shape is {value: value_description}.
    assert filter_collect_attrs([item(cwe={"CWE-79": "XSS", "CWE-89": "SQLi"})], "cwe") == ["CWE-79", "CWE-89"]


def test_nested_list_is_flattened() -> None:
    # Two attribute group items in different groups sharing a title.
    assert filter_collect_attrs([item(report_category=[["Ransomware"], ["Phishing"]])], "report_category") == ["Ransomware", "Phishing"]


def test_missing_attribute_is_skipped_not_an_error() -> None:
    items = [item(report_category="Ransomware"), item(), item(report_type="Advisory")]

    assert filter_collect_attrs(items, "report_category") == ["Ransomware"]


def test_report_item_without_attrs_is_skipped() -> None:
    assert filter_collect_attrs([{"name": "Report", "type": "Vulnerability Report"}], "report_category") == []


# --- combining across report items -------------------------------------------------


def test_values_from_every_report_item_are_combined() -> None:
    items = [item(report_category=["Ransomware", "Phishing"]), item(report_category="Supply Chain")]

    assert filter_collect_attrs(items, "report_category") == ["Ransomware", "Phishing", "Supply Chain"]


def test_repeats_across_report_items_are_deduped_in_first_seen_order() -> None:
    items = [item(report_category="Phishing"), item(report_category="Ransomware"), item(report_category="Phishing")]

    assert filter_collect_attrs(items, "report_category") == ["Phishing", "Ransomware"]


def test_unique_false_keeps_every_occurrence() -> None:
    items = [item(report_category="Phishing"), item(report_category="Phishing")]

    assert filter_collect_attrs(items, "report_category", unique=False) == ["Phishing", "Phishing"]


def test_empty_values_are_dropped() -> None:
    assert filter_collect_attrs([item(report_category=["", "   ", "Phishing"])], "report_category") == ["Phishing"]


def test_collected_values_are_scrubbed_of_line_breaks() -> None:
    # An analyst pasting a newline into an attribute must not be able to start a new header.
    items = [item(report_category="Ransomware\nBcc: attacker@evil.test")]

    assert filter_collect_attrs(items, "report_category") == ["Ransomware Bcc: attacker@evil.test"]


# --- header_value ------------------------------------------------------------------


def test_header_value_of_none_is_empty() -> None:
    # Without this, "{{ data.product.max_cvss }}" renders the literal "None".
    assert filter_header_value(None) == ""


def test_header_value_scrubs_and_collapses() -> None:
    assert filter_header_value("  Advisory \r\n Urgent  ") == "Advisory Urgent"


def test_header_value_stringifies_a_number() -> None:
    assert filter_header_value(9.8) == "9.8"


# --- registered in the real environment --------------------------------------------


def test_filters_are_available_to_templates() -> None:
    data = {"report_items": [item(report_category=["Ransomware", "Phishing"]), item(report_category="Ransomware")]}
    template = "X-Report-Category: {{ data.report_items | collect_attrs('report_category') | join(', ') }}"

    assert render(template, data) == "X-Report-Category: Ransomware, Phishing"


def test_collect_attrs_composes_with_selectattr() -> None:
    # selectattr yields a generator, so the filter must accept any iterable.
    data = {
        "report_items": [
            {"type": "Vulnerability Report", "attrs": {"report_category": "Ransomware"}},
            {"type": "Disinformation", "attrs": {"report_category": "Propaganda"}},
        ],
    }
    template = (
        "{{ data.report_items | selectattr('type', 'equalto', 'Vulnerability Report') | collect_attrs('report_category') | join(', ') }}"
    )

    assert render(template, data) == "Ransomware"
