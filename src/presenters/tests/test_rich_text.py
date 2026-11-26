"""Rich Text attributes: formatting in HTML output, plain text in any other, nothing else gets through.

A Rich Text attribute is stored as the editor's HTML. Autoescaped HTML output (HTML and PDF
products, MESSAGE bodies in an .html template) printed its tags, and plain-text output (TEXT
presenter, .txt MESSAGE bodies, MISP) printed them too. The presenter sanitizes the value against
the editor's allow-list and hands templates a value that is the formatting in HTML output and
plain text everywhere else.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from jinja2.sandbox import SandboxedEnvironment
from presenters.base_presenter import BasePresenter
from presenters.misp_presenter import json_string_content
from presenters.rich_text import RichText, as_html, rich_text
from shared.schema.attribute import AttributeType

GROUP_ITEM_ID = 9
REPORT_TYPES = {1: SimpleNamespace(title="Advisory", description="")}
FORMATTED = (
    '<p>Patch <strong>now</strong>:</p><ul><li>first</li><li>see <a href="https://example.org/x">advisory</a></li></ul>'
    "<ol><li>one</li><li>two<br>lines</li></ol><p>Never <code>&lt;script&gt;</code></p>"
)


def _attrs(attribute_type: AttributeType, *values: str, max_occurrence: int = 1) -> object:
    group_item = SimpleNamespace(title="Description", max_occurrence=max_occurrence, attribute=SimpleNamespace(type=attribute_type))
    report_item = SimpleNamespace(
        title="Example",
        title_prefix="EX",
        uuid="uuid-1",
        created=None,
        last_updated=None,
        report_item_type_id=1,
        news_item_aggregates=[],
        attributes=[SimpleNamespace(attribute_group_item_id=GROUP_ITEM_ID, value=value, value_description=None) for value in values],
    )
    return BasePresenter.ReportItemObject(report_item, REPORT_TYPES, {GROUP_ITEM_ID: group_item}).attrs


def _render(template: str, *, html: bool, **values: object) -> str:
    return SandboxedEnvironment(autoescape=html).from_string(template).render(**values)


def test_html_output_shows_the_formatting() -> None:
    value = _attrs(AttributeType.RICH_TEXT, FORMATTED).description

    assert isinstance(value, RichText)
    for template in ("{{ d }}", "{{ d | e }}"):
        rendered = _render(template, html=True, d=value)
        assert rendered.startswith("<p>Patch <strong>now</strong>:</p><ul><li>first</li>")
        assert '<a href="https://example.org/x" rel="noopener noreferrer">advisory</a>' in rendered
        assert "<code>&lt;script&gt;</code>" in rendered


def test_plain_text_output_shows_the_text_without_tags() -> None:
    value = _attrs(AttributeType.RICH_TEXT, FORMATTED).description

    assert _render("{{ d }}", html=False, d=value) == (
        "Patch now:\n\n- first\n- see advisory (https://example.org/x)\n1. one\n2. two\nlines\n\nNever <script>"
    )


def test_a_value_without_markup_is_text_with_its_line_breaks() -> None:
    value = _attrs(AttributeType.RICH_TEXT, "first line\nsecond: a < b & c").description

    assert _render("{{ d }}", html=False, d=value) == "first line\nsecond: a < b & c"
    assert _render("{{ d }}", html=True, d=value) == "first line<br>\nsecond: a &lt; b &amp; c"


def test_filters_work_on_the_plain_text_and_stay_escaped_in_html_output() -> None:
    value = rich_text("<p><b>a</b> &lt;b&gt;</p>")

    assert _render("{{ d | upper }}", html=True, d=value) == "A &lt;B&gt;"
    assert _render("{{ d | length }}", html=False, d=value) == "5"


def test_every_value_of_a_repeated_rich_text_attribute_is_sanitized() -> None:
    values = _attrs(AttributeType.RICH_TEXT, "<p>a</p>", "<script>x()</script><p>b</p>", max_occurrence=5).description

    assert [value.__html__() for value in values] == ["<p>a</p>", "<p>b</p>"]
    assert values == ["a", "b"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('<p onclick="steal()">x</p>', "<p>x</p>"),
        ('<p><img src="https://tracker.example/p.gif">text</p>', "<p>text</p>"),
        ("<script>alert(1)</script><style>p{display:none}</style><p>kept</p>", "<p>kept</p>"),
        ('<a href="javascript:alert(1)">click</a>', "<a>click</a>"),
        ('<a href=" JaVaScRiPt:alert(1)">click</a>', "<a>click</a>"),
        (
            '<a href="https://example.org/x?a=1&amp;b=2" target="_blank">ok</a>',
            '<a href="https://example.org/x?a=1&amp;b=2" rel="noopener noreferrer">ok</a>',
        ),
        ('<a href="mailto:csirt@example.org">mail</a>', '<a href="mailto:csirt@example.org" rel="noopener noreferrer">mail</a>'),
        ('<span class="evil" style="color:red">t</span>', "<span>t</span>"),
        ("<iframe src='https://x'>inside</iframe><p>after</p>", "<p>after</p>"),
        ("<!-- hidden --><p>x</p>", "<p>x</p>"),
        ("<marquee>moving</marquee> &lt;b&gt; stays text", "moving &lt;b&gt; stays text"),
        ("<p>unclosed", "<p>unclosed</p>"),
    ],
)
def test_nothing_but_the_editor_s_formatting_gets_through(value: str, expected: str) -> None:
    assert rich_text(value).__html__() == expected


def test_other_attribute_types_stay_text_as_written() -> None:
    value = _attrs(AttributeType.STRING, "<b>not bold</b>").description

    assert not isinstance(value, RichText)
    assert _render("{{ d }}", html=True, d=value) == "&lt;b&gt;not bold&lt;/b&gt;"
    assert _render("{{ d }}", html=False, d=value) == "<b>not bold</b>"


def test_empty_values_are_left_alone() -> None:
    assert rich_text("") == ""
    assert rich_text(None) is None


def test_template_data_keeps_both_forms() -> None:
    data = BasePresenter.to_template_data({"description": rich_text("<p><b>x</b></p>")})

    assert isinstance(data["description"], RichText)
    assert data["description"].__html__() == "<p><b>x</b></p>"


def test_misp_prints_the_plain_text_as_json_string_content() -> None:
    value = rich_text('<p>He said "patch"</p><p><a href="https://example.org">x</a></p>')

    assert json.loads(f'"{json_string_content(value)}"') == 'He said "patch"\n\nx (https://example.org)'


def test_json_output_keeps_the_sanitized_html() -> None:
    data = as_html({"items": [{"attrs": {"description": rich_text("<p><b>x</b><script>y</script></p>")}}]})

    assert json.loads(json.dumps(data)) == {"items": [{"attrs": {"description": "<p><b>x</b></p>"}}]}
