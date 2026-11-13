"""Stable link references: keys, rendering to numbered citations, and what leaves core.

Text cites a link by its stable key (``[#k3f9a2]``). Core is the only place that turns those
tokens into ``[n]`` numbers: the presenter input and the public-web feed must carry numbered
text and the merged list of URLs those numbers index, never a key.
"""

from __future__ import annotations

import copy
import types

from api import public_web
from managers import link_references
from managers.link_references import (
    LINK_KEY_RE,
    ReferenceIndex,
    build_index,
    generate_link_key,
    normalize_links,
    render_presenter_input,
)
from model.report_item import ReportItem
from shared.schema.attribute import AttributeType

VENDOR = "https://vendor.example/advisory"
NVD = "https://nvd.nist.gov/vuln/detail/CVE-2026-0001"
COMMIT = "https://git.example/commit/1"
BLOG = "https://blog.example/post"


def test_generated_keys_are_valid_and_avoid_taken_ones(monkeypatch) -> None:  # noqa: ANN001
    assert LINK_KEY_RE.fullmatch(generate_link_key())

    draws = iter("aaaaaa" + "bbbbbb")
    monkeypatch.setattr(link_references.secrets, "choice", lambda _alphabet: next(draws))
    assert generate_link_key({"aaaaaa"}) == "bbbbbb"


def test_normalize_links_trims_drops_empty_and_repairs_keys() -> None:
    links = normalize_links(
        [
            {"key": "abc123", "url": f"  {VENDOR} "},
            {"key": "abc123", "url": NVD},  # duplicate key
            {"key": None, "url": COMMIT},  # missing key
            {"key": "NOT-A-KEY", "url": BLOG},  # invalid key
            {"key": "zzz999", "url": "   "},  # no URL
        ],
    )

    assert [link["url"] for link in links] == [VENDOR, NVD, COMMIT, BLOG]
    assert links[0]["key"] == "abc123"
    keys = [link["key"] for link in links]
    assert len(set(keys)) == len(keys)
    assert all(LINK_KEY_RE.fullmatch(key) for key in keys)
    assert normalize_links(None) == []


def test_render_numbers_links_as_first_cited_and_leaves_plain_numbers_alone() -> None:
    index = ReferenceIndex()
    local = {"aaaaaa": index.add("aaaaaa", VENDOR), "bbbbbb": index.add("bbbbbb", NVD)}

    assert index.render("See [#bbbbbb] and [#aaaaaa]; [1] is plain text.", local) == "See [1] and [2]; [1] is plain text."
    assert index.render("Again [#aaaaaa].", local) == "Again [2]."
    assert index.urls == [NVD, VENDOR]
    assert index.render(None) is None
    assert index.render("") == ""


def test_a_citation_of_a_removed_link_is_dropped_with_its_space() -> None:
    index = ReferenceIndex()
    index.add("aaaaaa", VENDOR)

    assert index.render("Fixed [#gone00] upstream [#aaaaaa].") == "Fixed upstream [1]."


def test_links_are_numbered_as_the_text_cites_them_and_equal_urls_share_a_number() -> None:
    index, local_links = build_index(
        [{"key": "prod01", "url": BLOG}],
        [
            [("rep1aa", VENDOR), ("rep1bb", NVD)],
            [("rep2aa", f" {NVD} "), ("rep2bb", COMMIT), ("rep2cc", "")],
        ],
    )

    assert local_links == [{"rep1aa": VENDOR, "rep1bb": NVD}, {"rep2aa": NVD, "rep2bb": COMMIT}]
    # Read in order: the product description resolves any key in the product, a report its own first.
    assert index.render("Intro [#prod01], details [#rep1bb].") == "Intro [1], details [2]."
    assert index.render("Commit [#rep2bb], NVD [#rep2aa].", local_links[1]) == "Commit [3], NVD [2]."
    # The vendor advisory, cited nowhere, comes last.
    assert index.urls == [BLOG, NVD, COMMIT, VENDOR]


