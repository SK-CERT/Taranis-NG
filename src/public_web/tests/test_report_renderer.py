"""Report templates: which one renders a product, and what a template can and cannot do.

Custom templates are written by administrators and render text collected from outside
sources, so they run in a sandbox with autoescaping, and one that fails must never take
the page down - the built-in template takes over.
"""

from __future__ import annotations

import pytest
from lib.report.filters import FILTERS
from lib.report.product import build_product, displayable, visible_links
from lib.report.renderer import ReportRenderer, get_renderer, templates_for_web
from lib.web.taranis_client import TaranisClient
from shared.public_web_templates import FILTER_NAMES

PRESET = 4
DISINFO_ITEM_TYPE = 9


def _attribute(key: str, attribute_type: str, value: str, *, multiple: bool | None = False) -> dict:
    return {"key": key, "attribute_type": attribute_type, "value": value, "description": None, "label": key.title(), "multiple": multiple}


def _product(*items: dict, preset: int = PRESET, links: list[str] | None = None, renderer: ReportRenderer | None = None) -> dict:
    """The product as the cache builds it: with ``renderer``, items it has no template for are left out."""
    return build_product(
        {
            "id": 7,
            "title": "Bulletin",
            "description": "Weekly overview.",
            "links": links or [],
            "created": "2026-10-01T10:00:00",
            "user": {"name": "Analyst"},
            "product_preset": {"id": preset, "title": "Bulletin"},
            "report_items": list(items),
        },
        renderer.has_item_template if renderer else None,
    )


def _item(item_type: str, type_id: int, *attributes: dict) -> dict:
    return {"title": f"A {item_type}", "uuid": f"uuid-{type_id}", "type": item_type, "type_id": type_id, "attributes": list(attributes)}


def _disinfo(value: str = "Vaccines contain chips") -> dict:
    return _item("Disinformation", DISINFO_ITEM_TYPE, _attribute("claim", "STRING", value), _attribute("tlp", "TLP", "CLEAR"))


def _vulnerability(*links: str) -> dict:
    return _item(
        "Vulnerability Report",
        2,
        _attribute("description", "TEXT", "A flaw."),
        _attribute("cvss", "CVSS", "9.8"),
        _attribute("tlp", "TLP", "CLEAR"),
        *(_attribute("links", "LINK", link) for link in links),
    )


NOTE_ITEM_TYPE = 1


def _note(*links: str, tlp: str = "CLEAR", title: str = "Weekly note") -> dict:
    """An item of a type of the instance's own: only the generic built-in fits it."""
    return _item(
        title,
        NOTE_ITEM_TYPE,
        _attribute("description", "TEXT", "The note of this week."),
        _attribute("tlp", "TLP", tlp),
        *(_attribute("links", "LINK", link) for link in links),
    )


def _template(source: str, *, preset: int | None = None, item_type: int | None = None, require_tlp_clear: bool = True) -> dict:
    return {
        "id": 1,
        "name": "custom",
        "product_preset_id": preset,
        "report_item_type_id": item_type,
        "source": source,
        "require_tlp_clear": require_tlp_clear,
    }


def _page(renderer: ReportRenderer, product: dict, view: str = "detail") -> str:
    """Render a page part; rendering runs the clean filter, which needs bleach."""
    pytest.importorskip("bleach")
    return str(renderer.render(product, view))


def test_the_filters_are_the_ones_core_validates_templates_against() -> None:
    """Core compiles a template on save against FILTER_NAMES; a filter missing there would be refused."""
    assert sorted(FILTERS) == sorted(FILTER_NAMES)


# -- which template renders --------------------------------------------------------


def test_builtin_templates_render_what_has_no_template_of_its_own() -> None:
    renderer = ReportRenderer([])

    assert renderer.product_template(_product(_vulnerability())) == "builtin/product_vulnerability.html"
    assert renderer.product_template(_product(_disinfo())) == "builtin/product_base.html"
    product = _product(_vulnerability(), _disinfo())
    assert [renderer.item_template(item) for item in product["report_items"]] == [
        "builtin/item_vulnerability.html",
        "builtin/item_generic.html",
    ]


def test_a_custom_template_wins_over_the_builtin_one() -> None:
    renderer = ReportRenderer(
        [
            _template('{% extends "builtin/product_base.html" %}', preset=PRESET),
            _template("<i>{{ item.attrs.claim }}</i>", item_type=DISINFO_ITEM_TYPE),
        ],
    )
    product = _product(_disinfo())

    assert renderer.product_template(product) == f"product/{PRESET}"
    assert renderer.item_template(product["report_items"][0]) == f"item/{DISINFO_ITEM_TYPE}"
    assert "<i>Vaccines contain chips</i>" in _page(renderer, product)


