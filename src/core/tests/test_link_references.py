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


def test_render_numbers_tokens_and_leaves_plain_numbers_alone() -> None:
    index = ReferenceIndex()
    local = {"aaaaaa": index.add("aaaaaa", VENDOR), "bbbbbb": index.add("bbbbbb", NVD)}

    assert index.render("See [#bbbbbb] and [#aaaaaa]; [1] is plain text.", local) == "See [2] and [1]; [1] is plain text."
    assert index.render(None) is None
    assert index.render("") == ""


def test_a_citation_of_a_removed_link_is_dropped_with_its_space() -> None:
    index = ReferenceIndex()
    index.add("aaaaaa", VENDOR)

    assert index.render("Fixed [#gone00] upstream [#aaaaaa].") == "Fixed upstream [1]."


def test_product_links_come_first_and_equal_urls_share_a_number() -> None:
    index, local_numbers = build_index(
        [{"key": "prod01", "url": BLOG}],
        [
            [("rep1aa", VENDOR), ("rep1bb", NVD)],
            [("rep2aa", f" {NVD} "), ("rep2bb", COMMIT), ("rep2cc", "")],
        ],
    )

    assert index.urls == [BLOG, VENDOR, NVD, COMMIT]
    assert local_numbers == [{"rep1aa": 2, "rep1bb": 3}, {"rep2aa": 3, "rep2bb": 4}]
    # A report resolves its own keys; the product description resolves any key in the product.
    assert index.render("[#rep2aa][#rep2bb]", local_numbers[1]) == "[3][4]"
    assert index.render("Intro [#prod01], details [#rep1bb].") == "Intro [1], details [3]."


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

    # Product links first, then links in form order (by value id within a group item): 103 before 104.
    assert payload["product"]["links"] == [COMMIT, VENDOR, NVD, BLOG]
    assert payload["product"]["description"] == "Read [1] and [3]."

    vulnerability, osint = payload["reports"]
    values = {attribute["id"]: attribute["value"] for attribute in vulnerability["attributes"]}
    assert values[101] == "Patch [3], see [2]."
    assert values[102] == "Comment [2]"
    # Only citing types are rendered, links are trimmed and an empty one is left out.
    assert values[106] == "CVE-2026-0001 [#vulnaa]"
    assert values[103] == VENDOR
    assert 105 not in values
    assert osint["attributes"][0]["value"] == "<p>Blog [4], vendor [2]</p>"


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
        index=0,
        attribute=types.SimpleNamespace(type=attribute_type),
        attribute_group=types.SimpleNamespace(index=0),
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
        report_item_type=types.SimpleNamespace(title="Vulnerability Report", description=""),
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
        report_items=[report_item],
    )
    feed = public_web._serialize_product(product)

    assert feed["links"] == [BLOG, VENDOR, NVD]
    assert feed["description"] == "Our note [1], NVD [3]."
    entries = feed["report_items"][0]["attributes"]
    assert entries == [
        {"key": "description", "type": "TEXT", "value": "Fixed upstream [3].", "description": None},
        {"key": "links", "type": "LINK", "value": VENDOR, "description": None},
        {"key": "links", "type": "LINK", "value": NVD, "description": None},
    ]
    assert "rep1" not in str(feed)


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