def test_links_no_text_cites_follow_in_list_order() -> None:
    index, local_links = build_index(
        [{"key": "prod01", "url": BLOG}, {"key": "prod02", "url": COMMIT}],
        [[("rep1aa", VENDOR), ("rep1bb", NVD)]],
    )

    # The report cites its second link first; nothing else is cited.
    assert index.render("Fixed [#rep1bb].", local_links[0]) == "Fixed [1]."
    # Then the product's own links, then the report's, as listed.
    assert index.urls == [NVD, BLOG, COMMIT, VENDOR]
    # Once listed, the numbers stand.
    assert index.urls == [NVD, BLOG, COMMIT, VENDOR]
    assert index.render("Vendor [#rep1aa].", local_links[0]) == "Vendor [4]."


def test_reordering_the_reports_renumbers_their_links() -> None:
    vendor_report = ([("rep1aa", VENDOR)], "Vendor [#rep1aa].")
    nvd_report = ([("rep2aa", NVD), ("rep2bb", COMMIT)], "NVD [#rep2aa], commit [#rep2bb].")

    def rendered(reports: list) -> tuple[list, list]:
        index, local_links = build_index([], [links for links, _text in reports])
        texts = [index.render(text, local) for (_links, text), local in zip(reports, local_links, strict=True)]
        return texts, index.urls

    assert rendered([vendor_report, nvd_report]) == (["Vendor [1].", "NVD [2], commit [3]."], [VENDOR, NVD, COMMIT])
    assert rendered([nvd_report, vendor_report]) == (["NVD [1], commit [2].", "Vendor [3]."], [NVD, COMMIT, VENDOR])


def _presenter_payload() -> dict:
    """A dumped presenter input: a vulnerability report and an OSINT report with a custom text field."""

    def group_item(item_id: int, index: int, attribute_type: str) -> dict:
        return {"id": item_id, "index": index, "attribute": {"type": attribute_type}}

    return {
        "type": "PDF_PRESENTER",
        "product": {"title": "Bulletin", "description": "Read [#prod01] and [#vulnbb].", "links": None},
        "report_types": [
            {
                "id": 1,
                "attribute_groups": [
                    {"index": 0, "attribute_group_items": [group_item(10, 0, "TEXT"), group_item(11, 1, "STRING")]},
                    {"index": 1, "attribute_group_items": [group_item(12, 0, "LINK"), group_item(13, 1, "CVE")]},
                ],
            },
            {
                "id": 2,
                "attribute_groups": [
                    {"index": 0, "attribute_group_items": [group_item(20, 0, "RICH_TEXT"), group_item(21, 1, "LINK")]},
                ],
            },
        ],
        "reports": [
            {
                "report_item_type_id": 1,
                "attributes": [
                    {"id": 101, "attribute_group_item_id": 10, "value": "Patch [#vulnbb], see [#vulnaa].", "value_description": None},
                    {"id": 102, "attribute_group_item_id": 11, "value": "Comment [#vulnaa]", "value_description": None},
                    {"id": 104, "attribute_group_item_id": 12, "value": NVD, "value_description": "vulnbb"},
                    {"id": 103, "attribute_group_item_id": 12, "value": f" {VENDOR} ", "value_description": "vulnaa"},
                    {"id": 105, "attribute_group_item_id": 12, "value": "  ", "value_description": "vulncc"},
                    {"id": 106, "attribute_group_item_id": 13, "value": "CVE-2026-0001 [#vulnaa]", "value_description": None},
                ],
            },
            {
                "report_item_type_id": 2,
                "attributes": [
                    {
                        "id": 201,
                        "attribute_group_item_id": 20,
                        "value": "<p>Blog [#osinta1], vendor [#osintb2]</p>",
                        "value_description": None,
                    },
                    {"id": 202, "attribute_group_item_id": 21, "value": BLOG, "value_description": "osinta1"},
                    {"id": 203, "attribute_group_item_id": 21, "value": VENDOR, "value_description": "osintb2"},
                ],
            },
        ],
    }