# -- the built-in vulnerability template -----------------------------------------------


def _stock_vulnerability(*attributes: dict) -> dict:
    """An item of the "Vulnerability Report" type as Taranis creates it (attribute keys from its titles)."""
    return {"title": "", "uuid": "uuid-stock", "type": "Vulnerability Report", "type_id": 1, "attributes": list(attributes)}


def test_the_builtin_vulnerability_template_fits_the_type_taranis_creates() -> None:
    item = _stock_vulnerability(
        _attribute("tlp", "TLP", "CLEAR"),
        _attribute("cve", "CVE", "CVE-2026-1234", multiple=True),
        {**_attribute("cwe", "CWE", "79", multiple=True), "description": "Cross-site Scripting"},
        _attribute("cvss", "CVSS", "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N"),
        _attribute("cvss_number", "STRING", "7.1"),
        _attribute("description", "TEXT", "a stored XSS in the admin console."),
        _attribute("impact", "ENUM", "Information disclosure", multiple=True),
        _attribute("impact", "ENUM", "Privilege escalation", multiple=True),
        _attribute("exposure_date", "DATE", "2026-08-11"),
        _attribute("update_date", "DATE", "2026-08-12"),
        _attribute("confidentiality", "RADIO", "Internal"),
        _attribute("affected_systems_cpe_codes", "CPE", "cpe:2.3:a:example:console:*:*:*:*:*:*:*:*", multiple=True),
        _attribute("affected_systems", "STRING", "Example Console 4.x", multiple=True),
        _attribute("affected_systems", "STRING", "Example Console 5.0", multiple=True),
        _attribute("ioc", "STRING", "198.51.100.7", multiple=True),
        _attribute("recommendations", "TEXT", "update to 5.1."),
    )
    renderer = ReportRenderer([])
    product = _product(item)

    assert renderer.item_template(product["report_items"][0]) == "builtin/item_vulnerability.html"
    page = " ".join(_page(renderer, product).split())
    for shown in (
        '<b class="fw-bolder me-4">CVE-2026-1234</b>',
        "CVSS 7.1 (High)",
        "A stored XSS in the admin console.",
        "<b>Impact:</b> Information disclosure, Privilege escalation",
        '<span class="fw-light">Example Console 4.x</span>',
        "<b>Affected_Systems_Cpe_Codes:</b>",
        "<code>cpe:2.3:a:example:console:*:*:*:*:*:*:*:*</code>",
        "Update to 5.1.",
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N",
        "198.51.100.7",
        "https://nvd.nist.gov/vuln/detail/CVE-2026-1234",
        "CWE-79: Cross-site Scripting",
        "11. 8. 2026",
        "12. 8. 2026",
    ):
        assert shown in page, shown
    # Internal: how confidential the item is is not the public's business.
    assert "Internal" not in page


V30 = "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
V31 = "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N"
V40 = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
V20 = "AV:N/AC:L/Au:N/C:P/I:P/A:P"


@pytest.mark.parametrize(
    ("value", "url"),
    [
        (V30, f"https://www.first.org/cvss/calculator/3.0#{V30}"),
        (V31, f"https://www.first.org/cvss/calculator/3.1#{V31}"),
        (V40, f"https://www.first.org/cvss/calculator/4.0#{V40}"),
        # Surrounding space goes, and the metrics come in the order the specification lists them.
        (" CVSS:3.1/C:H/I:L/A:N/AV:N/AC:L/PR:N/UI:R/S:U ", f"https://www.first.org/cvss/calculator/3.1#{V31}"),
        # Temporal and environmental metrics are kept.
        (f"{V31}/E:P/CR:H", f"https://www.first.org/cvss/calculator/3.1#{V31}/E:P/CR:H"),
        # FIRST has no CVSS 2.0 calculator.
        (V20, None),
        (f"CVSS:2.0/{V20}", None),
        # The calculator needs every base metric; anything else is no vector.
        ("CVSS:3.1/AV:N/AC:L", None),
        ("CVSS:4.0/AV:N/AC:L/AT:N", None),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N/AV:L", None),
        ("javascript:alert(1)//CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:L/A:N", None),
        ("9.8", None),
        ("", None),
        (None, None),
    ],
)
def test_a_cvss_3_or_4_vector_links_to_firsts_calculator(value: str | None, url: str | None) -> None:
    assert FILTERS["cvss_calculator_url"](value) == url


