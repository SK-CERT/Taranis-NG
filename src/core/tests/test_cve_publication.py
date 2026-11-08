"""CVE records through CVE Services: the client, the record, reserving, publishing and rejecting.

No database and no network: CVE Services is a fake standing in for ``requests`` (the client
tests) or for the client itself (the publication tests), and the session's commit is stubbed.
The CVD Reports are built in memory the way the GCVE record tests build them.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from managers import cve_publication, cve_services  # noqa: E402 - after every mapper is registered
from managers.cve_publication import CvePublicationError  # noqa: E402
from managers.cve_services import Credentials, CveServicesError  # noqa: E402
from model import cve_services_account  # noqa: E402
from model.cve_assignment import PUBLISHED, REJECTED, RESERVED, CveAssignment  # noqa: E402
from model.cve_services_account import CveServicesAccount  # noqa: E402
from model.product import Product  # noqa: E402
from model.product_preset import ProductPreset  # noqa: E402
from model.report_item import ReportItem  # noqa: E402
from test_gcve_record import _minimal, _value  # noqa: E402

from shared import gcve  # noqa: E402

CREDENTIALS = Credentials("https://cve.test/api", "example", "analyst@example.org", "secret-key")
ORG_UUID = "6a1c5e2f-0b3d-4c8e-9f7a-1d2e3f4a5b6c"
ORGANIZATION = 4
MOMENT = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


# -- the client ----------------------------------------------------------------------------


class _Response:
    def __init__(self, status: int, body: object = None) -> None:
        self.status_code = status
        self.ok = status < HTTPStatus.BAD_REQUEST
        self._body = body

    def json(self) -> object:
        if self._body is None:
            raise ValueError
        return self._body


class _Calls(list):
    """The requests made, and the answers queued for the next ones."""

    def __init__(self) -> None:
        super().__init__()
        self.answers: list[object] = []


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """The requests the client makes; each answered with the next response queued in ``calls.answers``."""
    made = _Calls()
    answers = made.answers

    def request(method: str, url: str, **kwargs: object) -> _Response:
        made.append({"method": method, "url": url, **kwargs})
        answer = answers.pop(0) if answers else _Response(200, {})
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(requests, "request", request)
    return made


def test_every_call_names_the_cna_its_user_and_key(calls: _Calls) -> None:
    calls.answers.append(_Response(200, {"cve_ids": [{"cve_id": "CVE-2026-1234", "state": "RESERVED"}]}))

    assert cve_services.reserve(CREDENTIALS, 2026) == "CVE-2026-1234"

    (call,) = calls
    assert (call["method"], call["url"]) == ("POST", "https://cve.test/api/cve-id")
    assert call["params"] == {"amount": 1, "cve_year": 2026, "short_name": "example"}
    assert call["headers"]["CVE-API-ORG"] == "example"
    assert call["headers"]["CVE-API-USER"] == "analyst@example.org"
    assert call["headers"]["CVE-API-KEY"] == "secret-key"
    assert call["allow_redirects"] is False
    assert call["timeout"] == cve_services.TIMEOUT


def test_a_record_is_published_then_updated_with_its_cna_container(calls: _Calls) -> None:
    container = {"descriptions": []}

    cve_services.publish(CREDENTIALS, "CVE-2026-1234", container)
    cve_services.update(CREDENTIALS, "CVE-2026-1234", container)

    assert [(call["method"], call["url"], call["json"]) for call in calls] == [
        ("POST", "https://cve.test/api/cve/CVE-2026-1234/cna", {"cnaContainer": container}),
        ("PUT", "https://cve.test/api/cve/CVE-2026-1234/cna", {"cnaContainer": container}),
    ]


@pytest.mark.parametrize(("published", "method"), [(False, "POST"), (True, "PUT")])
def test_a_reserved_id_is_rejected_with_post_and_a_published_record_with_put(calls: _Calls, published: bool, method: str) -> None:
    cve_services.reject(CREDENTIALS, "CVE-2026-1234", "Not a vulnerability", published=published, org_uuid=ORG_UUID)

    (call,) = calls
    assert (call["method"], call["url"]) == (method, "https://cve.test/api/cve/CVE-2026-1234/reject")
    assert call["json"] == {
        "cnaContainer": {"rejectedReasons": [{"lang": "en", "value": "Not a vulnerability"}], "providerMetadata": {"orgId": ORG_UUID}},
    }


def test_where_an_id_stands_is_asked_of_cve_services(calls: _Calls) -> None:
    calls.answers.append(_Response(200, {"cve_id": "CVE-2026-1234", "state": "PUBLISHED", "owning_cna": "example"}))

    assert cve_services.id_state(CREDENTIALS, "CVE-2026-1234") == "PUBLISHED"
    (call,) = calls
    assert (call["method"], call["url"]) == ("GET", "https://cve.test/api/cve-id/CVE-2026-1234")

    calls.answers.append(_Response(200, {"cve_id": "CVE-2026-1234"}))
    with pytest.raises(CveServicesError, match="did not say where CVE-2026-1234 stands"):
        cve_services.id_state(CREDENTIALS, "CVE-2026-1234")


def test_testing_the_account_reads_the_cna_and_its_quota(calls: _Calls) -> None:
    calls.answers.extend(
        [
            _Response(200, {"short_name": "example", "name": "Example CERT", "UUID": ORG_UUID, "authority": {"active_roles": ["CNA"]}}),
            _Response(200, {"id_quota": 1000, "total_reserved": 12, "available": 988}),
        ],
    )

    info = cve_services.org_info(CREDENTIALS)

    assert info == {
        "name": "Example CERT",
        "short_name": "example",
        "uuid": ORG_UUID,
        "roles": ["CNA"],
        "id_quota": 1000,
        "total_reserved": 12,
        "available": 988,
    }
    assert [call["url"] for call in calls] == ["https://cve.test/api/org/example", "https://cve.test/api/org/example/id_quota"]


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (_Response(401, {"error": "UNAUTHORIZED"}), "refused the credentials"),
        (
            _Response(
                400,
                {
                    "error": "INVALID_JSON_SCHEMA",
                    "message": "CVE JSON schema validation FAILED.",
                    "details": {"errors": [{"instancePath": "/cnaContainer/affected", "message": "must NOT have fewer than 1 items"}]},
                },
            ),
            "CVE JSON schema validation FAILED.; /cnaContainer/affected: must NOT have fewer than 1 items",
        ),
        (_Response(403, None), "may not do this"),
        (_Response(500, None), "answered HTTP 500"),
        (requests.ConnectionError("refused"), "cannot be reached at https://cve.test/api"),
    ],
)
def test_a_failure_says_why_in_words(calls: _Calls, answer: object, message: str) -> None:
    calls.answers.append(answer)

    with pytest.raises(CveServicesError) as raised:
        cve_services.publish(CREDENTIALS, "CVE-2026-1234", {})

    assert message in str(raised.value)


def test_the_account_picks_its_service_unless_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    account = CveServicesAccount(id=1, environment="production", short_name="example", username="ann")
    assert account.base_url == "https://cveawg.mitre.org/api"
    account.environment = "test"
    assert account.base_url == "https://cveawg-test.mitre.org/api"
    monkeypatch.setattr(cve_services_account.Config, "CVE_SERVICES_URL", "http://stub:8080/api")
    assert account.base_url == "http://stub:8080/api"


def test_credentials_need_the_whole_account() -> None:
    account = CveServicesAccount(id=1, environment="test", short_name="example", username="")
    with pytest.raises(CveServicesError, match="short name and a user"):
        Credentials.of(account, "key")
    account.username = "ann"
    with pytest.raises(CveServicesError, match="no API key"):
        Credentials.of(account)
    assert Credentials.of(account, "key").headers()["CVE-API-KEY"] == "key"


# -- the record ----------------------------------------------------------------------------


def _assignment(state: str = RESERVED, **fields: object) -> CveAssignment:
    assignment = CveAssignment(cve_id="CVE-2026-1234", state=state, date_reserved=MOMENT)
    for name, value in fields.items():
        setattr(assignment, name, value)
    return assignment


def test_the_container_is_the_gcve_records_content_with_the_cnas_uuid() -> None:
    report = _minimal(_value("cve", "CVE-2026-1234"), cve_assignment=_assignment())

    container = cve_publication.cna_container(report, report.cve_assignment, ORG_UUID)

    assert container["providerMetadata"] == {"orgId": ORG_UUID}
    assert container["dateAssigned"] == "2026-11-08T12:00:00.000Z"
    assert container["title"] == "Login bypass"
    assert container["descriptions"][0]["value"] == "The portal lets anyone log in [1]."
    assert "cveMetadata" not in container
    assert cve_publication.problems(report, ORG_UUID) == []


def test_the_gcve_extension_comes_only_once_the_gcve_record_is_published() -> None:
    report = _minimal(_value("cve", "CVE-2026-1234"), cve_assignment=_assignment())
    assert cve_publication.cna_container(report, report.cve_assignment, ORG_UUID)["x_gcve"] == [
        {"vulnId": "GCVE-65535-2026-0001", "recordType": "advisory", "relationships": [{"destId": "CVE-2026-1234", "type": "equal"}]},
    ]

    report.gcve_assignment.published = False
    assert "x_gcve" not in cve_publication.cna_container(report, report.cve_assignment, ORG_UUID)
    report.gcve_assignment = None
    assert "x_gcve" not in cve_publication.cna_container(report, report.cve_assignment, ORG_UUID)


def test_a_cve_of_another_cna_is_not_published_again() -> None:
    report = _minimal(_value("cve", "CVE-2025-0001"), cve_assignment=None)

    (problem,) = cve_publication.problems(report)

    assert "CVE-2025-0001 was not reserved by this CNA" in problem
    assert "duplicate" in cve_publication.can_get_cve(SimpleNamespace(**{**vars(report), "is_cvd": True}))


def _record_type(report: SimpleNamespace, kind: str) -> SimpleNamespace:
    """The report with its Record type set to ``kind``."""
    next(attribute for attribute in report.attributes if attribute.attribute_group_item.title == "Record type").value = kind
    return report


@pytest.mark.parametrize("kind", ["comment", "update", "analysis", "bundle"])
def test_only_an_advisory_is_a_cve_record(kind: str) -> None:
    report = _record_type(_minimal(cve_assignment=None, is_cvd=True), kind)

    assert cve_publication.problems(report) == [f"Record type: a CVE record is published for an advisory only, and this report is a '{kind}'"]
    assert cve_publication.can_get_cve(report) == f"only an advisory gets a CVE ID, and this report is a '{kind}'"
    assert cve_publication.can_get_cve(_record_type(report, "advisory")) is None


def test_a_deprecated_reports_cve_id_is_rejected_not_published() -> None:
    report = _record_type(_minimal(_value("cve", "CVE-2026-1234"), cve_assignment=_assignment(PUBLISHED)), "deprecation")

    (problem,) = cve_publication.problems(report)

    assert problem == "Record type: a deprecated report's CVE ID is withdrawn by rejecting it, not published again (CVE-2026-1234)"


def test_the_cve_field_must_hold_the_reserved_id() -> None:
    report = _minimal(_value("cve", "CVE-2026-9999"), cve_assignment=_assignment())

    assert cve_publication.problems(report) == ["CVE: the field must hold the CVE ID reserved for the report, CVE-2026-1234"]


def test_an_incomplete_report_is_refused_as_for_gcve() -> None:
    report = _minimal(cve_assignment=None)
    report.attributes = [attribute for attribute in report.attributes if attribute.attribute_group_item.title != "References"]

    assert cve_publication.problems(report) == ["References: required"]
    other = _minimal(cve_assignment=None, report_item_type=SimpleNamespace(system_key=None))
    assert cve_publication.problems(other) == ["only CVD Reports can be published in a CVE Record"]


def test_the_reserved_cve_field_stays_until_the_id_is_rejected() -> None:
    report = _minimal(_value("cve", "CVE-2026-1234"), cve_assignment=_assignment())
    field = next(attribute for attribute in report.attributes if cve_publication.is_cve_field(attribute))
    other = report.attributes[0]

    assert cve_publication.cve_field_locked(report, field, "CVE-2026-1234") is None
    assert "reject it to free the field" in cve_publication.cve_field_locked(report, field, "")
    assert "reject it to free the field" in cve_publication.cve_field_locked(report, field)
    assert cve_publication.cve_field_locked(report, other, "anything") is None
    report.cve_assignment = None
    assert cve_publication.cve_field_locked(report, field, "") is None


# -- reserving, publishing, rejecting ------------------------------------------------------


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A fake CVE Services behind the client functions, the account, and a stubbed session.

    ``refuse`` holds the IDs whose every call is refused, or ``(call, ID)`` pairs for one call;
    ``upstream`` where an ID stands at CVE Services when asked (RESERVED unless set).
    """
    state = SimpleNamespace(calls=[], refuse=set(), upstream={}, next_id=1234, commits=0)

    def reserve(_credentials: Credentials, year: int) -> str:
        state.calls.append(("reserve", year))
        cve_id = f"CVE-{year}-{state.next_id}"
        state.next_id += 1
        return cve_id

    def call(name: str) -> object:
        def run(_credentials: Credentials, cve_id: str, *args: object, **kwargs: object) -> None:
            state.calls.append((name, cve_id, *args, *kwargs.values()))
            if cve_id in state.refuse or (name, cve_id) in state.refuse:
                msg = f"{cve_id} refused"
                raise CveServicesError(msg, 400)

        return run

    def id_state(_credentials: Credentials, cve_id: str) -> str:
        state.calls.append(("state", cve_id))
        return state.upstream.get(cve_id, RESERVED)

    def reserve_assignment(_cls: type, report: SimpleNamespace, cve_id: str, now: datetime | None = None) -> CveAssignment:
        assignment = CveAssignment(cve_id=cve_id, state=RESERVED, date_reserved=now or MOMENT)
        report.cve_assignment = assignment
        return assignment

    monkeypatch.setattr(cve_services, "reserve", reserve)
    monkeypatch.setattr(cve_services, "publish", call("publish"))
    monkeypatch.setattr(cve_services, "update", call("update"))
    monkeypatch.setattr(cve_services, "reject", call("reject"))
    monkeypatch.setattr(cve_services, "id_state", id_state)
    monkeypatch.setattr(CveAssignment, "reserve", classmethod(reserve_assignment))
    account = CveServicesAccount(
        id=1,
        organization_id=ORGANIZATION,
        environment="test",
        short_name="example",
        username="ann",
        org_uuid=ORG_UUID,
    )
    account.api_key = "encrypted"
    # The account of the reports' organization; any other has none.
    monkeypatch.setattr(
        CveServicesAccount,
        "get",
        classmethod(lambda _cls, organization_id: account if organization_id == ORGANIZATION else None),
    )
    monkeypatch.setattr(CveServicesAccount, "get_api_key", lambda _self: "secret-key")

    def commit() -> None:
        state.commits += 1

    monkeypatch.setattr(db.session, "commit", commit)
    return state


