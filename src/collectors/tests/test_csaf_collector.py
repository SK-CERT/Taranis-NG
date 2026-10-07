"""Tests for the CSAF collector.

The collector reads five kinds of listing - provider metadata, a directory with changes.csv, a
ROLIE feed, an RSS/Atom feed and a GitHub repository - and turns each CSAF 2.0 or 2.1 document
into a news item. Nothing here touches the network: a fake fetcher answers from a map of URLs,
and documents are signed at test time with a key generated for the run.

The fixtures follow the OASIS schemas (csaf_2.0/json_schema, csaf_2.1/json_schema), and the
listing shapes mirror what real providers serve (Red Hat, Cisco, BSI, ABB, Oracle, NVIDIA,
Intel, CISA, OPC Foundation).
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import re
import types
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from collectors.csaf_collector import CSAFCollector
from collectors.csaf_sources import (
    FAILED,
    NOT_MODIFIED,
    OK,
    RATE_LIMITED,
    RESTRICTED,
    DirectoryListing,
    FeedListing,
    Fetcher,
    GitHubListing,
    GitHubRepo,
    Resolver,
    Response,
    RolieListing,
    directory_url,
    parse_github_url,
    rewrite_github_blob,
)
from pysequoia import SignatureMode, Tsk, sign
from shared.common import ALLOWED_HTML_TAGS
from shared.schema import news_item

from collectors import csaf_document, csaf_integrity

if TYPE_CHECKING:
    from collections.abc import Callable

UTC = datetime.UTC


class RecordingLogger:
    """Stand-in for the per-source logger, keeping what was logged for assertions."""

    def __init__(self) -> None:
        """Start with an empty record for every level a collector logs at."""
        self.messages: dict[str, list[str]] = {level: [] for level in ("debug", "info", "warning", "error", "exception", "critical")}

    def __getattr__(self, level: str) -> Callable[[str], None]:
        """Return a logging call for any level, recording what it is given."""

        def record(message: str = "") -> None:
            self.messages.setdefault(level, []).append(str(message))

        return record


class FakeFetcher:
    """Answers GETs from a map of URLs, honouring ETags; unknown URLs answer 404."""

    def __init__(self) -> None:
        """Start empty."""
        self.routes: dict[str, object] = {}
        self.requests: list[tuple[str, dict]] = []

    def add(self, url: str, body: object = b"", status: int = 200, headers: dict | None = None) -> None:
        """Serve a body (bytes, str, or anything JSON) at a URL."""
        if isinstance(body, str):
            body = body.encode()
        elif not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.routes[url] = (status, body, {name.lower(): value for name, value in (headers or {}).items()})

    def get(self, url: str, *, headers: dict | None = None, max_bytes: int = 0) -> Response:  # noqa: ARG002
        """Answer like Fetcher.get."""
        headers = dict(headers or {})
        self.requests.append((url, headers))
        route = self.routes.get(url)
        if route is None:
            route = next((value for key, value in self.routes.items() if key.endswith("*") and url.startswith(key[:-1])), None)
        if route is None:
            return Response(404, url=url)
        if callable(route):
            return route(url, headers)
        status, body, route_headers = route
        if route_headers.get("etag") and headers.get("If-None-Match") == route_headers["etag"]:
            return Response(304, b"", route_headers, url)
        if not 200 <= status < 300:
            return Response(status, b"", route_headers, url)
        return Response(status, body, route_headers, url)

    def fetched(self, suffix: str = ".json") -> list[str]:
        """URLs requested that end with a suffix, in order."""
        return [url for url, _headers in self.requests if url.lower().endswith(suffix)]


# --- CSAF fixtures -------------------------------------------------------------------------

CVSS_V3 = {"version": "3.1", "baseScore": 9.8, "baseSeverity": "CRITICAL", "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}
CVSS_V4 = {
    "version": "4.0",
    "baseScore": 8.7,
    "baseSeverity": "HIGH",
    "vectorString": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
}


def vulnerability_20(cve: str = "CVE-2026-0001", score: float = 9.8) -> dict:
    """A CSAF 2.0 vulnerability: `cwe`, `scores`, `release_date`."""
    return {
        "cve": cve,
        "title": "Remote code execution",
        "cwe": {"id": "CWE-79", "name": "Improper Neutralization of Input"},
        "scores": [{"cvss_v3": {**CVSS_V3, "baseScore": score}, "products": ["P1"]}],
        "release_date": "2026-09-01T00:00:00Z",
        "product_status": {"known_affected": ["P1"], "fixed": ["P2"]},
        "remediations": [{"category": "vendor_fix", "details": "Update to 2.0.", "url": "https://example.com/fix", "product_ids": ["P1"]}],
        "notes": [{"category": "description", "text": "Details of the flaw."}],
    }


def vulnerability_21(cve: str = "CVE-2026-0002") -> dict:
    """A CSAF 2.1 vulnerability: `cwes`, `metrics` with CVSS v3/v4, EPSS and a rating."""
    return {
        "cve": cve,
        "title": "Privilege escalation",
        "cwes": [{"id": "CWE-269", "name": "Improper Privilege Management", "version": "4.14"}],
        "metrics": [
            {
                "content": {
                    "cvss_v3": CVSS_V3,
                    "cvss_v4": CVSS_V4,
                    "epss": {"probability": "0.42", "percentile": "0.97", "timestamp": "2026-09-01T00:00:00Z"},
                    "qualitative_severity_rating": "critical",
                },
                "products": ["P1"],
            },
        ],
        "disclosure_date": "2026-08-30T00:00:00Z",
        "first_known_exploitation_dates": [{"date": "2026-09-02T00:00:00Z", "exploitation_date": "2026-08-31T00:00:00Z"}],
        "product_status": {"known_affected": ["P1"]},
    }


def csaf(
    tracking_id: str = "EX-2026-001",
    version: str = "1",
    released: str = "2026-09-01T10:00:00Z",
    *,
    csaf_version: str = "2.0",
    category: str = "csaf_security_advisory",
    lang: str | None = None,
    tlp: str = "WHITE",
    vulnerabilities: list | None = None,
    product_tree: bool = True,
    **document: object,
) -> dict:
    """A minimal valid CSAF document of either version."""
    data = {
        "document": {
            "category": category,
            "csaf_version": csaf_version,
            "title": "Example product vulnerabilities",
            "publisher": {"category": "vendor", "name": "Example PSIRT", "namespace": "https://example.com"},
            "distribution": {"tlp": {"label": tlp, "url": "https://www.first.org/tlp/"}},
            "notes": [
                {"category": "summary", "text": "Two flaws in Example Product."},
                {"category": "legal_disclaimer", "text": "Provided as is."},
            ],
            "references": [
                {"category": "self", "url": f"https://example.com/advisories/{tracking_id.lower()}.json"},
                {"category": "self", "url": f"https://example.com/advisories/{tracking_id}", "summary": "Advisory page"},
            ],
            "tracking": {
                "id": tracking_id,
                "version": version,
                "status": "final",
                "initial_release_date": "2026-08-01T10:00:00Z",
                "current_release_date": released,
                "revision_history": [{"number": version, "date": released, "summary": "Current"}],
            },
            **document,
        },
        "vulnerabilities": vulnerabilities if vulnerabilities is not None else [vulnerability_20()],
    }
    if csaf_version == "2.1":
        data["$schema"] = "https://docs.oasis-open.org/csaf/csaf/v2.1/schema/csaf.json"
    if lang:
        data["document"]["lang"] = lang
    if product_tree:
        data["product_tree"] = {
            "branches": [
                {
                    "category": "vendor",
                    "name": "Example",
                    "branches": [
                        {"category": "product_version", "name": "1.0", "product": {"product_id": "P1", "name": "Example Product 1.0"}},
                        {"category": "product_version", "name": "2.0", "product": {"product_id": "P2", "name": "Example Product 2.0"}},
                    ],
                },
            ],
        }
    return data


def body_of(data: dict) -> bytes:
    return json.dumps(data, indent=2).encode()


@pytest.fixture(scope="module")
def signing_key() -> Tsk:
    """A key generated for the run, standing in for a provider's."""
    return Tsk.generate("Example PSIRT <psirt@example.com>")


