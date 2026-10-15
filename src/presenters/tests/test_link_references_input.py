"""Presenters receive link citations already numbered by core.

Core renders every ``[#key]`` citation to ``[n]`` and sends ``product.links``, the merged list
those numbers index. The presenter must pass both through untouched: renumbering here again
would point the citations at the wrong links.
"""

from __future__ import annotations

from presenters.base_presenter import BasePresenter
from shared.schema.presenter import PresenterInputSchema

VENDOR = "https://vendor.example/advisory"
NVD = "https://nvd.nist.gov/vuln/detail/CVE-2026-0001"
BLOG = "https://blog.example/post"


def _attribute(attribute_id: int, group_item_id: int, value: str, key: str | None = None) -> dict:
    return {
        "id": attribute_id,
        "attribute_group_item_id": group_item_id,
        "value": value,
        "value_description": key,
        "created": "01.10.2026 - 10:00",
        "last_updated": "01.10.2026 - 10:00",
        "version": 1,
        "current": True,
        "user": {"username": "analyst", "name": "Analyst"},
    }


def _group_item(group_item_id: int, title: str, index: int, max_occurrence: int, attribute_type: str) -> dict:
    return {
        "id": group_item_id,
        "title": title,
        "description": "",
        "index": index,
        "min_occurrence": 0,
        "max_occurrence": max_occurrence,
        "ai_provider_id": None,
        "ai_prompt": None,
        "attribute": {
            "id": group_item_id,
            "name": title,
            "description": "",
            "type": attribute_type,
            "default_value": None,
            "validator": None,
            "validator_parameter": None,
        },
    }


def _input(product_links: list[str] | None) -> dict:
    product = {
        "title": "Bulletin",
        "description": "Read [1] and [3].",
        "product_type": "PDF",
        "product_type_description": "",
        "user": {"username": "analyst", "name": "Analyst"},
        "id": "7",
    }
    if product_links is not None:
        product["links"] = product_links
    return {
        "type": "PDF_PRESENTER",
        "parameter_values": [],
        "product": product,
        "report_types": [
            {
                "id": 1,
                "title": "Vulnerability Report",
                "description": "",
                "attribute_groups": [
                    {
                        "id": 1,
                        "title": "Main",
                        "description": "",
                        "section": None,
                        "section_title": None,
                        "index": 0,
                        "attribute_group_items": [
                            _group_item(10, "Description", 0, 1, "TEXT"),
                            _group_item(12, "Links", 1, 100, "LINK"),
                        ],
                    },
                ],
            },
        ],
        "reports": [
            {
                "id": 1,
                "uuid": "uuid-1",
                "title": "Vuln",
                "title_prefix": "",
                "created": "01.10.2026 - 10:00",
                "last_updated": "01.10.2026 - 10:00",
                "report_item_type_id": 1,
                "state_id": None,
                "remote_user": None,
                "news_item_aggregates": [],
                "remote_report_items": [],
                "attributes": [
                    _attribute(101, 10, "Patch [3], see [2]."),
                    _attribute(103, 12, VENDOR, "vulnaa"),
                    _attribute(104, 12, NVD, "vulnbb"),
                ],
            },
        ],
    }


def test_numbered_citations_and_the_product_links_reach_templates_unchanged() -> None:
    data = BasePresenter.generate_input_data(PresenterInputSchema().load(_input([BLOG, VENDOR, NVD])))

    assert data["product"]["links"] == [BLOG, VENDOR, NVD]
    assert data["product"]["description"] == "Read [1] and [3]."
    (report,) = data["report_items"]
    assert report["attrs"]["description"] == "Patch [3], see [2]."
    assert report["attrs"]["links"] == [VENDOR, NVD]


def test_a_product_without_links_gets_an_empty_list() -> None:
    data = BasePresenter.generate_input_data(PresenterInputSchema().load(_input(None)))

    assert data["product"]["links"] == []