def _cvd(*values: SimpleNamespace, **fields: object) -> SimpleNamespace:
    report = _minimal(
        _value("cve", ""),
        *values,
        **{"cve_assignment": None, "is_cvd": True, "id": 7, "organization_id": ORGANIZATION, **fields},
    )
    for attribute in report.attributes:
        attribute.version = 1
    # A published GCVE record names the CVE ID, so it changes with it.
    report.gcve_touched = []
    report.gcve_assignment.touch = lambda: report.gcve_touched.append(True)
    return report


def _holding(assignment: CveAssignment) -> SimpleNamespace:
    """A CVD Report holding the ID of ``assignment`` in its CVE field."""
    report = _cvd()
    report.cve_assignment = assignment
    next(attribute for attribute in report.attributes if cve_publication.is_cve_field(attribute)).value = assignment.cve_id
    return report


def test_reserving_writes_the_id_into_the_cve_field(service: SimpleNamespace) -> None:
    report = _cvd()

    assignment = cve_publication.reserve(report, cve_publication.credentials(ORGANIZATION), MOMENT)

    assert assignment.cve_id == "CVE-2026-1234"
    assert cve_publication.cve_field_value(report) == "CVE-2026-1234"
    assert service.calls == [("reserve", 2026)]
    assert service.commits == 1
    assert report.gcve_touched == [True]
    with pytest.raises(CvePublicationError, match="it has the CVE ID CVE-2026-1234"):
        cve_publication.reserve(report, cve_publication.credentials(ORGANIZATION))