@pytest.fixture(scope="module")
def foreign_key() -> Tsk:
    """A key the collector does not know."""
    return Tsk.generate("Someone Else <else@example.org>")


def detached(key: Tsk, data: bytes) -> bytes:
    return bytes(sign(key.signer(), data, mode=SignatureMode.DETACHED))


def public_key(key: Tsk) -> bytes:
    return str(key.extract_certificate()).encode()


# --- a directory provider ------------------------------------------------------------------

BASE = "https://csaf.example.com/csaf/"
METADATA = "https://example.com/.well-known/csaf/provider-metadata.json"
KEY_URL = "https://example.com/csaf/key.asc"


class Provider:
    """A directory-based CSAF provider served by a FakeFetcher."""

    def __init__(self, fetcher: FakeFetcher, key: Tsk, *, etag: str | None = None, other_distributions: tuple[str, ...] = ()) -> None:
        """Publish the metadata and key; documents are added with `publish`."""
        self.fetcher = fetcher
        self.key = key
        self.rows: dict[str, str] = {}
        self.etag = etag
        fetcher.add(
            METADATA,
            {
                "canonical_url": METADATA,
                "metadata_version": "2.0",
                "role": "csaf_trusted_provider",
                "distributions": [{"directory_url": url} for url in (BASE, *other_distributions)],
                "public_openpgp_keys": [{"fingerprint": key.extract_certificate().fingerprint.upper(), "url": KEY_URL}],
                "publisher": {"category": "vendor", "name": "Example PSIRT", "namespace": "https://example.com"},
            },
        )
        fetcher.add(KEY_URL, public_key(key))
        self._write_changes()

    def publish(self, path: str, data: dict, changed: str, *, signed: bool = True, hashed: bool = True) -> bytes:
        """Serve a document with its hash and signature, and list it in changes.csv."""
        body = body_of(data)
        url = BASE + path
        self.fetcher.add(url, body)
        if hashed:
            self.fetcher.add(url + ".sha512", f"{hashlib.sha512(body).hexdigest()}  {path.rsplit('/', 1)[-1]}\n")
        if signed:
            self.fetcher.add(url + ".asc", detached(self.key, body))
        self.rows[path] = changed
        self._write_changes()
        return body

    def _write_changes(self) -> None:
        rows = sorted(self.rows.items(), key=lambda row: row[1], reverse=True)
        headers = {"ETag": self.etag} if self.etag else {}
        self.fetcher.add(BASE + "changes.csv", "".join(f'"{path}","{changed}"\n' for path, changed in rows), headers=headers)


def make_source(csaf_url: str = "example.com", **params: str) -> types.SimpleNamespace:
    values = {
        "CSAF_URL": csaf_url,
        "USER_AGENT": "",
        "PROXY_SERVER": "",
        "PUBLIC_KEY_URLS": "",
        "SKIP_CATEGORIES": "csaf_vex",
        "MAX_DOCUMENTS": "100",
        "VERIFY_SIGNATURES": "true",
        "CHECK_IF_MODIFIED": "true",
        "RESURFACE_NEW_VERSIONS": "true",
        "REFRESH_INTERVAL": "60",
    }
    values.update(params)
    return types.SimpleNamespace(id="source-1", name="Example CSAF", word_lists=[], last_collected=None, param_key_values=values)


class Harness:
    """Runs the collector against a fake fetcher, recording what it publishes."""

    def __init__(self, fetcher: FakeFetcher, source: types.SimpleNamespace) -> None:
        """Keep the fetcher and source; each `run` is one scheduled collection."""
        self.fetcher = fetcher
        self.source = source
        self.published: list[list] = []
        self.accept = True
        self.rejection: tuple = ({"error": "Add news items failed"}, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.logger = RecordingLogger()

    def run(self) -> list:
        """Collect once, as `run_collector` does, and return the items published by this run."""
        runner = CSAFCollector()
        runner._initialize_source(self.source)
        self.source.logger = self.logger
        runner.fetcher = self.fetcher
        before = len(self.published)

        def publish(items: list) -> object:
            self.published.append(list(items))
            return HTTPStatus.OK if self.accept else self.rejection

        runner.publish = publish
        runner.collect()
        return [item for chunk in self.published[before:] for item in chunk]


@pytest.fixture(autouse=True)
def fresh_state() -> None:
    """Per-source state lives on the class; start every test without it."""
    CSAFCollector._states.clear()
    yield
    CSAFCollector._states.clear()


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher()


def attrs(item: object) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for attribute in item.attributes:
        result.setdefault(attribute.key, []).append(attribute.value)
    return result


# --- resolving a CSAF URL ------------------------------------------------------------------


def test_a_domain_is_discovered_through_its_well_known_metadata(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    Provider(fetcher, signing_key)
    resolution = Resolver(fetcher).resolve("example.com")
    assert [type(listing) for listing in resolution.listings] == [DirectoryListing]
    assert resolution.listings[0].url == BASE
    assert resolution.key_urls == [(KEY_URL, signing_key.extract_certificate().fingerprint.upper())]


def test_a_domain_is_discovered_through_security_txt(fetcher: FakeFetcher) -> None:
    fetcher.add(
        "https://example.org/.well-known/security.txt",
        "Contact: mailto:psirt@example.org\nCSAF: https://example.org/data/provider-metadata.json\n",
    )
    fetcher.add("https://example.org/data/provider-metadata.json", {"distributions": [{"directory_url": "https://example.org/data/csaf/"}]})
    resolution = Resolver(fetcher).resolve("https://example.org/")
    assert [listing.url for listing in resolution.listings] == ["https://example.org/data/csaf/"]


def test_metadata_of_both_versions_is_read(fetcher: FakeFetcher) -> None:
    fetcher.add(
        "https://example.net/provider-metadata.json",
        {
            "metadata_version": "2.1",
            "distributions": [
                {"directory": {"url": "https://example.net/csaf/white", "tlp_label": "CLEAR"}},
                {"directory_url": "https://example.net/csaf/v20/"},
                {
                    "rolie": {
                        "feeds": [
                            {"url": "https://example.net/feed-green.json", "tlp_label": "GREEN", "last_updated": "2026-09-01T00:00:00Z"},
                        ],
                    },
                },
            ],
        },
    )
    listings = Resolver(fetcher).resolve("https://example.net/provider-metadata.json").listings
    assert [(listing.kind, listing.url, listing.tlp) for listing in listings] == [
        ("directory", "https://example.net/csaf/white/", "CLEAR"),
        ("directory", "https://example.net/csaf/v20/", ""),
        ("rolie", "https://example.net/feed-green.json", "GREEN"),
    ]
    assert listings[2].access_controlled
    assert not listings[0].access_controlled


def test_a_directory_url_without_a_trailing_slash_keeps_its_last_folder() -> None:
    # Microsoft lists https://msrc.microsoft.com/csaf/advisories - without the slash, urljoin
    # would resolve 2026/x.json against /csaf/ and drop "advisories".
    assert directory_url("https://msrc.microsoft.com/csaf/advisories") == "https://msrc.microsoft.com/csaf/advisories/"
    assert directory_url("https://example.com/csaf/changes.csv") == "https://example.com/csaf/"


def test_the_keys_of_a_feed_are_found_in_the_metadata_above_it(fetcher: FakeFetcher) -> None:
    # Red Hat and Siemens keep provider-metadata.json next to their distributions, not in .well-known.
    fetcher.add("https://example.com/product/csaf/feed.json", {"feed": {"entry": []}})
    fetcher.add(
        "https://example.com/product/csaf/provider-metadata.json",
        {"distributions": [], "public_openpgp_keys": [{"url": "https://example.com/k.asc"}]},
    )
    resolution = Resolver(fetcher).resolve("https://example.com/product/csaf/feed.json")
    assert isinstance(resolution.listings[0], RolieListing)
    assert resolution.key_urls == [("https://example.com/k.asc", None)]


def test_an_rss_feed_is_recognised(fetcher: FakeFetcher) -> None:
    fetcher.add(
        "https://example.com/alerts.xml",
        '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>',
        headers={"Content-Type": "text/xml"},
    )
    assert isinstance(Resolver(fetcher).resolve("https://example.com/alerts.xml").listings[0], FeedListing)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/nvidia/product-security", GitHubRepo("nvidia", "product-security")),
        ("https://github.com/intel/security-center/tree/main/advisories", GitHubRepo("intel", "security-center", "main", "advisories")),
        (
            "https://github.com/OPCFoundation/OPC-SecurityAdvisories/blob/latest/keys/OPC%20Key_public.asc",
            "https://raw.githubusercontent.com/OPCFoundation/OPC-SecurityAdvisories/latest/keys/OPC%20Key_public.asc",
        ),
        ("https://example.com/csaf/", None),
    ],
)
def test_github_urls_are_read(url: str, expected: object) -> None:
    assert parse_github_url(url) == expected


