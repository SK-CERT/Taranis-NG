"""The GCVE publication of a web (GCVE-BCP-03): the endpoint, the dump, security.txt, conformance.

Core serves the records of a web (see ``FakeTaranisClient.list_gcve_records``); the node answers
the queries GCVE-BCP-03 defines on webs whose configuration names an organization
(``gcve_organization_id``), and renders GCVE Advisories with the built-in templates of the shipped
preset and type.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from lib.report import gcve

if TYPE_CHECKING:
    from types import SimpleNamespace

GNA = 65535
HOST = {"Host": "localhost"}


def _record(
    number: int,
    updated: str,
    *,
    published: str = "2026-10-01T00:00:00.000Z",
    cve: str | None = None,
    cwe: str | None = None,
) -> dict:
    metadata = {
        "state": "PUBLISHED",
        "assignerShortName": "TEST-GNA",
        "dateReserved": "2026-09-01T00:00:00.000Z",
        "datePublished": published,
        "dateUpdated": updated,
    }
    if cve:
        metadata["cveId"] = cve
    cna = {
        "descriptions": [{"lang": "en", "value": f"Vulnerability {number}"}],
        "affected": [{"vendor": "Example", "product": "Portal" if number % 2 else "Gateway", "defaultStatus": "unaffected"}],
        "references": [{"url": f"https://example.com/{number}"}],
        "x_gcve": [{"vulnId": f"GCVE-{GNA}-2026-{number:04d}", "recordType": "advisory"}],
    }
    if cwe:
        cna["problemTypes"] = [{"descriptions": [{"lang": "en", "cweId": cwe, "description": cwe, "type": "CWE"}]}]
    return {"dataType": "CVE_RECORD", "dataVersion": "5.2.0", "cveMetadata": metadata, "containers": {"cna": cna}}


RECORDS = [
    _record(1, "2026-10-02T10:00:00.000Z", cve="CVE-2026-1111", cwe="CWE-79"),
    _record(2, "2026-11-05T10:00:00.000Z", cwe="CWE-287"),
    _record(3, "2026-10-20T10:00:00.000Z", published="2026-10-20T10:00:00.000Z"),
]


@pytest.fixture
def gcve_web(site_client: SimpleNamespace) -> SimpleNamespace:
    """Web 1 publishes GCVE records; web 2 does not."""
    site_client.fake.webs[0]["config"].update({"gcve_organization_id": 1, "security_contact": "cert@example.org"})
    site_client.fake.gcve_records[1] = {
        "gna_id": GNA,
        "short_name": "TEST-GNA",
        "license": "CC-BY-4.0",
        "conformance": {"governance": {"has_public_disclosure_policy": True}},
        "total_count": len(RECORDS),
        "items": RECORDS,
    }
    return site_client


def _get(client: SimpleNamespace, path: str, host: dict | None = None) -> tuple[object, int, dict]:
    response = client.client.get(path, headers=host or HOST)
    body = response.get_json(silent=True)
    return body if body is not None else response.get_data(as_text=True), response.status_code, response.headers


def _ids(records: list[dict]) -> list[str]:
    return [record["containers"]["cna"]["x_gcve"][-1]["vulnId"] for record in records]


def test_the_records_are_a_bare_list_newest_update_first(gcve_web: SimpleNamespace) -> None:
    body, status, headers = _get(gcve_web, "/api/gcve/publication")

    assert status == HTTPStatus.OK
    assert _ids(body) == ["GCVE-65535-2026-0002", "GCVE-65535-2026-0003", "GCVE-65535-2026-0001"]
    # The records are public: any origin may read them.
    assert headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("since=2026-10-15", ["0002", "0003"]),
        ("since=20261101", ["0002"]),
        ("since=2026-10-20T10:00:00Z", ["0002", "0003"]),
        ("date_sort=published&sort_order=asc", ["0001", "0002", "0003"]),
        ("date_sort=reserved", ["0003", "0002", "0001"]),
        ("cwe=79", ["0001"]),
        ("cwe=CWE-287", ["0002"]),
        ("product=portal", ["0003", "0001"]),
        ("product=portal&assigner=test-gna", ["0003", "0001"]),
        ("product=portal&assigner=other", []),
        ("assigner=other", ["0002", "0003", "0001"]),
        (f"source=gna-{GNA}", ["0002", "0003", "0001"]),
        ("source=GHSA", []),
        ("per_page=2", ["0002", "0003"]),
        ("per_page=2&page=2", ["0001"]),
        ("per_page=2&page=3", []),
    ],
)
def test_the_query_of_gcve_bcp_03(gcve_web: SimpleNamespace, query: str, expected: list[str]) -> None:
    body, status, _headers = _get(gcve_web, f"/api/gcve/publication?{query}")

    assert status == HTTPStatus.OK
    assert [vuln_id.rsplit("-", 1)[1] for vuln_id in _ids(body)] == expected


def test_per_page_is_capped_at_100(gcve_web: SimpleNamespace) -> None:
    many = [_record(number, f"2026-10-{1 + number % 28:02d}T00:00:00.000Z") for number in range(1, 151)]
    gcve_web.fake.gcve_records[1]["items"] = many

    body, _status, _headers = _get(gcve_web, "/api/gcve/publication?per_page=500")
    assert len(body) == 100
    body, _status, _headers = _get(gcve_web, "/api/gcve/publication")
    assert len(body) == 30


def test_light_mode_gives_the_identifiers(gcve_web: SimpleNamespace) -> None:
    body, _status, _headers = _get(gcve_web, "/api/gcve/publication?light=true&sort_order=asc&date_sort=published")

    assert body == [["GCVE-65535-2026-0001", "CVE-2026-1111"], ["GCVE-65535-2026-0002", None], ["GCVE-65535-2026-0003", None]]


def test_the_identifier_is_read_where_each_record_has_it() -> None:
    advisory = _record(1, "2026-10-02T10:00:00.000Z")
    update = _record(2, "2026-10-02T10:00:00.000Z")
    update["containers"]["cna"]["x_gcve"] = [{"vulnId": "GCVE-65535-2026-0002", "recordType": "update", "relationships": []}]
    # A record built before the identifier left cveMetadata (its deprecated place).
    older = _record(3, "2026-10-02T10:00:00.000Z")
    older["containers"]["cna"]["x_gcve"] = []
    older["cveMetadata"]["vulnId"] = "GCVE-65535-2026-0003"

    assert [gcve.record_id(record) for record in (advisory, update, older)] == [
        "GCVE-65535-2026-0001",
        "GCVE-65535-2026-0002",
        "GCVE-65535-2026-0003",
    ]
    assert gcve.light([older]) == [["GCVE-65535-2026-0003", None]]


@pytest.mark.parametrize("query", ["since=yesterday", "date_sort=title", "sort_order=up", "per_page=many", "page=first"])
def test_a_query_that_cannot_be_understood_is_a_json_400(gcve_web: SimpleNamespace, query: str) -> None:
    body, status, _headers = _get(gcve_web, f"/api/gcve/publication?{query}")

    assert status == HTTPStatus.BAD_REQUEST
    assert body["error"]


def test_the_dump_has_every_record_one_per_line(gcve_web: SimpleNamespace) -> None:
    response = gcve_web.client.get(f"/dumps/gna-{GNA}.ndjson", headers=HOST)

    assert response.status_code == HTTPStatus.OK
    assert response.mimetype == "application/x-ndjson"
    lines = response.get_data(as_text=True).splitlines()
    assert _ids([json.loads(line) for line in lines]) == ["GCVE-65535-2026-0002", "GCVE-65535-2026-0003", "GCVE-65535-2026-0001"]

    body, status, _headers = _get(gcve_web, "/dumps/gna-1.ndjson")
    assert (status, body) == (HTTPStatus.NOT_FOUND, {"error": "Not found"})


def test_a_web_that_does_not_publish_gcve_records_says_so_in_json(gcve_web: SimpleNamespace) -> None:
    body, status, _headers = _get(gcve_web, "/api/gcve/publication", {"Host": "disinfo.localhost"})
    assert (status, body) == (HTTPStatus.NOT_FOUND, {"error": "This web does not publish GCVE records"})

    body, status, _headers = _get(gcve_web, "/api/gcve/publication", {"Host": "unknown.example"})
    assert (status, body) == (HTTPStatus.NOT_FOUND, {"error": "Not found"})

    # Its other pages are the site's as before.
    assert gcve_web.client.get("/", headers={"Host": "disinfo.localhost"}).status_code == HTTPStatus.OK


def test_records_core_cannot_serve_are_a_json_503(gcve_web: SimpleNamespace) -> None:
    del gcve_web.fake.gcve_records[1]

    body, status, _headers = _get(gcve_web, "/api/gcve/publication")

    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert "not available" in body["error"]


def test_security_txt_declares_the_endpoint(gcve_web: SimpleNamespace) -> None:
    body, status, headers = _get(gcve_web, "/.well-known/security.txt")

    assert status == HTTPStatus.OK
    assert headers["Content-Type"].startswith("text/plain")
    lines = body.splitlines()
    assert "Contact: mailto:cert@example.org" in lines
    assert "GCVE: https://localhost/api/gcve/publication" in lines
    assert "Canonical: https://localhost/.well-known/security.txt" in lines
    assert any(line.startswith("Expires: ") for line in lines)


def test_no_security_txt_without_a_contact(gcve_web: SimpleNamespace) -> None:
    del gcve_web.fake.webs[0]["config"]["security_contact"]

    _body, status, _headers = _get(gcve_web, "/.well-known/security.txt")

    assert status == HTTPStatus.NOT_FOUND


def test_the_conformance_document_of_gcve_bcp_06(gcve_web: SimpleNamespace) -> None:
    body, status, _headers = _get(gcve_web, "/api/gcve/conformance")

    assert status == HTTPStatus.OK
    assert body["gna_id"] == str(GNA)
    assert body["license"] == "CC-BY-4.0"
    assert body["governance"] == {"has_public_disclosure_policy": True}
    assert body["synchronization"]["sync_endpoint_url"] == "https://localhost/api/gcve/publication"
    assert body["allocation_quality"]["has_cwe_classification"] is True
    assert body["allocation_quality"]["identifier_reuse_detected"] is False
    assert body["interoperability"]["feed_format"] == ["json", "ndjson"]


# -- the pages of a GCVE Advisory -----------------------------------------------------------


def _attribute(key: str, label: str, attribute_type: str, value: str, data: dict | None = None, order: tuple = (0, 0)) -> dict:
    entry = {
        "key": key,
        "value": value,
        "description": None,
        "label": label,
        "group": "Vulnerability",
        "attribute_type": attribute_type,
        "multiple": key not in ("record_type", "description", "cve"),
        "order": list(order),
    }
    if data is not None:
        entry["data"] = data
    return entry


ADVISORY = {
    "id": 301,
    "title": "Portal advisory",
    "description": "",
    "links": ["https://example.com/advisory"],
    "created": "2026-11-08T10:00:00",
    "product_preset": {"id": 30, "title": "GCVE Advisory", "key": "gcve"},
    "user": {"name": "Jan Novak", "username": "jnovak"},
    "report_items": [
        {
            "title": "Login bypass",
            "title_prefix": "",
            "uuid": "cvd-301-1",
            "created": "2026-11-01T08:00:00",
            "last_updated": "2026-11-08T09:00:00",
            "type": "CVD Report",
            "type_id": 7,
            "type_key": "cvd",
            "gcve_id": "GCVE-65535-2026-0001",
            "type_description": "Coordinated Vulnerability Disclosure",
            "attributes": [
                _attribute("record_type", "Record type", "RADIO", "advisory"),
                _attribute("cve", "CVE", "CVE", "CVE-2026-1111", order=(0, 1)),
                _attribute("description", "Description", "RICH_TEXT", "<p>Anyone can log in [1].</p>", order=(1, 0)),
                _attribute(
                    "affected_products",
                    "Affected products",
                    "AFFECTED",
                    "Example Portal: 1.0 to before 1.4.2 (affected)",
                    {
                        "vendor": "Example",
                        "product": "Portal",
                        "versions": [{"version": "1.0", "lessThan": "1.4.2", "status": "affected", "versionType": "semver"}],
                    },
                    order=(1, 1),
                ),
                _attribute("cvss", "CVSS", "CVSS", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", order=(1, 2)),
                _attribute(
                    "credits",
                    "Credits",
                    "CREDIT",
                    "Example Researcher (finder)",
                    {"value": "Example Researcher", "type": "finder"},
                    order=(4, 1),
                ),
                _attribute(
                    "references",
                    "References",
                    "REFERENCE",
                    "Vendor advisory <https://example.com/advisory>",
                    {"url": "https://example.com/advisory", "name": "Vendor advisory", "tags": ["vendor-advisory"]},
                    order=(5, 0),
                ),
            ],
        },
    ],
}


@pytest.fixture
def advisory(gcve_web: SimpleNamespace) -> SimpleNamespace:
    gcve_web.fake.products[301] = json.loads(json.dumps(ADVISORY))
    return gcve_web


def test_a_gcve_advisory_has_a_page_with_its_record(advisory: SimpleNamespace) -> None:
    page = advisory.client.get("/reports/301", headers=HOST).get_data(as_text=True)

    assert "GCVE-65535-2026-0001" in page
    assert "Login bypass" in page
    assert "Anyone can log in" in page
    assert "Portal" in page
    assert "1.4.2" in page
    assert "Example Researcher (finder)" in page
    assert "Vendor advisory" in page
    assert "https://cve.org/CVERecord?id=CVE-2026-1111" in page


def test_a_range_shows_where_its_status_changes(gcve_web: SimpleNamespace) -> None:
    product = json.loads(json.dumps(ADVISORY))
    affected = next(entry for entry in product["report_items"][0]["attributes"] if entry["key"] == "affected_products")
    affected["data"]["versions"][0]["changes"] = [{"at": "1.2.0", "status": "unaffected"}]
    gcve_web.fake.products[301] = product

    page = gcve_web.client.get("/reports/301", headers=HOST).get_data(as_text=True)

    assert re.search(r"from 1\.2\.0:\s*not affected", page)


def test_the_homepage_names_the_gcve_identifiers(advisory: SimpleNamespace) -> None:
    page = advisory.client.get("/", headers=HOST).get_data(as_text=True)

    assert "Portal advisory" in page
    assert "GCVE-65535-2026-0001" in page


def test_a_gcve_advisory_needs_no_tlp(advisory: SimpleNamespace) -> None:
    # The fixture's other products carry TLP:CLEAR; a GCVE Advisory has none and is shown all the same.
    response = advisory.client.get("/reports/301", headers=HOST)

    assert response.status_code == HTTPStatus.OK


# -- a tab per type of reports ---------------------------------------------------------------------
#
# With the advisory, web 1 shows two types: the GCVE Advisories (``?type=gcve``, the preset's key)
# and the vulnerability reports (``?type=10``, the preset's id). Every page lists all by default.

TAB = re.compile(r'<a class="nav-link([^"]*)"\s*(aria-current="page")?\s*href="([^"]*)"\s*data-test="report-type">(.*?)</a>', re.DOTALL)


def _tabs(page: str) -> list[tuple[str, str, bool]]:
    """(label, address, active) of each tab."""
    return [
        (re.sub(r"<[^>]+>", "", label).strip(), href.replace("&amp;", "&"), "active" in classes and bool(current))
        for classes, current, href, label in TAB.findall(page)
    ]


def _page(client: SimpleNamespace, path: str) -> tuple[str, int]:
    response = client.client.get(path, headers=HOST)
    return response.get_data(as_text=True), response.status_code


def test_one_type_of_reports_needs_no_tabs(gcve_web: SimpleNamespace) -> None:
    page, _status = _page(gcve_web, "/")

    assert 'data-test="report-types"' not in page


def test_several_types_get_a_tab_each_after_all(advisory: SimpleNamespace) -> None:
    page, _status = _page(advisory, "/")

    assert _tabs(page) == [
        ("All", "/", True),
        ("GCVE Advisory", "/?type=gcve", False),
        ("Vulnerability Report", "/?type=10", False),
    ]
    # All of them, as before.
    assert "Portal advisory" in page
    assert "OpenSSL denial of service" in page


def test_a_tab_lists_its_type_only(advisory: SimpleNamespace) -> None:
    gcve, _status = _page(advisory, "/?type=gcve")
    reports, _status = _page(advisory, "/?type=10")

    assert "Portal advisory" in gcve
    assert "OpenSSL denial of service" not in gcve
    assert [active for _label, _href, active in _tabs(gcve)] == [False, True, False]
    assert "OpenSSL denial of service" in reports
    assert "Portal advisory" not in reports


def test_a_type_the_web_does_not_show_is_not_found(advisory: SimpleNamespace) -> None:
    assert _page(advisory, "/?type=20")[1] == HTTPStatus.NOT_FOUND
    assert _page(advisory, "/?type=nonsense")[1] == HTTPStatus.NOT_FOUND


def test_a_search_stays_within_its_tab(advisory: SimpleNamespace) -> None:
    page, _status = _page(advisory, "/?type=10&search=OpenSSL")

    assert '<input type="hidden" name="type" value="10">' in page
    assert "OpenSSL denial of service" in page
    assert "Critical  vulnerabilities in Apache" not in page
    # The tabs keep the search, and the page links keep the tab.
    assert ("GCVE Advisory", "/?type=gcve&search=OpenSSL", False) in _tabs(page)
    assert "/?type=10&amp;search=OpenSSL&amp;page=1" in page


def test_the_gcve_tab_points_to_the_gcve_records(advisory: SimpleNamespace) -> None:
    gcve, _status = _page(advisory, "/?type=gcve")
    reports, _status = _page(advisory, "/?type=10")
    every, _status = _page(advisory, "/")

    assert 'href="/api/gcve/publication" data-test="gcve-records-publication"' in gcve
    assert 'href="/dumps/gna-65535.ndjson" data-test="gcve-records-dump"' in gcve
    assert 'data-test="gcve-records"' not in reports
    assert 'data-test="gcve-records"' not in every


def test_a_tab_offers_the_feeds_of_its_type(advisory: SimpleNamespace) -> None:
    gcve, _status = _page(advisory, "/?type=gcve")
    every, _status = _page(advisory, "/")

    # Web 1 has two languages, so each feed names its language too: after the type, as its own address does.
    assert 'href="/rss?type=gcve&amp;lang=en"' in gcve
    assert 'href="https://localhost/atom?type=gcve&amp;lang=cs"' in gcve
    assert 'data-test="feed-type"><bdi dir="auto">GCVE Advisory</bdi>' in gcve
    assert "?type=" not in re.sub(r'href="/\?type=[^"]*"', "", every)


def test_the_feed_of_a_type_lists_that_type_only(advisory: SimpleNamespace) -> None:
    response = advisory.client.get("/atom?type=gcve", headers=HOST)
    root = ET.fromstring(response.get_data())  # noqa: S314 (our own output)
    atom = "{http://www.w3.org/2005/Atom}"

    assert response.status_code == HTTPStatus.OK
    assert [entry.findtext(f"{atom}title") for entry in root.findall(f"{atom}entry")] == ["Portal advisory"]
    assert root.findtext(f"{atom}title").endswith("GCVE Advisory")
    assert {link.get("rel"): link.get("href") for link in root.findall(f"{atom}link")}["self"] == "https://localhost/atom?type=gcve"
    assert advisory.client.get("/rss?type=nonsense", headers=HOST).status_code == HTTPStatus.NOT_FOUND
    assert response.headers["ETag"] != advisory.client.get("/atom", headers=HOST).headers["ETag"]