def test_publishing_reserves_publishes_and_later_sends_only_changes(service: SimpleNamespace) -> None:
    report = _cvd()

    assert cve_publication.publish([report]) == ["CVE-2026-1234"]
    assignment = report.cve_assignment
    assert assignment.state == PUBLISHED
    assert [call[0] for call in service.calls] == ["reserve", "publish"]
    container = service.calls[1][2]
    assert container["providerMetadata"] == {"orgId": ORG_UUID}

    # Saved again unchanged: nothing is sent.
    assert cve_publication.publish([report]) == []
    assert len(service.calls) == 2

    # Changed since: the record is updated.
    assignment.changed(assignment.date_submitted + timedelta(microseconds=1))
    assert assignment.out_of_date
    assert cve_publication.publish([report]) == ["CVE-2026-1234"]
    assert service.calls[-1][0] == "update"
    assert not assignment.out_of_date


def test_a_cve_record_holding_a_report_that_is_no_advisory_sends_nothing(service: SimpleNamespace) -> None:
    good = _cvd()
    comment = _record_type(_cvd(id=8, title="Second"), "comment")

    with pytest.raises(CvePublicationError, match="Second: Record type: a CVE record is published for an advisory only"):
        cve_publication.publish([good, comment])
    assert service.calls == []


def test_nothing_is_sent_while_any_report_cannot_be_published(service: SimpleNamespace) -> None:
    good = _cvd()
    bad = _cvd(id=8, title="Second")
    bad.attributes = [attribute for attribute in bad.attributes if attribute.attribute_group_item.title != "Affected products"]

    with pytest.raises(CvePublicationError, match="Second: Affected products: required"):
        cve_publication.publish([good, bad])
    assert service.calls == []