def test_a_github_page_url_is_rewritten_to_the_file() -> None:
    assert rewrite_github_blob("https://github.com/o/r/blob/main/csaf") == "https://raw.githubusercontent.com/o/r/main/csaf"
    assert rewrite_github_blob("https://example.com/csaf/key.asc") == "https://example.com/csaf/key.asc"


def github_tree(fetcher: FakeFetcher, owner: str, repo: str, paths: dict[str, str], ref: str = "HEAD", etag: str | None = None) -> None:
    fetcher.add(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1",
        {"truncated": False, "tree": [{"path": path, "type": "blob", "sha": sha} for path, sha in paths.items()]},
        headers={"ETag": etag} if etag else None,
    )


def test_a_repository_with_changes_csv_folders_is_read_as_directories(fetcher: FakeFetcher) -> None:
    # CISA keeps standard directories in its repository.
    github_tree(
        fetcher,
        "cisagov",
        "CSAF",
        {
            "README.md": "a",
            "csaf_files/IT/white/changes.csv": "b",
            "csaf_files/OT/white/changes.csv": "c",
            "csaf_files/OT/white/2026/x.json": "d",
        },
    )
    listings = Resolver(fetcher).resolve("https://github.com/cisagov/CSAF").listings
    assert [(listing.kind, listing.url) for listing in listings] == [
        ("directory", "https://raw.githubusercontent.com/cisagov/CSAF/HEAD/csaf_files/IT/white/"),
        ("directory", "https://raw.githubusercontent.com/cisagov/CSAF/HEAD/csaf_files/OT/white/"),
    ]


def test_keys_come_from_metadata_kept_in_the_repository(fetcher: FakeFetcher) -> None:
    # OPC Foundation's metadata points at github.com pages, which are HTML, not the key.
    github_tree(fetcher, "o", "r", {"csaf-provider-metadata.json": "a", "csaf/2026/001/A.json": "b"})
    fetcher.add(
        "https://raw.githubusercontent.com/o/r/HEAD/csaf-provider-metadata.json",
        {
            "distributions": [{"directory_url": "https://github.com/o/r/blob/latest/csaf"}],
            "public_openpgp_keys": [{"fingerprint": "AB", "url": "https://github.com/o/r/blob/latest/keys/k.asc"}],
        },
    )
    resolution = Resolver(fetcher).resolve("https://github.com/o/r")
    assert [type(listing) for listing in resolution.listings] == [GitHubListing]
    assert resolution.key_urls == [("https://raw.githubusercontent.com/o/r/latest/keys/k.asc", "AB")]


def test_a_github_listing_finds_documents_and_their_integrity_files(fetcher: FakeFetcher) -> None:
    github_tree(
        fetcher,
        "o",
        "r",
        {
            "2026/5885/5885.json": "s1",
            "2026/5885/5885.json.sha256": "h1",
            "2026/5885/5885.md": "m1",
            "2026/5885/CVE-2026-24267.json": "c1",
            "advisories/INTEL-SA-01499.JSON": "s2",
            "advisories/INTEL-SA-01499-JSON.sha256": "h2",
            "csaf/2017/1/OPC_CSAF_CVE-2017-11672.json": "s3",
            "csaf/2017/1/OPC_CSAF_CVE-2017-11672.json.sha512": "h3",
            "csaf/2017/1/OPC_CSAF_CVE-2017-11672.json.asc": "a3",
            "csaf-provider-metadata.json": "p",
        },
    )
    result = GitHubListing(GitHubRepo("o", "r")).list_changes(fetcher, (None, None))
    changes = {change.key: change for change in result.changes}
    # NVIDIA's CVE record and the provider metadata are not advisories; OPC's file keeps its CVE in the middle.
    assert sorted(changes) == ["2026/5885/5885.json", "advisories/INTEL-SA-01499.JSON", "csaf/2017/1/OPC_CSAF_CVE-2017-11672.json"]
    raw = "https://raw.githubusercontent.com/o/r/HEAD/"
    assert changes["2026/5885/5885.json"].hash_urls == [raw + "2026/5885/5885.json.sha256"]
    assert changes["2026/5885/5885.json"].page_url == "https://github.com/o/r/blob/HEAD/2026/5885/5885.md"
    assert changes["advisories/INTEL-SA-01499.JSON"].hash_urls == [raw + "advisories/INTEL-SA-01499-JSON.sha256"]
    opc = changes["csaf/2017/1/OPC_CSAF_CVE-2017-11672.json"]
    assert (opc.hash_urls, opc.signature_url, opc.probe) == (
        [raw + "csaf/2017/1/OPC_CSAF_CVE-2017-11672.json.sha512"],
        raw + "csaf/2017/1/OPC_CSAF_CVE-2017-11672.json.asc",
        False,
    )
    assert opc.blob_sha == "s3"


def test_a_github_folder_limits_the_listing(fetcher: FakeFetcher) -> None:
    github_tree(fetcher, "intel", "security-center", {"advisories/INTEL-SA-1.JSON": "a", "vex/INTEL-SA-1.json": "b"}, ref="main")
    result = GitHubListing(GitHubRepo("intel", "security-center", "main", "advisories")).list_changes(fetcher, (None, None))
    assert [change.key for change in result.changes] == ["advisories/INTEL-SA-1.JSON"]


# --- reading listings ----------------------------------------------------------------------


