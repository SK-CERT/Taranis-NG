"""Filling a CVD Report from a CVE's published record (managers.cve_import, ReportItem.fill_cvd_fields).

No database and no network: CVE Services is a fake standing in for ``requests``, the reports are
built in memory and the session's commit is stubbed. The records are made up (example vendors
and people, example.com addresses).
"""

from __future__ import annotations

import copy
import importlib
import json
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from typing import Self

import pytest
import requests
from flask import Flask
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from api import analyze as analyze_api  # noqa: E402 - after every mapper is registered
from managers import cve_import, cve_services, gcve_publication  # noqa: E402
from managers.cve_import import CvdImport, CveImportError, ImportedValue  # noqa: E402
from managers.cve_services import CveServicesError  # noqa: E402
from model.report_item import ReportItem, ReportItemAttribute  # noqa: E402
from model.user import User  # noqa: E402
from test_gcve_record import AFFECTED, _minimal, _record, _value  # noqa: E402

from shared import gcve  # noqa: E402

CVE_ID = "CVE-2026-1000042"
JAVASCRIPT_LINK = "javascript:alert(1)"

THIRD_PARTY = {
    "dataType": "CVE_RECORD",
    "dataVersion": "5.1",
    "cveMetadata": {"cveId": CVE_ID, "state": "PUBLISHED", "assignerShortName": "example-cna"},
    "containers": {
        "cna": {
            "providerMetadata": {"orgId": "00000000-0000-4000-8000-000000000000", "shortName": "example-cna"},
            "descriptions": [
                {"lang": "cs", "value": "Portál pustí kohokoli dovnitř."},
                {
                    "lang": "en-US",
                    "value": "The portal lets anyone log in.",
                    "supportingMedia": [
                        {
                            "type": "text/html",
                            "base64": False,
                            "value": (
                                "<p>The portal lets <b>anyone</b> log in.</p><script>alert(1)</script>"
                                f'<p><a href="{JAVASCRIPT_LINK}">bad</a> <a href="https://example.com/a">good</a></p>'
                            ),
                        },
                    ],
                },
            ],
            "affected": [AFFECTED, {"versions": [{"version": "1.0", "status": "affected"}]}],
            "references": [{"url": "https://example.com/advisory", "name": "Vendor advisory", "tags": ["vendor-advisory", "x_custom"]}],
            "metrics": [
                {
                    "format": "CVSS",
                    "scenarios": [{"lang": "en", "value": "GENERAL"}],
                    "other": {"type": "Textual", "content": {"text": "High"}},
                },
            ],
            "problemTypes": [
                {"descriptions": [{"lang": "en", "cweId": "CWE-287", "description": "CWE-287: Improper Authentication", "type": "CWE"}]},
            ],
            "impacts": [{"capecId": "CAPEC-115", "descriptions": [{"lang": "en", "value": "Authentication bypass"}]}],
            "solutions": [{"lang": "en", "value": "Update to 1.4.2.\n\nOr later."}],
            "timeline": [{"time": "2026-10-01T09:30:15.000+02:00", "lang": "en", "value": "Reported"}],
            "credits": [
                {"lang": "en", "value": "Example Researcher", "type": "finder"},
                {"lang": "en", "value": "Example Bot", "type": "robot"},
            ],
            "source": {"discovery": "EXTERNAL", "defect": ["BUG-17"], "advisory": ["EX-2026-03"], "x_note": "ignored"},
            "tags": ["disputed", "x_custom"],
            "datePublic": "2026-11-01T23:30:00.000-02:00",
            "x_generator": {"engine": "Example editor"},
        },
        "adp": [
            {
                "providerMetadata": {"shortName": "other-adp"},
                "metrics": [{"cvssV3_1": {"vectorString": "CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N"}}],
            },
            {
                "providerMetadata": {"shortName": "CISA-ADP"},
                "metrics": [
                    {"cvssV3_1": {"vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "baseScore": 9.8}},
                    {"other": {"type": "ssvc", "content": {"options": [{"Exploitation": "none"}]}}},
                    {"other": {"type": "kev", "content": {"dateAdded": "2026-11-02"}}},
                ],
                "problemTypes": [
                    {"descriptions": [{"lang": "en", "cweId": "CWE-306", "description": "CWE-306 Missing Authentication", "type": "CWE"}]},
                ],
            },
        ],
    },
}


def _values(imported: CvdImport, key: str) -> list[str]:
    return [value.value for value in imported.fields.get(key, [])]


# -- the mapping -----------------------------------------------------------------------------


def test_a_record_taranis_published_gives_back_what_its_report_said() -> None:
    report = _minimal(
        _value("cve", "CVE-2026-12345"),
        _value("tags", "disputed\nexclusively-hosted-service"),
        _value("cvss", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "Default configuration"),
        _value("cvss", "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"),
        _value("other_metrics", {"type": "ssvc", "content": {"exploitation": "poc"}}),
        _value("cwe", "287", "Improper Authentication"),
        _value("problem_types", "Login bypass"),
        _value("impacts", "<p>CAPEC-115 Authentication Bypass</p>"),
        _value(
            "taxonomy_mappings",
            {
                "taxonomyName": "ATT&CK",
                "taxonomyRelations": [{"taxonomyId": "T1078", "relationshipName": "mitigatedBy", "relationshipValue": "M1032"}],
            },
        ),
        _value("date_public", "2026-11-01"),
        _value("solutions", "<p>Update to 1.4.2.</p>"),
        _value("workarounds", "<p>Block /login.</p>"),
        _value("configurations", "<p>SSO enabled.</p>"),
        _value("exploits", "<p>A proof of concept exists.</p>"),
        _value("discovery", "EXTERNAL"),
        _value("defects", "BUG-17"),
        _value("advisories", "EX-2026-03"),
        _value("timeline", {"time": "2026-10-01T09:30", "value": "Reported to the vendor"}),
        _value("credits", {"value": "Example Researcher", "type": "finder"}),
    )
    record = _record(report)
    record["cveMetadata"]["cveId"] = "CVE-2026-12345"

    imported = cve_import.cvd_values(record, "CVE-2026-12345")

    stored = {key: [attribute.value for attribute in attributes] for key, attributes in gcve_publication.field_values(report).items()}
    # Citations come back numbered as the record prints them; the record type and the
    # relationships are the GCVE record's, not the CVE's; tags come in their declared order.
    stored["description"] = ["<p>The portal lets anyone log in [1].</p>"]
    stored["tags"] = ["exclusively-hosted-service\ndisputed"]
    del stored["record_type"]
    assert imported.fields.keys() == stored.keys()
    for key, values in stored.items():
        expected = [cve_import.serialize(json.loads(value)) if value.startswith("{") else value for value in values]
        assert _values(imported, key) == expected, key
    assert [value.value_description for value in imported.fields["cvss"]] == ["Default configuration", None]
    assert imported.fields["cwe"][0].value_description == "Improper Authentication"
    assert imported.title == "Login bypass"
    assert imported.skipped == []


def test_a_third_party_record_fills_what_a_field_takes() -> None:
    imported = cve_import.cvd_values(copy.deepcopy(THIRD_PARTY), CVE_ID)

    assert imported.cve_id == CVE_ID
    assert _values(imported, "cve") == [CVE_ID]
    (description,) = _values(imported, "description")
    # The English text, its HTML made safe: no script, no javascript: link.
    assert "<b>anyone</b>" in description
    assert "script" not in description
    assert JAVASCRIPT_LINK not in description
    assert '<a href="https://example.com/a">good</a>' in description
    # A title the record does not have comes from the description.
    assert imported.title == "The portal lets anyone log in."
    assert _values(imported, "solutions") == ["<p>Update to 1.4.2.</p><p>Or later.</p>"]
    assert _values(imported, "impacts") == ["<p>CAPEC-115 Authentication bypass</p>"]
    assert _values(imported, "references") == ['{"name":"Vendor advisory","tags":["vendor-advisory"],"url":"https://example.com/advisory"}']
    assert _values(imported, "affected_products") == [cve_import.serialize(AFFECTED)]
    assert any(note.startswith("Affected products: ") for note in imported.skipped)
    # The CNA gives a CWE: CISA's is not taken. It gives no CVSS and no SSVC: CISA's are.
    assert _values(imported, "cwe") == ["287"]
    assert imported.fields["cwe"][0].value_description == "Improper Authentication"
    assert _values(imported, "cvss") == ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"]
    assert imported.fields["cvss"][0].value_description is None
    assert _values(imported, "other_metrics") == [
        '{"content":{"text":"High"},"type":"Textual"}',
        '{"content":{"options":[{"Exploitation":"none"}]},"type":"ssvc"}',
    ]
    assert _values(imported, "timeline") == ['{"time":"2026-10-01T07:30","value":"Reported"}']
    # A credit role the record format does not know is left out, the credit stays.
    assert _values(imported, "credits") == ['{"type":"finder","value":"Example Researcher"}', '{"value":"Example Bot"}']
    assert _values(imported, "discovery") == ["EXTERNAL"]
    assert _values(imported, "defects") == ["BUG-17"]
    assert _values(imported, "advisories") == ["EX-2026-03"]
    assert _values(imported, "tags") == ["disputed"]
    assert _values(imported, "date_public") == ["2026-11-02"]


def test_a_rejected_record_or_another_cves_fills_nothing() -> None:
    rejected = copy.deepcopy(THIRD_PARTY)
    rejected["cveMetadata"]["state"] = "REJECTED"
    with pytest.raises(CveImportError, match="is rejected"):
        cve_import.cvd_values(rejected, CVE_ID)
    with pytest.raises(CveImportError, match="record of CVE-2026-1000042 for CVE-2026-0001"):
        cve_import.cvd_values(copy.deepcopy(THIRD_PARTY), "CVE-2026-0001")


def test_only_a_cve_id_is_looked_up() -> None:
    with pytest.raises(CveImportError, match="is not a CVE ID"):
        cve_import.fetch("GCVE-1-2026-0001")


# -- reading the record -------------------------------------------------------------------------


class _Raw:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self, size: int, decode_content: bool = False) -> bytes:  # noqa: ARG002 - urllib3's signature
        return self.body[:size]


class _Response:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status_code = status
        self.ok = status < HTTPStatus.BAD_REQUEST
        self.raw = _Raw(body)

    def json(self) -> object:
        return json.loads(self.raw.body)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


@pytest.fixture
def requested(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The GET made, answered with ``requested.answer``; ``requested.provider`` is the CVE Services data provider (none by default)."""
    state = SimpleNamespace(calls=[], answer=_Response(200, json.dumps(THIRD_PARTY).encode()), provider=None)
    monkeypatch.setattr(cve_services, "_cve_services_provider", lambda: state.provider)

    def get(url: str, **kwargs: object) -> _Response:
        state.calls.append({"url": url, **kwargs})
        if isinstance(state.answer, Exception):
            raise state.answer
        return state.answer

    monkeypatch.setattr(requests, "get", get)
    return state


def test_the_published_record_is_read_without_credentials(requested: SimpleNamespace) -> None:
    imported = cve_import.fetch(" cve-2026-1000042 ")

    assert imported.cve_id == CVE_ID
    (call,) = requested.calls
    assert call["url"] == f"https://cveawg.mitre.org/api/cve/{CVE_ID}"
    assert not any(header.startswith("CVE-API") for header in call["headers"])
    assert call["allow_redirects"] is False
    assert call["timeout"] == cve_services.TIMEOUT


def test_the_record_is_read_where_the_cve_services_data_provider_points(requested: SimpleNamespace) -> None:
    requested.provider = SimpleNamespace(api_url=" https://cve-mirror.example.org/api/ ", user_agent="Example CERT Taranis")

    cve_services.published_record(CVE_ID)

    (call,) = requested.calls
    assert call["url"] == f"https://cve-mirror.example.org/api/cve/{CVE_ID}"
    assert call["headers"]["User-Agent"] == "Example CERT Taranis"


def test_without_a_url_in_the_provider_mitre_answers(requested: SimpleNamespace) -> None:
    requested.provider = SimpleNamespace(api_url="  ", user_agent=None)

    cve_services.published_record(CVE_ID)

    (call,) = requested.calls
    assert call["url"] == f"https://cveawg.mitre.org/api/cve/{CVE_ID}"
    assert "User-Agent" not in call["headers"]


def test_the_stub_url_overrides_the_provider(requested: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cve_services.Config, "CVE_SERVICES_URL", "http://stub:8080/api/")
    requested.provider = SimpleNamespace(api_url="https://cve-mirror.example.org/api/", user_agent=None)

    cve_services.published_record(CVE_ID)

    assert requested.calls[0]["url"] == f"http://stub:8080/api/cve/{CVE_ID}"


@pytest.mark.parametrize(
    ("answer", "message", "status"),
    [
        (_Response(404), "has no published record of CVE-2026-1000042", 404),
        (_Response(200, b"<html>"), "not a record of CVE-2026-1000042", None),
        (_Response(200, b"[]"), "not a record of CVE-2026-1000042", None),
        (_Response(500), "answered HTTP 500", 500),
        (requests.ConnectionError("refused"), "cannot be reached at https://cveawg.mitre.org/api", None),
    ],
)
def test_a_record_that_cannot_be_had_says_why(requested: SimpleNamespace, answer: object, message: str, status: int | None) -> None:
    requested.answer = answer

    with pytest.raises(CveServicesError, match=message) as raised:
        cve_services.published_record(CVE_ID)

    assert raised.value.status == status


def test_a_record_larger_than_the_cap_is_refused(requested: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cve_services, "MAX_RECORD_BYTES", 10)

    with pytest.raises(CveServicesError, match="larger than"):
        cve_services.published_record(CVE_ID)
    assert requested.calls


# -- filling a saved report -------------------------------------------------------------------


USER = User(-1, "analyst", "Ann Analyst")
USER.id = 5
FIELDS = gcve.cvd_fields()
GROUP_IDS = {key: number for number, key in enumerate(FIELDS, start=100)}
TYPES = {attribute.name: attribute.type for attribute in gcve.CVD_ATTRIBUTES}


def _group_item(key: str) -> SimpleNamespace:
    field = FIELDS[key]
    attribute_type = TYPES.get(field.attribute, field.attribute)
    return SimpleNamespace(id=GROUP_IDS[key], title=field.title, attribute=SimpleNamespace(type=SimpleNamespace(name=attribute_type)))


def _attribute(number: int, key: str, value: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=number,
        value=value,
        value_description="",
        version=1,
        attribute_group_item_id=GROUP_IDS[key],
        attribute_group_item=_group_item(key),
    )


def _saved(*attributes: SimpleNamespace, title: str = "") -> SimpleNamespace:
    """A saved CVD Report: its required fields hold the empty values the form starts them with."""
    report = SimpleNamespace(
        id=7,
        title=title,
        attributes=list(attributes),
        report_item_type=SimpleNamespace(attribute_groups=[SimpleNamespace(attribute_group_items=[_group_item(key) for key in FIELDS])]),
        cve_assignment=None,
        gcve_assignment=None,
        link_keys=0,
        cpes=0,
    )
    report.ensure_link_keys = lambda: setattr(report, "link_keys", report.link_keys + 1)
    report.update_cpes = lambda: setattr(report, "cpes", report.cpes + 1)
    return report


@pytest.fixture
def commits(monkeypatch: pytest.MonkeyPatch) -> list:
    made: list = []
    monkeypatch.setattr(db.session, "commit", lambda: made.append(True))
    return made


def _imported(**fields: list[str]) -> CvdImport:
    return CvdImport(
        CVE_ID,
        "Login bypass",
        {key: [ImportedValue(value) for value in values] for key, values in fields.items()},
        ["CVSS: one too many"],
    )


def test_only_empty_fields_are_filled_in_the_values_they_start_with(commits: list) -> None:
    description = _attribute(1, "description", "<p></p>")
    references = _attribute(2, "references", "")
    solutions = _attribute(3, "solutions", "<p>Ours.</p>")
    report = _saved(description, references, solutions)
    imported = _imported(
        description=["<p>Theirs.</p>"],
        references=['{"url":"https://example.com/a"}', '{"url":"https://example.com/b"}'],
        solutions=["<p>Theirs too.</p>"],
        cwe=["287"],
    )

    result = ReportItem.fill_cvd_fields(report, imported, USER, {})

    assert result["filled"] == ["Description", "References", "CWE"]
    assert result["kept"] == ["Solutions"]
    assert result["skipped"] == ["CVSS: one too many"]
    assert (description.value, description.version, description.user) == ("<p>Theirs.</p>", 2, USER)
    assert references.value == '{"url":"https://example.com/a"}'
    assert solutions.value == "<p>Ours.</p>"
    added = [attribute for attribute in report.attributes if isinstance(attribute, ReportItemAttribute)]
    assert [(attribute.attribute_group_item_id, attribute.value) for attribute in added] == [
        (GROUP_IDS["references"], '{"url":"https://example.com/b"}'),
        (GROUP_IDS["cwe"], "287"),
    ]
    assert report.title == "Login bypass"
    assert (report.link_keys, report.cpes, report.updated_by, commits) == (1, 1, "Ann Analyst", [True])
    assert [next(key for key in ("update", "add") if key in event) for event in result["events"]] == [
        "update",
        "update",
        "add",
        "add",
        "update",
    ]
    assert result["events"][-1] == {"update": True, "title": "", "report_item_id": 7, "user_id": 5}
    assert result["gcve_record_updated"] is False


def test_a_field_someone_else_is_editing_stays_as_it_is(commits: list) -> None:
    description = _attribute(1, "description", "")
    report = _saved(description, title="Ours")

    result = ReportItem.fill_cvd_fields(report, _imported(description=["<p>Theirs.</p>"]), USER, {"1": {"user_id": 9}})

    assert (result["filled"], result["kept"]) == ([], ["Description"])
    assert description.value == ""
    assert report.title == "Ours"
    assert commits == []


def test_ones_own_lock_does_not_keep_a_field(commits: list) -> None:
    description = _attribute(1, "description", "")
    report = _saved(description)

    result = ReportItem.fill_cvd_fields(report, _imported(description=["<p>Theirs.</p>"]), USER, {"1": {"user_id": USER.id}})

    assert result["filled"] == ["Description"]
    assert commits == [True]


def test_a_published_gcve_record_that_would_turn_invalid_is_not_touched(commits: list, monkeypatch: pytest.MonkeyPatch) -> None:
    rolled_back: list = []
    monkeypatch.setattr(db.session, "rollback", lambda: rolled_back.append(True))
    monkeypatch.setattr(gcve_publication, "problems", lambda _report, _short_name: ["CVSS: broken"])
    report = _saved(_attribute(1, "description", ""))
    report.gcve_assignment = SimpleNamespace(published=True, gcve_id="GCVE-65535-2026-0001")
    report.gna_short_name = "TEST-GNA"

    result = ReportItem.fill_cvd_fields(report, _imported(description=["<p>Theirs.</p>"]), USER, {})

    assert result == {"error": "GCVE-65535-2026-0001 is published, and this change would make its record invalid: CVSS: broken"}
    assert (rolled_back, commits) == ([True], [])


# -- the endpoints -----------------------------------------------------------------------------


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    """A bare app and an analyst; SSE and the public webs go nowhere."""
    monkeypatch.setattr(analyze_api.auth_manager, "get_user_from_jwt", lambda: USER)
    app = Flask(__name__)
    app.published = []
    monkeypatch.setattr(analyze_api.sse_manager, "report_item_updated", app.published.append)
    monkeypatch.setattr(analyze_api.sse_manager, "report_items_updated", lambda: app.published.append("list"))
    monkeypatch.setattr(analyze_api.sse_manager, "remote_access_report_items_updated", lambda _type_id: None)
    monkeypatch.setattr(analyze_api.sse_manager, "get_report_item_locks", lambda _id: {})
    monkeypatch.setattr(analyze_api.asset_manager, "report_item_changed", lambda _report: None)
    return app


def _call(app: Flask, resource: object, method: str, body: dict | None, *args: object) -> tuple[dict, HTTPStatus]:
    with app.test_request_context("/", method=method.upper(), json=body):
        return getattr(type(resource), method).__wrapped__.__get__(resource)(*args)


@pytest.mark.usefixtures("requested")
def test_a_new_report_gets_the_values_by_field(app: Flask) -> None:
    payload, status = _call(app, analyze_api.CveRecordCvd(), "get", None, CVE_ID)

    assert status == HTTPStatus.OK
    assert payload["cve_id"] == CVE_ID
    assert payload["fields"]["cwe"] == [{"value": "287", "value_description": "Improper Authentication"}]


@pytest.mark.parametrize(
    ("answer", "status"),
    [(_Response(404), HTTPStatus.NOT_FOUND), (requests.ConnectionError("refused"), HTTPStatus.BAD_GATEWAY)],
)
def test_a_cve_that_cannot_be_had_says_why(app: Flask, requested: SimpleNamespace, answer: object, status: HTTPStatus) -> None:
    requested.answer = answer

    payload, got = _call(app, analyze_api.CveRecordCvd(), "get", None, CVE_ID)

    assert got == status
    assert payload["error"]
    assert _call(app, analyze_api.CveRecordCvd(), "get", None, "CVE-1")[1] == HTTPStatus.BAD_REQUEST


@pytest.mark.usefixtures("requested", "commits")
def test_a_saved_report_is_filled_and_the_editors_told(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _saved(_attribute(1, "description", ""), _attribute(2, "references", ""), _attribute(3, "affected_products", ""))
    report.is_cvd = True
    report.report_item_type_id = 3
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))

    payload, status = _call(app, analyze_api.ReportItemCvdFill(), "post", {"cve_id": CVE_ID}, 7)

    assert status == HTTPStatus.OK
    assert "Description" in payload["filled"]
    assert "CVE" in payload["filled"]
    assert set(payload) == {"filled", "kept", "skipped"}
    assert app.published[-1] == "list"
    assert all(event["user_id"] == USER.id for event in app.published[:-1])


@pytest.mark.usefixtures("commits")
def test_a_saved_report_is_filled_from_the_cve_it_holds(app: Flask, requested: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _saved(_attribute(1, "cve", CVE_ID))
    report.is_cvd = True
    report.report_item_type_id = 3
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))

    payload, status = _call(app, analyze_api.ReportItemCvdFill(), "post", {"cve_id": "CVE-2026-0001"}, 7)
    assert status == HTTPStatus.BAD_REQUEST
    assert "holds CVE-2026-1000042" in payload["error"]

    payload, status = _call(app, analyze_api.ReportItemCvdFill(), "post", {}, 7)
    assert status == HTTPStatus.OK
    assert "CVE" in payload["kept"]
    assert requested.calls[-1]["url"].endswith(CVE_ID)


def test_only_a_cvd_report_is_filled(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _saved()
    report.is_cvd = False
    monkeypatch.setattr(analyze_api.ReportItem, "find", classmethod(lambda _cls, _id: report))

    payload, status = _call(app, analyze_api.ReportItemCvdFill(), "post", {"cve_id": CVE_ID}, 7)

    assert (status, payload) == (HTTPStatus.BAD_REQUEST, {"error": "Only a CVD Report is filled from a CVE"})