def test_render_presenter_input_numbers_every_report_and_the_product() -> None:
    payload = render_presenter_input(_presenter_payload(), [{"key": "prod01", "url": COMMIT}])

    # Numbered as first cited: the description, then each report in form order.
    assert payload["product"]["links"] == [COMMIT, NVD, VENDOR, BLOG]
    assert payload["product"]["description"] == "Read [1] and [2]."

    vulnerability, osint = payload["reports"]
    values = {attribute["id"]: attribute["value"] for attribute in vulnerability["attributes"]}
    assert values[101] == "Patch [2], see [3]."
    assert values[102] == "Comment [3]"
    # Only citing types are rendered, links are trimmed and an empty one is left out.
    assert values[106] == "CVE-2026-0001 [#vulnaa]"
    assert values[103] == VENDOR
    assert 105 not in values
    assert osint["attributes"][0]["value"] == "<p>Blog [4], vendor [3]</p>"


def test_render_presenter_input_reads_a_report_in_form_order() -> None:
    payload = _presenter_payload()
    payload["product"]["description"] = ""
    vulnerability = payload["reports"][0]
    # The comment, second in the form, comes first in the list.
    vulnerability["attributes"].insert(0, vulnerability["attributes"].pop(1))

    payload = render_presenter_input(payload, [])

    values = {attribute["id"]: attribute["value"] for attribute in vulnerability["attributes"]}
    assert (values[101], values[102]) == ("Patch [1], see [2].", "Comment [2]")
    assert payload["product"]["links"] == [NVD, VENDOR, BLOG]
    # The list keeps its order.
    assert [attribute["id"] for attribute in vulnerability["attributes"][:2]] == [102, 101]


def test_render_presenter_input_leaves_its_input_objects_alone() -> None:
    """The renderer works on the dumped dict only; nothing it was given is shared and changed."""
    payload = _presenter_payload()
    product_links = [{"key": "prod01", "url": COMMIT}]
    original_links = copy.deepcopy(product_links)

    render_presenter_input(payload, product_links)

    assert product_links == original_links


def _attribute(attribute_id: int, title: str, attribute_type: AttributeType, value: str, key: str | None = None) -> types.SimpleNamespace:
    group_item = types.SimpleNamespace(
        title=title,
        index=0 if title == "Description" else 1,
        max_occurrence=1 if title == "Description" else 10,
        attribute=types.SimpleNamespace(type=attribute_type),
        attribute_group=types.SimpleNamespace(index=0, title="Vulnerability"),
    )
    return types.SimpleNamespace(id=attribute_id, attribute_group_item=group_item, value=value, value_description=key)


def test_public_web_feed_carries_numbers_and_urls_but_no_keys() -> None:
    attributes = [
        _attribute(1, "Description", AttributeType.TEXT, "Fixed upstream [#rep1bb]."),
        _attribute(2, "Links", AttributeType.LINK, f"{VENDOR} ", "rep1aa"),
        _attribute(3, "Links", AttributeType.LINK, NVD, "rep1bb"),
        _attribute(4, "Links", AttributeType.LINK, "", "rep1cc"),
    ]
    report_item = types.SimpleNamespace(
        title="Vuln",
        title_prefix="",
        uuid="u-1",
        created=None,
        last_updated=None,
        report_item_type=types.SimpleNamespace(id=2, title="Vulnerability Report", description=""),
        attributes=attributes,
        links=[{"key": "rep1aa", "url": f"{VENDOR} "}, {"key": "rep1bb", "url": NVD}],
    )
    product = types.SimpleNamespace(
        id=7,
        title="Bulletin",
        description="Our note [#prod01], NVD [#rep1bb].",
        links=[{"key": "prod01", "url": BLOG}],
        created=None,
        user=None,
        product_preset=types.SimpleNamespace(id=4, name="Vulnerability bulletin"),
        report_items=[report_item],
    )
    feed = public_web._serialize_product(product)

    # The description is read first, then the report; the vendor advisory nobody cites comes last.
    assert feed["links"] == [BLOG, NVD, VENDOR]
    assert feed["description"] == "Our note [1], NVD [2]."
    assert feed["product_preset"] == {"id": 4, "title": "Vulnerability bulletin"}
    assert feed["report_items"][0]["type_id"] == 2
    entries = feed["report_items"][0]["attributes"]
    layout = {"group": "Vulnerability", "description": None}
    assert entries == [
        {
            "key": "description",
            "attribute_type": "TEXT",
            "label": "Description",
            "multiple": False,
            "order": [0, 0],
            "value": "Fixed upstream [2].",
            **layout,
        },
        {"key": "links", "attribute_type": "LINK", "label": "Links", "multiple": True, "order": [0, 1], "value": VENDOR, **layout},
        {"key": "links", "attribute_type": "LINK", "label": "Links", "multiple": True, "order": [0, 1], "value": NVD, **layout},
    ]
    assert "rep1" not in str(feed)