def test_the_filter_takes_the_first_of_several_values() -> None:
    assert FILTERS["cvss_calculator_url"]([V40, V31]) == f"https://www.first.org/cvss/calculator/4.0#{V40}"


@pytest.mark.parametrize("vector", [V30, V31, V40])
def test_the_vulnerability_template_links_the_vector_to_the_calculator(vector: str) -> None:
    page = " ".join(_page(ReportRenderer([]), _product(_stock_vulnerability(_attribute("cvss", "CVSS", vector)))).split())

    version = vector[5:8]
    # Rendered without a catalog, a phrase reads as its key; the golden pages show it translated.
    link = f'<a href="https://www.first.org/cvss/calculator/{version}#{vector}" title="cvss_calculator">{vector}</a>'
    assert f"<b>CVSS:</b> {link}" in page


def test_a_cvss_2_vector_is_shown_without_a_link() -> None:
    page = " ".join(_page(ReportRenderer([]), _product(_stock_vulnerability(_attribute("cvss", "CVSS", V20)))).split())

    assert f"<b>CVSS:</b> {V20}" in page
    assert "first.org" not in page


def test_without_a_vector_the_score_comes_from_the_cvss_number() -> None:
    page = _page(ReportRenderer([]), _product(_stock_vulnerability(_attribute("cvss_number", "STRING", "9.8"))))

    assert "CVSS 9.8 (Critical)" in page


@pytest.mark.parametrize(
    ("title", "template"),
    [
        ("Vulnerability Report", "builtin/item_vulnerability.html"),
        ("Vulnerability Report - Intro", "builtin/item_generic.html"),
        ("Vulnerability Report - old", "builtin/item_generic.html"),
        ("Disinformation", "builtin/item_generic.html"),
    ],
)
def test_only_the_type_taranis_creates_gets_the_vulnerability_template(title: str, template: str) -> None:
    """Another type - changed, renamed, or one's own - is not what the template was written for."""
    item = _product({**_stock_vulnerability(), "type": title})["report_items"][0]

    assert ReportRenderer([]).item_template(item) == template


# -- built-ins switched off ----------------------------------------------------------


def test_a_switched_off_item_builtin_falls_back_on_the_generic_one() -> None:
    renderer = ReportRenderer([], ["builtin/item_vulnerability.html"])
    product = _product(_vulnerability(), _disinfo())

    assert [renderer.item_template(item) for item in product["report_items"]] == [
        "builtin/item_generic.html",
        "builtin/item_generic.html",
    ]
    assert renderer.has_builtin_product_template() is True


def test_an_item_with_every_builtin_off_and_no_template_is_left_out() -> None:
    renderer = ReportRenderer(
        [_template("<i>{{ item.attrs.claim }}</i>", item_type=DISINFO_ITEM_TYPE)],
        ["builtin/item_vulnerability.html", "builtin/item_generic.html"],
    )
    product = _product(_vulnerability(), _disinfo())

    assert renderer.item_template(product["report_items"][0]) is None
    page = _page(renderer, product)
    assert "A flaw." not in page
    assert "<i>Vaccines contain chips</i>" in page


def test_a_failing_custom_item_template_with_its_builtins_off_leaves_only_that_item_out() -> None:
    renderer = ReportRenderer(
        [_template("{{ item.attrs.claim.missing.deeper }}", item_type=DISINFO_ITEM_TYPE)],
        ["builtin/item_generic.html"],
    )

    page = _page(renderer, _product(_disinfo()))

    assert "Bulletin" in page
    assert "Vaccines contain chips" not in page


def test_with_the_vulnerability_product_builtin_off_only_presets_with_a_template_are_rendered() -> None:
    renderer = ReportRenderer(
        [_template('{% extends "builtin/product_vulnerability.html" %}{% block header %}<b>own</b>{% endblock %}', preset=PRESET)],
        ["builtin/product_vulnerability.html"],
    )

    assert renderer.has_builtin_product_template() is False
    # A failing custom template falls back on the base layout, which cannot be switched off.
    assert renderer.product_template(_product(_vulnerability(), preset=PRESET + 1)) == "builtin/product_base.html"
    # Custom templates still extend the switched-off built-in: off means it is not used on its own.
    assert "<b>own</b>" in _page(renderer, _product(_vulnerability()))


