"""What a web publishing an organization's GCVE records registers at gcve.eu, and whether it answers.

The endpoints are asked through a stubbed ``requests.get``; no network.
"""

from __future__ import annotations

import io
import json
from types import SimpleNamespace
from typing import Self

import pytest
import requests
from api import organization_gcve
from managers import gna_registration

WEB = SimpleNamespace(id=7, name="Advisories", hostname="advisories.example.org", config={"security_contact": "cert@example.org"})


def _gna(directory: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(gna_id=65535, directory=directory)


def test_what_to_register_is_compared_with_the_directory() -> None:
    gna = _gna({"gcve_url": "https://advisories.example.org", "gcve_pull_api": "https://elsewhere.example.org/"})

    urls = {entry["key"]: entry for entry in gna_registration.web_urls(WEB, gna)}

    assert list(urls) == ["website", "pull_api", "dumps", "publication", "dump", "conformance", "security_txt"]
    assert urls["website"] == {
        "key": "website",
        "field": "gcve_url",
        "url": "https://advisories.example.org/",
        "registered": "https://advisories.example.org",
        "matches": True,
    }
    assert (urls["pull_api"]["registered"], urls["pull_api"]["matches"]) == ("https://elsewhere.example.org/", False)
    assert (urls["dumps"]["registered"], urls["dumps"]["matches"]) == (None, False)
    assert urls["dump"]["url"] == "https://advisories.example.org/dumps/gna-65535.ndjson"
    assert urls["dump"]["field"] is None


def test_without_a_security_contact_there_is_no_security_txt() -> None:
    web = SimpleNamespace(**{**vars(WEB), "config": {}})

    assert "security_txt" not in [entry["key"] for entry in gna_registration.web_urls(web, _gna())]
    assert gna_registration.web_urls(web, None) == []


class _Response:
    def __init__(self, status: int, body: bytes = b"", content_type: str = "application/json", location: str | None = None) -> None:
        self.status_code = status
        self.headers = {"Content-Type": content_type, **({"Location": location} if location else {})}
        self.raw = SimpleNamespace(read=lambda size, decode_content=True: io.BytesIO(body).read(size))  # noqa: ARG005

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _answer(monkeypatch: pytest.MonkeyPatch, response: object) -> list[dict]:
    asked: list[dict] = []

    def get(url: str, **kwargs: object) -> _Response:
        asked.append({"url": url, **kwargs})
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(gna_registration.requests, "get", get)
    return asked


def test_the_publication_is_a_list_of_records_read_without_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _answer(monkeypatch, _Response(200, json.dumps([{"cveMetadata": {}}, {"cveMetadata": {}}]).encode()))

    result = gna_registration.probe("publication", "https://advisories.example.org/api/gcve/publication")

    assert (result["ok"], result["status"], result["detail"]) == (True, 200, "2 records on the first page")
    assert asked[0]["allow_redirects"] is False


@pytest.mark.parametrize(
    ("key", "response", "ok", "detail"),
    [
        ("publication", _Response(301, location="https://other.example.org/"), False, "redirects to https://other.example.org/"),
        ("publication", _Response(404), False, "HTTP 404"),
        ("publication", _Response(200, b"<html>", "text/html"), False, "served as text/html, not JSON"),
        ("publication", _Response(200, b'{"items": []}'), False, "not a list of records"),
        ("conformance", _Response(200, b'{"gna_id": "65535"}'), True, "a conformance document"),
        ("dump", _Response(200, b'{"a": 1}\n{"b": 2}\n', "application/x-ndjson"), True, "2 records"),
        ("security_txt", _Response(200, b"Contact: mailto:cert@example.org\n", "text/plain"), True, "names a contact"),
        ("security_txt", _Response(200, b"Expires: 2027-01-01\n", "text/plain"), False, "names no contact"),
    ],
)
def test_each_endpoint_answers_as_gcve_consumers_expect(
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    response: _Response,
    ok: bool,
    detail: str,
) -> None:
    _answer(monkeypatch, response)

    result = gna_registration.probe(key, "https://advisories.example.org/x")

    assert result["ok"] is ok
    assert result["detail"].startswith(detail)


def test_an_endpoint_taranis_cannot_reach_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer(monkeypatch, requests.ConnectionError("no route"))

    result = gna_registration.probe("dump", "https://advisories.example.org/dumps/gna-65535.ndjson")

    assert (result["ok"], result["status"]) == (False, None)
    assert result["detail"] == "not reachable from Taranis: the name does not resolve or the connection was refused"

    _answer(monkeypatch, requests.ConnectTimeout("slow"))
    assert gna_registration.probe("dump", "https://x.example.org/")["detail"] == "not reachable from Taranis: no answer in time"
    _answer(monkeypatch, requests.exceptions.SSLError("bad certificate"))
    assert "TLS certificate" in gna_registration.probe("dump", "https://x.example.org/")["detail"]


def test_a_check_asks_only_the_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = _answer(monkeypatch, _Response(200, b"[]"))

    checked = gna_registration.check_web(WEB, _gna())

    assert [result["key"] for result in checked["results"]] == ["publication", "dump", "conformance", "security_txt"]
    assert len(asked) == 4


# -- the settings form -------------------------------------------------------------------------


def test_the_gna_form_takes_a_number_and_a_conformance_object() -> None:
    form, problem = organization_gcve._gna_form({"gna_id": " 69 ", "records_license": "CC0-1.0", "conformance": '{"governance": {}}'})
    assert problem is None
    assert form == {"gna_id": 69, "records_license": "CC0-1.0", "conformance": {"governance": {}}}

    assert organization_gcve._gna_form({"gna_id": ""})[0]["gna_id"] is None
    assert organization_gcve._gna_form({"gna_id": "x"})[1] == "The GNA number is a whole number"
    assert organization_gcve._gna_form({"gna_id": 1, "conformance": "[1]"})[1] == "The conformance details are a JSON object"
    assert organization_gcve._gna_form({"gna_id": 1, "conformance": "{"})[1] == "The conformance details are a JSON object"


def test_the_cve_services_form_is_checked() -> None:
    form, problem = organization_gcve._cve_form({"environment": "production", "short_name": " example ", "username": "ann", "api_key": ""})
    assert problem is None
    assert form == {"environment": "production", "short_name": "example", "username": "ann", "api_key": None}
    assert "environment is one of" in organization_gcve._cve_form({"environment": "staging"})[1]