def test_public_web_feed_reads_a_report_in_form_order() -> None:
    attributes = [
        _attribute(1, "Notes", AttributeType.STRING, "Vendor [#rep1aa]."),
        _attribute(2, "Description", AttributeType.TEXT, "NVD [#rep1bb], vendor [#rep1aa]."),
    ]
    report_item = types.SimpleNamespace(
        title="Vuln",
        title_prefix="",
        uuid="u-1",
        created=None,
        last_updated=None,
        report_item_type=None,
        attributes=attributes,
        links=[{"key": "rep1aa", "url": VENDOR}, {"key": "rep1bb", "url": NVD}],
    )
    product = types.SimpleNamespace(
        id=7,
        title="Bulletin",
        description="",
        links=[],
        created=None,
        user=None,
        product_preset=None,
        report_items=[report_item],
    )

    feed = public_web._serialize_product(product)

    # The description sits above the notes in the form, so it is read, numbered and listed first.
    assert [(entry["key"], entry["value"]) for entry in feed["report_items"][0]["attributes"]] == [
        ("description", "NVD [1], vendor [2]."),
        ("notes", "Vendor [2]."),
    ]
    assert feed["links"] == [NVD, VENDOR]


def test_report_item_links_and_keys() -> None:
    """LINK values are listed in form order, and every one gets a unique key."""
    link_group_items = {12}

    def value(attribute_id: int | None, group_item_id: int, url: str, key: str | None) -> types.SimpleNamespace:
        group_item = types.SimpleNamespace(index=0, attribute_group=types.SimpleNamespace(index=1))
        return types.SimpleNamespace(
            id=attribute_id,
            attribute_group_item_id=group_item_id,
            attribute_group_item=group_item,
            value=url,
            value_description=key,
        )

    values = [
        value(5, 12, NVD, "keep01"),
        value(3, 12, VENDOR, "keep01"),  # a duplicate key: the later value in form order gets a new one
        value(4, 10, "Description", None),
        value(None, 12, "", None),  # just added, no key yet
    ]
    report_item = types.SimpleNamespace(attributes=values, _is_link_attribute=lambda group_item_id: group_item_id in link_group_items)
    report_item._link_attributes = lambda: ReportItem._link_attributes(report_item)

    ReportItem.ensure_link_keys(report_item)
    keys = [values[1].value_description, values[0].value_description, values[3].value_description]
    assert keys[0] == "keep01"
    assert len(set(keys)) == len(keys)
    assert all(LINK_KEY_RE.fullmatch(key) for key in keys)
    assert values[2].value_description is None

    links = ReportItem.links.fget(report_item)
    assert links == [{"key": "keep01", "url": VENDOR}, {"key": values[0].value_description, "url": NVD}]


def test_remote_sync_carries_the_link_keys() -> None:
    """A report shared with another node keeps its citations resolvable there."""
    from shared.schema.report_item import ReportItemAttributeRemoteSchema  # noqa: PLC0415

    link = types.SimpleNamespace(
        attribute_group_item_title="Links",
        value=NVD,
        value_description="rep1bb",
        binary_mime_type=None,
        binary_size=None,
        binary_description=None,
        binary_data=None,
    )

    assert ReportItemAttributeRemoteSchema().dump(link)["value_description"] == "rep1bb"