ITEM_BUILTINS = ["builtin/item_vulnerability.html", "builtin/item_generic.html"]


def test_an_item_without_a_template_is_left_out_of_the_product() -> None:
    """Not shown as a block, nor in RSS or search; the links only it cites are hidden, its TLP still counts."""
    renderer = ReportRenderer([_template("<i>{{ item.attrs.description }}</i>", item_type=2)], ITEM_BUILTINS)

    product = _product(_note("https://note.example", tlp="AMBER"), _vulnerability("https://flaw.example"), renderer=renderer)

    assert [item["type"] for item in product["report_items"]] == ["Vulnerability Report"]
    assert product["body_items"] == product["report_items"]
    assert product["items_left_out"] == 1
    assert product["max_tlp"] == "AMBER"
    assert product["is_vulnerability"] is True
    links = ["https://note.example", "https://flaw.example"]
    product = _product(_note("https://note.example"), _vulnerability("https://flaw.example"), links=links, renderer=renderer)
    assert visible_links(product, None) == [None, "https://flaw.example"]
    page = _page(renderer, product)
    assert "The note of this week." not in page
    assert "<i>A flaw.</i>" in page
    assert "note.example" not in page
    assert "The note of this week." not in str(renderer.render_text(product))


def test_without_any_builtin_item_template_every_item_is_left_out() -> None:
    product = _product(_note(), _vulnerability(), renderer=ReportRenderer([], ITEM_BUILTINS))

    assert product["report_items"] == []
    assert product["items_left_out"] == 2
    assert product["max_cvss"] is None


def test_no_report_item_type_has_a_role_of_its_own() -> None:
    """Not even one titled "Vulnerability Report - Intro": it is one of the items, and the page opens with the description."""
    renderer = ReportRenderer([_template("<blockquote>{{ item.attrs.description }}</blockquote>", item_type=NOTE_ITEM_TYPE)])
    product = _product(_note(title="Vulnerability Report - Intro"), _vulnerability())

    assert "intro" not in product
    assert [item["type"] for item in product["body_items"]] == ["Vulnerability Report - Intro", "Vulnerability Report"]
    assert product["lead"] == product["description"] == "Weekly overview."
    page = " ".join(_page(renderer, product).split())
    assert page.index("Weekly overview.") < page.index("<blockquote>The note of this week.</blockquote>") < page.index("A flaw.")


def test_the_bases_cannot_be_switched_off() -> None:
    product = _product(_vulnerability(), _disinfo())

    renderer = ReportRenderer([], ["builtin/product_base.html", "builtin/_macros.html", "builtin/no_such.html"])

    assert renderer.has_builtin_product_template() is True
    assert _page(renderer, product) == _page(ReportRenderer([]), product)


class _Response:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self.payload = payload or {}
        self.text = ""

    def json(self) -> dict:
        return self.payload


@pytest.mark.parametrize(
    ("response", "disabled"),
    [
        (_Response(200, {"items": [], "disabled_builtins": ["builtin/item_generic.html"]}), ["builtin/item_generic.html"]),
        (_Response(200, {"total_count": 0, "items": []}), []),
        (_Response(404), []),
    ],
    ids=["current core", "core before built-ins could be switched off", "core before report templates"],
)
def test_the_client_reads_the_switched_off_builtins_from_core(response: _Response, disabled: list[str]) -> None:
    client = TaranisClient("https://core.example", "key")
    client._session.get = lambda _url, **_kwargs: response

    assert client.get_report_templates() == {"items": [], "disabled_builtins": disabled}


# -- templates for chosen webs -------------------------------------------------------


def _for_webs(template_id: int, *web_ids: int, preset: int | None = PRESET, item_type: int | None = None) -> dict:
    return {**_template(f"<i>{template_id}</i>", preset=preset, item_type=item_type), "id": template_id, "public_web_ids": list(web_ids)}


def test_a_web_renders_with_the_template_that_lists_it_else_the_one_for_every_web() -> None:
    every_web = _for_webs(1)
    web_one = _for_webs(2, 1)
    web_two_and_three = _for_webs(3, 2, 3)
    item_for_web_three = _for_webs(4, 3, preset=None, item_type=DISINFO_ITEM_TYPE)
    templates = [every_web, web_one, web_two_and_three, item_for_web_three]

    assert [t["id"] for t in templates_for_web(templates, 1)] == [2]
    assert [t["id"] for t in templates_for_web(templates, 3)] == [3, 4]
    assert [t["id"] for t in templates_for_web(templates, 4)] == [1]
    # No web in particular: only what is for every web.
    assert [t["id"] for t in templates_for_web(templates, None)] == [1]
    # A core from before sends no webs: every template is for every web.
    assert templates_for_web([_template("<i>x</i>", preset=PRESET)], 7) == [_template("<i>x</i>", preset=PRESET)]