def test_changes_csv_is_read_with_its_times(fetcher: FakeFetcher) -> None:
    fetcher.add(
        BASE + "changes.csv",
        '"2026/b.json","2026-09-02T10:00:00.000000Z"\n2026/a.json,2026-09-01T10:00:00Z\n',
        headers={"ETag": '"v1"'},
    )
    result = DirectoryListing(BASE).list_changes(fetcher, (None, None))
    assert result.status == OK
    assert [(change.url, change.changed_at) for change in result.changes] == [
        (BASE + "2026/b.json", datetime.datetime(2026, 9, 2, 10, tzinfo=UTC)),
        (BASE + "2026/a.json", datetime.datetime(2026, 9, 1, 10, tzinfo=UTC)),
    ]
    assert result.etag == '"v1"'
    assert DirectoryListing(BASE).list_changes(fetcher, ('"v1"', None)).status == NOT_MODIFIED


@pytest.mark.parametrize(
    ("status", "tlp", "expected"),
    [
        (204, None, OK),
        (401, None, RESTRICTED),
        (403, None, RESTRICTED),
        (404, None, FAILED),
        # A TLP:GREEN listing answering 404 is access control, not a broken listing (BSI).
        (404, "GREEN", RESTRICTED),
        (500, None, FAILED),
    ],
)
def test_listing_answers_are_classified(fetcher: FakeFetcher, status: int, tlp: str | None, expected: str) -> None:
    fetcher.add(BASE + "changes.csv", b"", status=status)
    result = DirectoryListing(BASE, tlp).list_changes(fetcher, (None, None))
    assert result.status == expected
    assert result.changes == []


def test_a_github_rate_limit_is_reported(fetcher: FakeFetcher) -> None:
    fetcher.add(
        "https://api.github.com/repos/o/r/git/trees/HEAD?recursive=1",
        b"",
        status=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1790000000"},
    )
    result = GitHubListing(GitHubRepo("o", "r")).list_changes(fetcher, (None, None))
    assert result.status == RATE_LIMITED
    assert "rate limit" in result.message


def test_a_rolie_entry_names_its_hashes_best_first(fetcher: FakeFetcher) -> None:
    # ABB lists both a SHA-256 and a SHA-512 file; BSI states the document category.
    fetcher.add(
        "https://example.com/feed.json",
        {
            "feed": {
                "entry": [
                    {
                        "id": "X",
                        "updated": "2026-09-23T04:15:00Z",
                        "content": {"src": "https://example.com/2026/x.json", "type": "application/json"},
                        "link": [
                            {"rel": "self", "href": "https://example.com/2026/x.json"},
                            {"rel": "hash", "href": "https://example.com/2026/x.json.sha256"},
                            {"rel": "signature", "href": "https://example.com/2026/x.json.asc"},
                            {"rel": "hash", "href": "https://example.com/2026/x.json.sha512"},
                        ],
                        "category": [
                            {
                                "scheme": "https://docs.oasis-open.org/csaf/csaf/v2.0/os/csaf-v2.0-os.html#3122?document_category",
                                "term": "csaf_vex",
                            },
                        ],
                    },
                ],
            },
        },
    )
    (change,) = RolieListing("https://example.com/feed.json").list_changes(fetcher, (None, None)).changes
    assert change.hash_urls == ["https://example.com/2026/x.json.sha512", "https://example.com/2026/x.json.sha256"]
    assert change.signature_url == "https://example.com/2026/x.json.asc"
    assert change.category == "csaf_vex"
    assert change.changed_at == datetime.datetime(2026, 9, 23, 4, 15, tzinfo=UTC)


def test_an_rss_feed_links_its_documents(fetcher: FakeFetcher) -> None:
    # Oracle pads the <link> text with whitespace.
    fetcher.add(
        "https://example.com/alerts.xml",
        """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Alerts</title>
  <item><title>September</title>
    <link>https://example.com/docs/cpusep2026csaf.json
          </link>
    <pubDate>Tue, 15 Sep 2026 13:00:00 -0700</pubDate></item>
  <item><title>A web page</title><link>https://example.com/alerts.html</link><pubDate>Tue, 15 Sep 2026 13:00:00 -0700</pubDate></item>
</channel></rss>""",
    )
    (change,) = FeedListing("https://example.com/alerts.xml").list_changes(fetcher, (None, None)).changes
    assert change.url == "https://example.com/docs/cpusep2026csaf.json"
    assert change.changed_at == datetime.datetime(2026, 9, 15, 20, 0, tzinfo=UTC)


def test_only_http_urls_are_fetched() -> None:
    response = Fetcher().get("file:///etc/passwd")
    assert response.status == 0
    assert "http" in response.error


# --- integrity -----------------------------------------------------------------------------

DOCUMENT = b'{\n  "document": {}\n}\n'


@pytest.mark.parametrize(
    "hash_file",
    [
        f"{hashlib.sha512(DOCUMENT).hexdigest()}  x.json\n".encode(),
        hashlib.sha512(DOCUMENT).hexdigest().encode(),
        # certutil on Windows: UTF-16, the digest on a line of its own (OPC Foundation).
        f"SHA512 hash of x.json:\r\n{hashlib.sha512(DOCUMENT).hexdigest()}\r\nCertUtil: -hashfile command completed successfully.\r\n".encode(
            "utf-16",
        ),
    ],
)
def test_hash_files_are_read_in_every_format_seen(hash_file: bytes) -> None:
    assert csaf_integrity.check_digest(DOCUMENT, csaf_integrity.parse_digest(hash_file)) == csaf_integrity.VALID


def test_a_page_served_for_a_missing_hash_file_is_not_a_hash() -> None:
    assert csaf_integrity.parse_digest(b"<!DOCTYPE html><html><body>Not found</body></html>") is None


def test_hash_results() -> None:
    assert csaf_integrity.check_digest(DOCUMENT, hashlib.sha256(DOCUMENT).hexdigest()) == csaf_integrity.VALID
    assert csaf_integrity.check_digest(DOCUMENT + b" ", hashlib.sha256(DOCUMENT).hexdigest()) == csaf_integrity.MISMATCH
    assert csaf_integrity.check_digest(DOCUMENT, None) == csaf_integrity.MISSING


def test_a_document_hashed_with_windows_line_endings_is_valid() -> None:
    # Hashed and signed on Windows, served by Git with LF (OPC Foundation).
    crlf = DOCUMENT.replace(b"\n", b"\r\n")
    assert csaf_integrity.check_digest(DOCUMENT, hashlib.sha512(crlf).hexdigest()) == csaf_integrity.VALID


def test_signature_results(signing_key: Tsk, foreign_key: Tsk) -> None:
    keys = csaf_integrity.KeyRing()
    assert keys.add(public_key(signing_key), signing_key.extract_certificate().fingerprint, origin="test")
    assert keys.verify(DOCUMENT, detached(signing_key, DOCUMENT)) == csaf_integrity.VALID
    assert keys.verify(DOCUMENT + b"tampered", detached(signing_key, DOCUMENT)) == csaf_integrity.INVALID
    assert keys.verify(DOCUMENT, detached(foreign_key, DOCUMENT)) == csaf_integrity.UNVERIFIED
    assert keys.verify(DOCUMENT, None) == csaf_integrity.MISSING
    assert keys.verify(DOCUMENT.replace(b"\n", b"\r\n"), detached(signing_key, DOCUMENT)) == csaf_integrity.VALID