def test_a_refused_record_leaves_the_others_published_and_says_which(service: SimpleNamespace) -> None:
    first, second = _cvd(), _cvd(id=8, title="Second")
    service.refuse.add("CVE-2026-1235")

    with pytest.raises(CvePublicationError, match=r"refused 1 record\(s\)\. Sent: CVE-2026-1234\. CVE-2026-1235: CVE-2026-1235 refused"):
        cve_publication.publish([first, second])

    assert first.cve_assignment.state == PUBLISHED
    assert (second.cve_assignment.state, second.cve_assignment.last_error) == (RESERVED, "CVE-2026-1235 refused")

    # Published again: only the refused one is tried, and now it goes through.
    service.refuse.clear()
    assert cve_publication.publish([first, second]) == ["CVE-2026-1235"]
    assert second.cve_assignment.last_error is None


def test_a_record_published_without_its_answer_is_updated_next_time(service: SimpleNamespace) -> None:
    report = _holding(_assignment(last_error="CVE Services cannot be reached at https://cve.test/api"))
    # The earlier POST went through; its answer did not come back. A second POST is refused.
    service.refuse.add(("publish", "CVE-2026-1234"))
    service.upstream["CVE-2026-1234"] = PUBLISHED

    assert cve_publication.publish([report]) == ["CVE-2026-1234"]

    assert [call[0] for call in service.calls] == ["publish", "state", "update"]
    assert service.calls[2][2] == service.calls[0][2]
    assert (report.cve_assignment.state, report.cve_assignment.last_error) == (PUBLISHED, None)