def test_each_web_keeps_a_renderer_of_its_own() -> None:
    templates = [_for_webs(1), _for_webs(2, 1)]

    web_one = get_renderer(templates, (), 1)
    other_web = get_renderer(templates, (), 2)

    assert web_one is get_renderer(templates, (), 1)
    assert web_one is not other_web
    product = _product(_disinfo())
    assert "<i>2</i>" in _page(web_one, product)
    assert "<i>1</i>" in _page(other_web, product)


def test_a_web_without_a_template_for_a_preset_shows_only_its_vulnerability_reports() -> None:
    """Which products a web shows follows the templates that apply to it."""
    renderer = get_renderer([_for_webs(2, 1)], (), 2)

    assert renderer.has_product_template(PRESET) is False


# -- what a template can do ----------------------------------------------------------


def test_values_are_escaped() -> None:
    renderer = ReportRenderer([_template("<i>{{ item.attrs.claim }}</i>", item_type=DISINFO_ITEM_TYPE)])

    page = _page(renderer, _product(_disinfo("<script>alert(1)</script>")))

    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_the_sandbox_keeps_templates_away_from_python_internals() -> None:
    """The attempt fails, and the built-in template renders the item instead."""
    renderer = ReportRenderer([_template("{{ item.__class__.__mro__ }}", item_type=DISINFO_ITEM_TYPE)])

    detail = _page(renderer, _product(_disinfo()))

    assert "<class" not in detail
    assert "Vaccines contain chips" in detail


def test_a_broken_template_falls_back_to_the_builtin_one() -> None:
    renderer = ReportRenderer(
        [
            _template(
                '{% extends "builtin/product_base.html" %}{% block header %}{{ product.title | no_such_filter }}{% endblock %}',
                preset=PRESET,
            ),
            _template("{{ item.attrs.claim.missing.deeper }}", item_type=DISINFO_ITEM_TYPE),
        ],
    )

    detail = _page(renderer, _product(_disinfo()))

    assert "Bulletin" in detail
    assert "Vaccines contain chips" in detail


# -- which products are shown --------------------------------------------------------


def test_tlp_gate_and_vulnerability_only_mode() -> None:
    amber = _product(_item("Disinformation", DISINFO_ITEM_TYPE, _attribute("tlp", "TLP", "AMBER")))
    no_tlp = _product(_item("Disinformation", DISINFO_ITEM_TYPE, _attribute("claim", "STRING", "x")))

    assert displayable(amber, vulnerability_only=False, require_tlp_clear=False)[0] is False
    assert displayable(no_tlp, vulnerability_only=False, require_tlp_clear=True)[0] is False
    assert displayable(no_tlp, vulnerability_only=False, require_tlp_clear=False)[0] is True
    # A product preset without a report template shows vulnerability reports only.
    assert displayable(_product(_disinfo()), vulnerability_only=True)[0] is False
    assert displayable(_product(_vulnerability()), vulnerability_only=True)[0] is True


def test_a_template_can_allow_products_without_tlp() -> None:
    renderer = ReportRenderer([_template('{% extends "builtin/product_base.html" %}', preset=PRESET, require_tlp_clear=False)])

    assert renderer.require_tlp_clear(PRESET) is False
    assert renderer.require_tlp_clear(PRESET + 1) is True


# -- template data -------------------------------------------------------------------


def test_attrs_follow_the_presenter_shape() -> None:
    item = _item(
        "Disinformation",
        DISINFO_ITEM_TYPE,
        _attribute("claim", "STRING", "one claim"),
        _attribute("sources", "STRING", "a", multiple=True),
        _attribute("sectors", "MULTI_CHOICE", "Energy"),
        _attribute("sectors", "MULTI_CHOICE", "Health"),
        _attribute("cwe_ids", "CWE", "79"),
    )

    attrs = _product(item)["report_items"][0]["attrs"]

    assert attrs["claim"] == "one claim"
    assert attrs["sources"] == ["a"]
    assert attrs["sectors"] == ["Energy", "Health"]
    assert attrs["cwe_ids"] == {"79": None}