def test_a_key_that_is_not_the_declared_one_is_refused(signing_key: Tsk, foreign_key: Tsk) -> None:
    keys = csaf_integrity.KeyRing()
    assert not keys.add(public_key(foreign_key), signing_key.extract_certificate().fingerprint, origin="https://example.com/key.asc")
    assert keys.certs == []
    assert "does not match" in keys.rejected[0]


def test_a_declared_fingerprint_may_be_written_with_spaces(signing_key: Tsk) -> None:
    fingerprint = signing_key.extract_certificate().fingerprint.upper()
    spaced = " ".join(fingerprint[i : i + 4] for i in range(0, len(fingerprint), 4))
    assert csaf_integrity.KeyRing().add(public_key(signing_key), spaced)


def test_something_that_is_not_a_signature_is_told_apart() -> None:
    assert not csaf_integrity.looks_like_signature(b"<html>Moved</html>")
    assert csaf_integrity.looks_like_signature(b"-----BEGIN PGP SIGNATURE-----\n...")


# --- documents -----------------------------------------------------------------------------

SOURCE = types.SimpleNamespace(id="source-1", url="example.com")


def test_a_csaf_20_document_becomes_a_news_item() -> None:
    item = csaf_document.build_news_item(csaf(version="2", released="2026-09-05T08:30:00Z"), BASE + "2026/ex-2026-001.json", SOURCE)
    assert item.title == "EX-2026-001: Example product vulnerabilities"
    assert item.review == "Two flaws in Example Product."
    # The advisory's own page, not its JSON.
    assert item.link == "https://example.com/advisories/EX-2026-001"
    assert item.author == "Example PSIRT"
    assert item.version == "2"
    assert item.source == "example.com"
    assert item.osint_source_id == "source-1"
    assert re.fullmatch(r"\d\d\.\d\d\.2026 - \d\d:\d\d", item.published)


def test_attributes_of_a_csaf_20_document() -> None:
    item = csaf_document.build_news_item(csaf(), BASE + "x.json", SOURCE, {"CSAF_HASH": "valid", "CSAF_SIGNATURE": "missing"})
    assert attrs(item) == {
        "CVE": ["CVE-2026-0001"],
        "CWE": ["CWE-79"],
        "CVSS": [CVSS_V3["vectorString"]],
        # TLP 2.0 naming, so revisions of 2.0 and 2.1 documents compare equal.
        "TLP": ["CLEAR"],
        "CSAF_HASH": ["valid"],
        "CSAF_SIGNATURE": ["missing"],
    }
    assert all(attribute.binary_mime_type == "" for attribute in item.attributes)


def test_a_csaf_21_document_is_read() -> None:
    data = csaf(csaf_version="2.1", tlp="AMBER+STRICT", vulnerabilities=[vulnerability_21()], license_expression="CC-BY-4.0")
    item = csaf_document.build_news_item(data, BASE + "x.json", SOURCE)
    assert attrs(item) == {
        "CVE": ["CVE-2026-0002"],
        "CWE": ["CWE-269"],
        "CVSS": [CVSS_V3["vectorString"], CVSS_V4["vectorString"]],
        "TLP": ["AMBER+STRICT"],
    }
    for expected in (
        "CVSS 4.0",
        "probability 0.42, percentile 0.97",
        "critical",
        "Disclosed",
        "2026-08-30",
        "Exploited since",
        "2026-08-31",
        "CC-BY-4.0",
    ):
        assert expected in item.content, expected


def test_a_withdrawn_advisory_says_so() -> None:
    item = csaf_document.build_news_item(csaf(csaf_version="2.1", category="csaf_withdrawn", tlp="CLEAR"), BASE + "x.json", SOURCE)
    assert item.title.startswith("[Withdrawn] EX-2026-001")
    assert "This advisory is withdrawn." in item.content


def test_a_document_without_a_product_tree_is_read() -> None:
    # Intel's security advisories have none.
    item = csaf_document.build_news_item(csaf(product_tree=False), BASE + "x.json", SOURCE)
    assert "P1" in item.content
    assert attrs(item)["CVE"] == ["CVE-2026-0001"]


def test_product_names_come_from_the_product_tree() -> None:
    item = csaf_document.build_news_item(csaf(), BASE + "x.json", SOURCE)
    assert "Example Product 1.0" in item.content
    assert "Example Product 2.0" in item.content


def test_revisions_share_an_identity_and_differ_in_hash() -> None:
    first, second = csaf(version="1"), csaf(version="2", released="2026-09-10T00:00:00Z")
    assert csaf_document.version_key(first) == csaf_document.version_key(second)
    assert csaf_document.revision_hash(first) != csaf_document.revision_hash(second)
    # A translation is another document, not a revision.
    assert csaf_document.version_key(csaf(lang="en")) != csaf_document.version_key(csaf(lang="zh"))
    # Another publisher's advisory with the same id is another document too.
    other = copy.deepcopy(first)
    other["document"]["publisher"]["namespace"] = "https://example.org"
    assert csaf_document.version_key(other) != csaf_document.version_key(first)


def test_document_text_is_escaped_and_only_kept_tags_are_used() -> None:
    data = csaf()
    data["document"]["notes"].append(
        {"category": "details", "title": "<b>Details</b>", "text": "Versions < 2.1 are affected.\n\n<script>alert(1)</script>"},
    )
    content = csaf_document.render_content(data, BASE + "x.json")
    assert "Versions &lt; 2.1 are affected." in content
    assert "&lt;script&gt;" in content
    assert "<script>" not in content
    assert "Provided as is." not in content  # the legal disclaimer is left out
    assert set(re.findall(r"</?([a-z0-9]+)", content)) <= ALLOWED_HTML_TAGS


def test_a_large_advisory_details_the_worst_vulnerabilities_and_keeps_every_cve() -> None:
    # An Oracle Critical Patch Update lists some 800 vulnerabilities.
    vulnerabilities = [vulnerability_20(f"CVE-2026-{index:04d}", score=round(1 + index / 10, 1)) for index in range(60)]
    item = csaf_document.build_news_item(csaf(vulnerabilities=vulnerabilities), BASE + "x.json", SOURCE)
    assert len(attrs(item)["CVE"]) == 60
    assert item.content.count("<h4>CVE-2026-") == csaf_document.MAX_DETAILED_VULNERABILITIES
    assert "<h4>CVE-2026-0059: " in item.content  # the highest score is detailed
    assert "10 more vulnerabilities" in item.content
    # The same remediation under every vulnerability is listed once.
    assert item.content.count("Update to 2.0.") == 1


# --- collecting ----------------------------------------------------------------------------