def test_an_id_rejected_at_cve_services_is_reported_so(service: SimpleNamespace) -> None:
    report = _holding(_assignment())
    service.refuse.add("CVE-2026-1234")
    service.upstream["CVE-2026-1234"] = REJECTED

    with pytest.raises(CvePublicationError, match="CVE-2026-1234 is rejected at CVE Services: reject it here too"):
        cve_publication.publish([report])

    assert report.cve_assignment.state == RESERVED
    assert "rejected at CVE Services" in report.cve_assignment.last_error


def test_nothing_is_asked_when_cve_services_did_not_answer(service: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _holding(_assignment())

    def unreachable(*_args: object) -> None:
        msg = "CVE Services cannot be reached at https://cve.test/api"
        raise CveServicesError(msg)

    monkeypatch.setattr(cve_services, "publish", unreachable)

    with pytest.raises(CvePublicationError, match="cannot be reached"):
        cve_publication.publish([report])

    assert ("state", "CVE-2026-1234") not in service.calls
    assert report.cve_assignment.state == RESERVED


@pytest.mark.usefixtures("service")
def test_publishing_needs_the_account_of_the_reports_organization() -> None:
    with pytest.raises(CvePublicationError, match="organization of the CVD Report has no CVE Services account"):
        cve_publication.publish([_cvd(organization_id=ORGANIZATION + 1)])


@pytest.mark.usefixtures("service")
def test_a_cve_record_holds_the_reports_of_one_organization() -> None:
    with pytest.raises(CvePublicationError, match="of one organization"):
        cve_publication.publish([_cvd(), _cvd(id=8, organization_id=ORGANIZATION + 1)])
    assert cve_publication.publish([]) == []


def test_a_reports_calls_use_its_organizations_account(service: SimpleNamespace) -> None:  # noqa: ARG001
    assert cve_publication.credentials_for(_cvd()).organization_id == ORGANIZATION
    with pytest.raises(CvePublicationError, match="no CVE Services account"):
        cve_publication.credentials_for(_cvd(organization_id=None))


@pytest.mark.parametrize(("state", "published"), [(RESERVED, False), (PUBLISHED, True)])
def test_rejecting_frees_the_cve_field(service: SimpleNamespace, state: str, published: bool) -> None:
    report = _cvd()
    report.cve_assignment = _assignment(state)
    next(attribute for attribute in report.attributes if cve_publication.is_cve_field(attribute)).value = "CVE-2026-1234"

    with pytest.raises(CvePublicationError, match="with a reason"):
        cve_publication.reject(report, " ", cve_publication.credentials(ORGANIZATION))
    assignment = cve_publication.reject(report, "Duplicate of CVE-2025-0001", cve_publication.credentials(ORGANIZATION))

    assert service.calls == [("reject", "CVE-2026-1234", "Duplicate of CVE-2025-0001", published, ORG_UUID)]
    assert (assignment.state, assignment.rejected_reason) == (REJECTED, "Duplicate of CVE-2025-0001")
    assert cve_publication.cve_field_value(report) is None


def test_a_refused_rejection_keeps_the_id_and_says_why(service: SimpleNamespace) -> None:
    report = _cvd()
    report.cve_assignment = _assignment()
    service.refuse.add("CVE-2026-1234")

    with pytest.raises(CveServicesError):
        cve_publication.reject(report, "Not a vulnerability", cve_publication.credentials(ORGANIZATION))

    assert (report.cve_assignment.state, report.cve_assignment.last_error) == (RESERVED, "CVE-2026-1234 refused")


def test_rejecting_an_id_whose_record_was_published_after_all_uses_put(service: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    report = _holding(_assignment())
    service.upstream["CVE-2026-1234"] = PUBLISHED

    def reject_published_with_put(_credentials: Credentials, cve_id: str, reason: str, *, published: bool, org_uuid: str) -> None:
        service.calls.append(("reject", cve_id, reason, published, org_uuid))
        if not published:
            msg = f"{cve_id} has a record"
            raise CveServicesError(msg, 400)

    monkeypatch.setattr(cve_services, "reject", reject_published_with_put)

    assignment = cve_publication.reject(report, "Duplicate of CVE-2025-0001", cve_publication.credentials(ORGANIZATION))

    assert service.calls == [
        ("reject", "CVE-2026-1234", "Duplicate of CVE-2025-0001", False, ORG_UUID),
        ("state", "CVE-2026-1234"),
        ("reject", "CVE-2026-1234", "Duplicate of CVE-2025-0001", True, ORG_UUID),
    ]
    assert assignment.state == REJECTED


def test_an_id_rejected_at_cve_services_already_is_taken_over(service: SimpleNamespace) -> None:
    report = _holding(_assignment(PUBLISHED))
    service.refuse.add("CVE-2026-1234")
    service.upstream["CVE-2026-1234"] = REJECTED

    assignment = cve_publication.reject(report, "Not a vulnerability", cve_publication.credentials(ORGANIZATION))

    assert [call[0] for call in service.calls] == ["reject", "state"]
    assert (assignment.state, assignment.rejected_reason, assignment.last_error) == (REJECTED, "Not a vulnerability", None)
    assert cve_publication.cve_field_value(report) is None


# -- products and reports ------------------------------------------------------------------


def test_only_a_published_cve_record_product_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = []
    monkeypatch.setattr(cve_publication, "publish", lambda items: sent.append(items) or ["CVE-2026-1234"])
    monkeypatch.setattr(Product, "_published_state_id", staticmethod(lambda: 1))
    presets = {3: SimpleNamespace(is_cve=False), 4: SimpleNamespace(is_cve=True)}
    monkeypatch.setattr(ProductPreset, "find", classmethod(lambda _cls, preset_id: presets.get(preset_id)))

    assert Product.publish_cve_records(1, 3, ["report"]) == []
    assert Product.publish_cve_records(2, 4, ["report"]) == []
    assert Product.publish_cve_records(None, 4, ["report"]) == []
    assert Product.publish_cve_records(1, 4, ["report"]) == ["CVE-2026-1234"]
    assert sent == [["report"]]


def test_the_preset_knows_it_publishes_cve_records() -> None:
    preset = SimpleNamespace(system_key=gcve.CVE_PRESET_KEY)
    assert ProductPreset.is_cve.fget(preset)
    assert not ProductPreset.is_gcve.fget(preset)
    assert ProductPreset.locked.fget(preset)


@pytest.mark.parametrize(("state", "reason"), [(RESERVED, "reject it before deleting"), (PUBLISHED, "reject it to withdraw it")])
def test_a_report_holding_a_cve_id_is_not_deleted(monkeypatch: pytest.MonkeyPatch, state: str, reason: str) -> None:
    report = SimpleNamespace(cve_assignment=_assignment(state), gcve_assignment=None)
    monkeypatch.setattr(db.session, "get", lambda _cls, _id: report)
    deleted = []
    monkeypatch.setattr(db.session, "delete", deleted.append)

    message, status = ReportItem.delete_report_item(7)

    assert status == HTTPStatus.CONFLICT
    assert reason in message
    assert deleted == []


def test_an_edit_puts_a_published_cve_record_out_of_date() -> None:
    assignment = _assignment(PUBLISHED, date_submitted=MOMENT)
    report = SimpleNamespace(cve_assignment=assignment, gcve_assignment=None)
    data: dict = {}

    assert ReportItem._update_published_record(report, data)

    assert assignment.out_of_date
    assert data["cve_record_out_of_date"] is True
    assert CveAssignment(cve_id="x", state=RESERVED, date_reserved=MOMENT).out_of_date is False


def test_the_account_never_shows_its_api_key() -> None:
    account = CveServicesAccount(id=1, environment="test", short_name="example", username="ann", org_uuid=ORG_UUID)
    account.api_key = "gAAAA-encrypted"

    shown = account.to_json()

    assert "api_key" not in shown
    assert "gAAAA-encrypted" not in str(shown)
    assert (shown["has_secret"], shown["complete"], shown["url"]) == (True, True, "https://cveawg-test.mitre.org/api")
