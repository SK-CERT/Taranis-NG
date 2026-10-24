"""public-web shows link citations exactly as Taranis-NG core numbered them.

Core renders every citation to ``[n]`` and serves ``links``, the merged list of the product's
sources those numbers index (the product's own links first). The node must not renumber
anything; it only needs the attribute type (LINK) to tell which sources belong to which item.
"""

from __future__ import annotations

import pytest
from lib.report.product import build_product, visible_links

BLOG = "https://blog.example/post"
VENDOR = "https://vendor.example/advisory"
NVD = "https://nvd.nist.gov/vuln/detail/CVE-2026-0001"
COMMIT = "https://git.example/commit/1"


def _attribute(key: str, attribute_type: str, value: str) -> dict:
    return {"key": key, "attribute_type": attribute_type, "value": value, "description": None}


def _item(title: str, description: str, links: list[str]) -> dict:
    return {
        "title": title,
        "uuid": f"uuid-{title}",
        "type": "Vulnerability Report",
        "attributes": [
            _attribute("description", "TEXT", description),
            _attribute("tlp", "TLP", "CLEAR"),
            *(_attribute("links", "LINK", link) for link in links),
        ],
    }


def _served() -> dict:
    """A product as core's public-web API serves it: citations already numbered."""
    return {
        "id": 7,
        "title": "Bulletin",
        "description": "Our note [1], NVD [3].",
        "links": [BLOG, VENDOR, NVD, COMMIT],
        "created": "2026-10-01T10:00:00",
        "user": {"name": "Analyst", "username": "analyst"},
        "report_items": [
            _item("First", "Fixed upstream [3], vendor [2].", [VENDOR, NVD]),
            _item("Second", "See the commit [4] and [3].", [NVD, COMMIT]),
        ],
    }


def test_citations_and_the_product_links_are_taken_as_served() -> None:
    product = build_product(_served())

    assert product["links"] == [BLOG, VENDOR, NVD, COMMIT]
    assert product["description"] == "Our note [1], NVD [3]."
    first, second = product["report_items"]
    assert first["attrs"]["description"] == "Fixed upstream [3], vendor [2]."
    assert second["attrs"]["description"] == "See the commit [4] and [3]."


def test_the_links_of_selected_items_keep_their_numbers() -> None:
    """With ?items=, the selected items' sources show - and those of the product's description, which shows too."""
    product = build_product(_served())

    assert visible_links(product, [2]) == [BLOG, None, NVD, COMMIT]
    assert visible_links(product, None) == [BLOG, VENDOR, NVD, COMMIT]


def test_the_rendered_page_links_each_number_to_its_source() -> None:
    pytest.importorskip("bleach")
    from lib.report.renderer import ReportRenderer  # noqa: PLC0415 (after the optional import check)

    page = str(ReportRenderer([]).render(build_product(_served()), "detail"))

    assert f'<a href="{NVD}" style="text-decoration: none;">[3]</a>' in page
    assert f'<a href="{COMMIT}" style="text-decoration: none;">[4]</a>' in page
