"""public-web shows link citations exactly as Taranis-NG core numbered them.

Core renders every citation to ``[n]`` and serves ``links``, the merged list of the product's
sources those numbers index (the product's own links first). The node must not renumber
anything; it only needs to know which attributes are links (``type`` LINK) to tell which
sources belong to which report item.
"""

from __future__ import annotations

from lib.report.vulnerability_report import VulnerabilityReport

BLOG = "https://blog.example/post"
VENDOR = "https://vendor.example/advisory"
NVD = "https://nvd.nist.gov/vuln/detail/CVE-2026-0001"
COMMIT = "https://git.example/commit/1"


def _attribute(key: str, attribute_type: str, value: str) -> dict:
    return {"key": key, "type": attribute_type, "value": value, "description": None}


def _item(title: str, description: str, links: list[str]) -> dict:
    return {
        "title": title,
        "title_prefix": "",
        "uuid": f"uuid-{title}",
        "created": "2026-10-01T10:00:00",
        "last_updated": "2026-10-01T10:00:00",
        "type": "Vulnerability Report",
        "attributes": [
            _attribute("description", "TEXT", description),
            _attribute("tlp", "TLP", "CLEAR"),
            _attribute("affected_systems", "STRING", "Example server"),
            _attribute("affected_versions_parsability", "RADIO", "Do not parse"),
            *(_attribute("links", "LINK", link) for link in links),
        ],
    }


def _product() -> dict:
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
    report = VulnerabilityReport.from_dict(_product())

    assert report.get_links() == [BLOG, VENDOR, NVD, COMMIT]
    assert report.get_description() == "Our note [1], NVD [3]."
    first, second = report.get_report_items()
    assert first.get_description() == "Fixed upstream [3], vendor [2]."
    assert second.get_description() == "See the commit [4] and [3]."
    assert first.get_links() == [VENDOR, NVD]


def test_the_links_of_selected_items_keep_their_numbers() -> None:
    report = VulnerabilityReport.from_dict(_product())

    assert report.get_links([2]) == [None, None, NVD, COMMIT]


def test_a_cached_report_is_rebuilt_from_the_served_data() -> None:
    report = VulnerabilityReport.from_dict(_product())
    restored = VulnerabilityReport.__new__(VulnerabilityReport)
    restored.__setstate__(report.__getstate__())

    assert restored.get_links() == report.get_links()
    assert restored.get_report_items()[0].get_description() == "Fixed upstream [3], vendor [2]."