def test_a_first_run_collects_only_the_newest_documents(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    for day in range(1, 6):
        provider.publish(f"2026/ex-{day}.json", csaf(f"EX-{day}", released=f"2026-09-0{day}T10:00:00Z"), f"2026-09-0{day}T10:00:00Z")
    harness = Harness(fetcher, make_source(MAX_DOCUMENTS="2"))

    items = harness.run()

    # The newest two, published oldest first; the archive is not paged through.
    assert [item.title.split(":")[0] for item in items] == ["EX-4", "EX-5"]
    assert harness.logger.messages["warning"] == []
    assert [url for url in fetcher.fetched() if url.startswith(BASE)] == [BASE + "2026/ex-4.json", BASE + "2026/ex-5.json"]


def test_integrity_is_recorded_on_every_item(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    (item,) = Harness(fetcher, make_source()).run()
    assert attrs(item)["CSAF_HASH"] == ["valid"]
    assert attrs(item)["CSAF_SIGNATURE"] == ["valid"]


def test_a_later_run_collects_what_changed_and_nothing_twice(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    (first,) = harness.run()

    # A new document, and a revision of the first one overwriting the same file.
    provider.publish("2026/ex-2.json", csaf("EX-2", released="2026-09-02T10:00:00Z"), "2026-09-02T10:00:00Z")
    provider.publish("2026/ex-1.json", csaf("EX-1", version="2", released="2026-09-03T10:00:00Z"), "2026-09-03T10:00:00Z")
    fetcher.requests.clear()
    second = harness.run()

    assert [item.title.split(":")[0] for item in second] == ["EX-2", "EX-1"]
    revision = second[1]
    assert revision.version_key == first.version_key
    assert revision.hash != first.hash
    assert revision.version == "2"

    fetcher.requests.clear()
    assert harness.run() == []
    assert fetcher.fetched() == []


@pytest.mark.parametrize(("setting", "expected"), [("true", True), ("false", False)])
def test_items_tell_core_whether_a_new_version_resurfaces(fetcher: FakeFetcher, signing_key: Tsk, setting: str, *, expected: bool) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    (item,) = Harness(fetcher, make_source(RESURFACE_NEW_VERSIONS=setting)).run()
    assert item.resurface is expected
    assert news_item.NewsItemDataSchema().dump(item)["resurface"] is expected


def test_a_document_dated_in_the_future_does_not_hold_collection_back(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    # Microsoft lists some updates under the date of their Patch Tuesday, days ahead.
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    provider.publish("2099/ex-future.json", csaf("EX-FUTURE", released="2099-01-01T00:00:00Z"), "2099-01-01T00:00:00Z")
    harness = Harness(fetcher, make_source())
    assert sorted(item.title.split(":")[0] for item in harness.run()) == ["EX-1", "EX-FUTURE"]
    assert any("1 documents dated in the future" in message for message in harness.logger.messages["info"])

    # A change listed afterwards with an ordinary date is still collected, and the future one
    # is not downloaded again.
    provider.publish("2026/ex-2.json", csaf("EX-2", released="2026-09-02T10:00:00Z"), "2026-09-02T10:00:00Z")
    assert [item.title.split(":")[0] for item in harness.run()] == ["EX-2"]


def test_the_same_file_listed_again_unchanged_is_not_downloaded(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    harness.run()
    # Still inside the overlap: listed with the same time, it must not be fetched again.
    provider.publish("2026/ex-2.json", csaf("EX-2"), "2026-09-01T11:00:00Z")
    fetcher.requests.clear()
    harness.run()
    assert fetcher.fetched() == [BASE + "2026/ex-2.json"]


def test_an_unchanged_listing_is_not_read_again(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key, etag='"v1"')
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    harness.run()
    fetcher.requests.clear()
    assert harness.run() == []
    assert [url for url, _ in fetcher.requests] == [BASE + "changes.csv"]
    assert fetcher.requests[0][1] == {"If-None-Match": '"v1"'}


def test_changes_left_out_by_the_limit_are_read_although_the_listing_is_unchanged(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key, etag='"v1"')
    provider.publish("2026/ex-0.json", csaf("EX-0"), "2026-09-01T00:00:00Z")
    harness = Harness(fetcher, make_source(MAX_DOCUMENTS="2"))
    harness.run()

    provider.etag = '"v2"'
    for hour in (1, 2, 3):
        changed = f"2026-09-02T0{hour}:00:00Z"
        provider.publish(f"2026/ex-{hour}.json", csaf(f"EX-{hour}", released=changed), changed)
    assert [item.title.split(":")[0] for item in harness.run()] == ["EX-2", "EX-3"]

    # The listing has not changed since, but EX-1 was left out: the listing is read in full
    # rather than asked whether it changed.
    fetcher.requests.clear()
    assert [item.title.split(":")[0] for item in harness.run()] == ["EX-1"]
    assert fetcher.requests[0] == (BASE + "changes.csv", {})

    # Nothing is left out now, so the next run asks again.
    fetcher.requests.clear()
    assert harness.run() == []
    assert fetcher.requests == [(BASE + "changes.csv", {"If-None-Match": '"v2"'})]


def test_check_if_modified_off_reads_the_listing_every_run(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key, etag='"v1"')
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source(CHECK_IF_MODIFIED="false"))
    harness.run()
    fetcher.requests.clear()
    # The listing is read in full, but the document already handled is not downloaded again.
    assert harness.run() == []
    assert [url for url, _ in fetcher.requests] == [BASE + "changes.csv"]
    assert fetcher.requests[0][1] == {}


def test_too_many_changes_are_limited_with_a_warning(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-0.json", csaf("EX-0"), "2026-09-01T00:00:00Z")
    harness = Harness(fetcher, make_source(MAX_DOCUMENTS="2"))
    harness.run()
    for hour in range(1, 5):
        provider.publish(f"2026/ex-{hour}.json", csaf(f"EX-{hour}"), f"2026-09-01T0{hour}:00:00Z")
    items = harness.run()
    assert [item.title.split(":")[0] for item in items] == ["EX-3", "EX-4"]
    assert any("4 documents changed, collecting the newest 2" in message for message in harness.logger.messages["warning"])


def test_documents_core_did_not_accept_are_collected_again(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    harness.accept = False
    assert len(harness.run()) == 1
    assert any("will be collected again" in message for message in harness.logger.messages["warning"])

    harness.accept = True
    assert [item.title.split(":")[0] for item in harness.run()] == ["EX-1"]


def test_a_core_timeout_is_reported_as_possibly_stored(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    # Core keeps working after the client gives up, so "did not accept" would be wrong.
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    harness.accept = False
    harness.rejection = ({"error": "Add news items timed out"}, HTTPStatus.GATEWAY_TIMEOUT)
    harness.run()
    warnings = harness.logger.messages["warning"]
    assert any("did not answer in time for 1 news items and may have stored them" in message for message in warnings)
    assert not any("did not accept" in message for message in warnings)

    # Sent again on the next run, like any unconfirmed chunk.
    harness.accept = True
    assert [item.title.split(":")[0] for item in harness.run()] == ["EX-1"]


def test_skipped_categories(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/vex-1.json", csaf("VEX-1", category="csaf_vex"), "2026-09-01T10:00:00Z")
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T11:00:00Z")
    items = Harness(fetcher, make_source()).run()
    assert [item.title.split(":")[0] for item in items] == ["EX-1"]


def test_every_category_is_collected_when_none_is_skipped(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/vex-1.json", csaf("VEX-1", category="csaf_vex"), "2026-09-01T10:00:00Z")
    assert len(Harness(fetcher, make_source(SKIP_CATEGORIES="")).run()) == 1


def test_a_rolie_category_is_skipped_before_download(fetcher: FakeFetcher) -> None:
    fetcher.add(
        "https://example.com/feed.json",
        {
            "feed": {
                "entry": [
                    {
                        "updated": "2026-09-01T00:00:00Z",
                        "content": {"src": "https://example.com/v.json"},
                        "category": [{"scheme": "x?document_category", "term": "csaf_vex"}],
                    },
                ],
            },
        },
    )
    Harness(fetcher, make_source("https://example.com/feed.json")).run()
    assert "https://example.com/v.json" not in fetcher.fetched()


def test_the_limit_counts_only_entries_of_collected_categories(fetcher: FakeFetcher) -> None:
    # The newest entries of the feed are VEX: they must not use up the limit of one.
    def entry(url: str, updated: str, category: str) -> dict:
        return {"updated": updated, "content": {"src": url}, "category": [{"scheme": "x?document_category", "term": category}]}

    fetcher.add(
        "https://example.com/feed.json",
        {
            "feed": {
                "entry": [
                    entry("https://example.com/v2.json", "2026-09-03T00:00:00Z", "csaf_vex"),
                    entry("https://example.com/v1.json", "2026-09-02T00:00:00Z", "csaf_vex"),
                    entry("https://example.com/ex-1.json", "2026-09-01T00:00:00Z", "csaf_security_advisory"),
                ],
            },
        },
    )
    fetcher.add("https://example.com/ex-1.json", body_of(csaf("EX-1")))
    items = Harness(fetcher, make_source("https://example.com/feed.json", MAX_DOCUMENTS="1")).run()
    assert [item.title.split(":")[0] for item in items] == ["EX-1"]


VEX_BASE = "https://csaf.example.com/csaf-vex/"


@pytest.mark.parametrize(("skip", "read"), [("csaf_vex", False), ("", True)])
def test_a_distribution_named_as_vex_is_read_only_when_vex_is_collected(
    fetcher: FakeFetcher,
    signing_key: Tsk,
    skip: str,
    *,
    read: bool,
) -> None:
    # SUSE's metadata lists csaf/ and csaf-vex/: skipping VEX should not cost a download.
    provider = Provider(fetcher, signing_key, other_distributions=(VEX_BASE,))
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    fetcher.add(VEX_BASE + "changes.csv", '"2026/cve-1.json","2026-09-02T10:00:00Z"\n')
    fetcher.add(VEX_BASE + "2026/cve-1.json", body_of(csaf("CVE-1", category="csaf_vex")))
    harness = Harness(fetcher, make_source(SKIP_CATEGORIES=skip))

    items = harness.run()

    assert [item.title.split(":")[0] for item in items] == (["EX-1", "CVE-1"] if read else ["EX-1"])
    assert (VEX_BASE + "changes.csv" in fetcher.fetched(".csv")) is read
    assert any(message.startswith(f"{VEX_BASE}: not read") for message in harness.logger.messages["info"]) is not read


@pytest.mark.parametrize(
    ("listing", "expected"),
    [
        (DirectoryListing("https://ftp.suse.com/pub/projects/security/csaf-vex/"), "csaf_vex"),
        (DirectoryListing("https://security.access.redhat.com/data/csaf/v2/vex/"), "csaf_vex"),
        (DirectoryListing("https://msrc.microsoft.com/csaf/vex"), "csaf_vex"),
        (RolieListing("https://example.com/csaf/example-csaf-vex-feed.json"), "csaf_vex"),
        (DirectoryListing("https://ftp.suse.com/pub/projects/security/csaf/"), None),
        (DirectoryListing("https://msrc.microsoft.com/csaf/advisories"), None),
        (DirectoryListing("https://example.com/vexation/"), None),
    ],
)
def test_a_distribution_is_known_as_vex_by_its_name(listing: DirectoryListing | RolieListing, expected: str | None) -> None:
    assert listing.named_category == expected


def test_missing_integrity_files_are_not_a_warning(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z", signed=False, hashed=False)
    harness = Harness(fetcher, make_source())
    (item,) = harness.run()
    assert (attrs(item)["CSAF_HASH"], attrs(item)["CSAF_SIGNATURE"]) == (["missing"], ["missing"])
    assert harness.logger.messages["warning"] == []


def test_a_page_served_instead_of_a_missing_signature_counts_as_missing(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    # Microsoft redirects missing .asc files to an HTML page.
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z", signed=False)
    fetcher.add(BASE + "2026/ex-1.json.asc", "<!DOCTYPE html><html>CSAF</html>")
    fetcher.add(BASE + "2026/ex-1.json.sha512", "<!DOCTYPE html><html>CSAF</html>")
    harness = Harness(fetcher, make_source())
    (item,) = harness.run()
    assert attrs(item)["CSAF_SIGNATURE"] == ["missing"]
    assert harness.logger.messages["warning"] == []


def test_a_tampered_document_is_collected_with_a_warning(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    fetcher.add(BASE + "2026/ex-1.json", body_of(csaf("EX-1", title="Changed on the way")))
    harness = Harness(fetcher, make_source())
    (item,) = harness.run()
    assert (attrs(item)["CSAF_HASH"], attrs(item)["CSAF_SIGNATURE"]) == (["mismatch"], ["invalid"])
    assert len(harness.logger.messages["warning"]) == 2


def test_a_signature_by_an_unknown_key_is_unverified(fetcher: FakeFetcher, signing_key: Tsk, foreign_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    body = provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    fetcher.add(BASE + "2026/ex-1.json.asc", detached(foreign_key, body))
    harness = Harness(fetcher, make_source())
    (item,) = harness.run()
    assert attrs(item)["CSAF_SIGNATURE"] == ["unverified"]
    assert harness.logger.messages["warning"] == []


def test_configured_keys_are_used_as_well(fetcher: FakeFetcher, signing_key: Tsk, foreign_key: Tsk) -> None:
    # CISA's metadata cannot always be reached; its key can be configured instead.
    provider = Provider(fetcher, signing_key)
    body = provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    fetcher.add(BASE + "2026/ex-1.json.asc", detached(foreign_key, body))
    fetcher.add("https://keys.example.org/other.asc", public_key(foreign_key))
    (item,) = Harness(fetcher, make_source(PUBLIC_KEY_URLS="https://keys.example.org/other.asc")).run()
    assert attrs(item)["CSAF_SIGNATURE"] == ["valid"]


def test_integrity_is_not_checked_when_switched_off(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1"), "2026-09-01T10:00:00Z")
    (item,) = Harness(fetcher, make_source(VERIFY_SIGNATURES="false")).run()
    assert "CSAF_HASH" not in attrs(item)
    assert [url for url in fetcher.fetched(".asc") + fetcher.fetched(".sha512") if url.startswith(BASE)] == []


def test_an_unknown_csaf_version_is_read_with_a_warning(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/ex-1.json", csaf("EX-1", csaf_version="2.2"), "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    assert len(harness.run()) == 1
    assert any("CSAF 2.2" in message for message in harness.logger.messages["warning"])


def test_json_that_is_not_csaf_is_skipped(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/cve.json", {"dataType": "CVE_RECORD"}, "2026-09-01T10:00:00Z")
    harness = Harness(fetcher, make_source())
    assert harness.run() == []
    assert harness.logger.messages["warning"] == []


def test_a_document_with_windows_1252_characters_is_read(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    # Oracle writes the names in its acknowledgments in Windows-1252, which is not valid JSON.
    provider = Provider(fetcher, signing_key)
    data = csaf("EX-1", title="Flaw reported by Joakim Bülow")
    provider.publish("2026/ex-1.json", data, "2026-09-01T10:00:00Z", signed=False, hashed=False)
    fetcher.add(BASE + "2026/ex-1.json", json.dumps(data, ensure_ascii=False).encode("cp1252"))
    (item,) = Harness(fetcher, make_source()).run()
    assert "Joakim Bülow" in item.title


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ('{"name": "Joakim Bülow"}'.encode(), "Joakim Bülow"),
        ('{"name": "Joakim Bülow"}'.encode("cp1252"), "Joakim Bülow"),
        # Valid UTF-8 stays as it is next to a stray Windows-1252 byte.
        ('{"name": "Café '.encode() + 'Díaz"}'.encode("cp1252"), "Café Díaz"),
        (b"\xef\xbb\xbf" + '{"name": "D\xedaz"}'.encode("cp1252"), "Díaz"),
    ],
)
def test_documents_are_decoded_as_utf_8_or_windows_1252(body: bytes, expected: str) -> None:
    assert csaf_document.loads(body)["name"] == expected


def test_a_body_that_is_not_json_is_still_refused() -> None:
    with pytest.raises(ValueError, match="Expecting value"):
        csaf_document.loads(b"<html>\xfc</html>")


def test_a_document_too_large_is_skipped(fetcher: FakeFetcher, signing_key: Tsk) -> None:
    provider = Provider(fetcher, signing_key)
    provider.publish("2026/big.json", csaf("BIG"), "2026-09-01T10:00:00Z")
    fetcher.routes[BASE + "2026/big.json"] = lambda url, _headers: Response(200, b"", {}, url, too_large=True)
    harness = Harness(fetcher, make_source())
    assert harness.run() == []
    assert any("larger than" in message for message in harness.logger.messages["warning"])


def test_restricted_distributions_are_summarised(fetcher: FakeFetcher) -> None:
    fetcher.add(
        METADATA,
        {
            "distributions": [
                {"directory_url": "https://example.com/white/"},
                {"directory_url": "https://example.com/amber/"},
                {"directory_url": "https://example.com/red/"},
            ],
        },
    )
    fetcher.add("https://example.com/white/changes.csv", b"", status=204)
    fetcher.add("https://example.com/amber/changes.csv", b"", status=401)
    fetcher.add("https://example.com/red/changes.csv", b"", status=403)
    harness = Harness(fetcher, make_source())
    harness.run()
    assert "2 of 3 distributions require authentication and were skipped" in harness.logger.messages["info"]
    assert harness.logger.messages["warning"] == []


def test_a_warning_when_no_distribution_is_accessible(fetcher: FakeFetcher) -> None:
    fetcher.add(METADATA, {"distributions": [{"directory_url": "https://example.com/amber/"}]})
    fetcher.add("https://example.com/amber/changes.csv", b"", status=401)
    harness = Harness(fetcher, make_source())
    harness.run()
    assert any("could be read" in message for message in harness.logger.messages["warning"])


def test_nothing_found_at_the_url_is_a_warning(fetcher: FakeFetcher) -> None:
    harness = Harness(fetcher, make_source("nothing.example"))
    assert harness.run() == []
    assert any("No CSAF provider metadata" in message for message in harness.logger.messages["warning"])


# --- GitHub repositories -------------------------------------------------------------------


def github_repository(fetcher: FakeFetcher, documents: dict[str, tuple[dict, str]], etag: str | None = None) -> dict[str, bytes]:
    """Serve documents from a repository o/r: path -> (document, blob sha)."""
    paths = {}
    bodies = {}
    for path, (data, sha) in documents.items():
        body = body_of(data)
        bodies[path] = body
        paths[path] = sha
        paths[path + ".sha256"] = "h-" + sha
        fetcher.add(f"https://raw.githubusercontent.com/o/r/HEAD/{path}", body)
        fetcher.add(f"https://raw.githubusercontent.com/o/r/HEAD/{path}.sha256", hashlib.sha256(body).hexdigest())
    github_tree(fetcher, "o", "r", paths, etag=etag)
    return bodies


def test_a_first_run_of_a_repository_takes_the_newest_by_their_numbers(fetcher: FakeFetcher) -> None:
    github_repository(
        fetcher,
        {
            # Without references of their own, the items link to the GitHub page.
            "advisories/INTEL-TA-01132.JSON": (csaf("INTEL-TA-01132", references=[]), "a"),
            "advisories/INTEL-SA-01499.JSON": (csaf("INTEL-SA-01499", references=[]), "b"),
            "advisories/INTEL-SA-00606.JSON": (csaf("INTEL-SA-00606", references=[]), "c"),
        },
    )
    harness = Harness(fetcher, make_source("https://github.com/o/r", MAX_DOCUMENTS="2"))
    items = harness.run()
    # By the numbers in the path, not the text around them: SA-01499 is newer than TA-01132.
    assert sorted(item.title.split(":")[0] for item in items) == ["INTEL-SA-01499", "INTEL-TA-01132"]
    assert all(attrs(item)["CSAF_HASH"] == ["valid"] for item in items)
    assert all(attrs(item)["CSAF_SIGNATURE"] == ["missing"] for item in items)
    assert harness.logger.messages["warning"] == []
    assert items[0].link.startswith("https://github.com/o/r/blob/HEAD/advisories/")


def test_a_repository_is_followed_by_blob_sha(fetcher: FakeFetcher) -> None:
    github_repository(fetcher, {"2026/1/1.json": (csaf("1"), "a"), "2026/2/2.json": (csaf("2"), "b")})
    harness = Harness(fetcher, make_source("https://github.com/o/r"))
    assert len(harness.run()) == 2

    # One file changes; only it is downloaded.
    github_repository(
        fetcher,
        {"2026/1/1.json": (csaf("1"), "a"), "2026/2/2.json": (csaf("2", version="2", released="2026-09-05T00:00:00Z"), "b2")},
    )
    fetcher.requests.clear()
    items = harness.run()
    assert [item.version for item in items] == ["2"]
    assert fetcher.fetched() == ["https://raw.githubusercontent.com/o/r/HEAD/2026/2/2.json"]


def test_an_unchanged_repository_costs_one_request(fetcher: FakeFetcher) -> None:
    github_repository(fetcher, {"2026/1/1.json": (csaf("1"), "a")}, etag='"t1"')
    harness = Harness(fetcher, make_source("https://github.com/o/r"))
    harness.run()
    fetcher.requests.clear()
    assert harness.run() == []
    assert [url for url, _ in fetcher.requests] == ["https://api.github.com/repos/o/r/git/trees/HEAD?recursive=1"]


def test_after_a_restart_the_commits_tell_what_changed(fetcher: FakeFetcher) -> None:
    github_repository(fetcher, {"2026/1/1.json": (csaf("1"), "a"), "2026/2/2.json": (csaf("2"), "b"), "2026/3/3.json": (csaf("3"), "c")})
    fetcher.add("https://api.github.com/repos/o/r/commits?*", [{"sha": "c1"}])
    fetcher.add("https://api.github.com/repos/o/r/commits/c1", {"files": [{"filename": "2026/1/1.json", "status": "modified"}]})
    source = make_source("https://github.com/o/r")
    source.last_collected = datetime.datetime(2026, 9, 20, 10, 0)  # noqa: DTZ001 - loaded naive, as the source schema does

    items = Harness(fetcher, source).run()

    assert [item.title for item in items] == ["1: Example product vulnerabilities"]


def test_after_a_restart_too_many_commits_fall_back_to_the_newest(fetcher: FakeFetcher) -> None:
    github_repository(fetcher, {"2026/1/1.json": (csaf("1"), "a"), "2026/2/2.json": (csaf("2"), "b")})
    fetcher.add("https://api.github.com/repos/o/r/commits?*", [{"sha": f"c{index}"} for index in range(31)])
    source = make_source("https://github.com/o/r", MAX_DOCUMENTS="1")
    source.last_collected = datetime.datetime(2026, 9, 20, 10, 0)  # noqa: DTZ001 - loaded naive, as the source schema does
    harness = Harness(fetcher, source)

    items = harness.run()

    assert [item.title.split(":")[0] for item in items] == ["2"]
    assert any("could not tell what changed" in message for message in harness.logger.messages["warning"])
