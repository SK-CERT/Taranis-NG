"""CVD Reports published as CVE records through CVE Services, their organization acting as a CNA.

The record is the one the GCVE record is built from (``gcve_publication.cna_content``): the CNA
container of a CVE record, which is all CVE Services takes. CVE Services sets the rest itself
(``cveMetadata``, the provider's short name and dates); the container names the CNA's UUID and
the date its CVE ID was reserved, and carries the GCVE extension once the report's GCVE record is
published too.

A CVD Report's "CVE" field holds its CVE ID. One this CNA reserved here (see model.cve_assignment)
is the report's own, and the field stays fixed while it is live; any other CVE there was assigned
by another CNA, so the report cannot be published as a CVE record of this CNA (it would be a
duplicate).

A CVD Report is published with the CVE Services account of its organization
(``report_item.organization_id``, see model.organization_gna); a CVE Record product holds the reports
of one organization. Publishing one (``publish``) checks every report first and calls CVE Services
only when all of them can be published. Each report then gets an ID if it has none, and its record
is published (or updated, when the report changed since). Every call that succeeds is committed at
once: the record is public from then on, even if a later one fails.

A call can go through at CVE Services without its answer reaching Taranis (a timeout): the ID then
stays RESERVED here while its record is published there, and publishing it again is refused. So
when CVE Services refuses a call, Taranis asks where the ID stands (``GET /cve-id/{id}``) and
catches up: a record already there is updated instead, a rejection already there is taken over,
and an ID rejected there is reported as such.
"""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from managers import cve_services, gcve_publication
from managers.cve_services import Credentials, CveServicesError
from managers.db_manager import db
from managers.log_manager import logger
from model.cve_assignment import PUBLISHED, REJECTED, RESERVED, CveAssignment
from model.cve_services_account import CveServicesAccount

from shared import gcve

if TYPE_CHECKING:
    from model.report_item import ReportItem, ReportItemAttribute

CVE_FIELD = "cve"
CONTAINER_POINTER = "definitions/cnaPublishedContainer"
# A placeholder for checking a container before the CNA's UUID is known: only its form matters.
_CHECK_ORG_UUID = "00000000-0000-4000-8000-000000000000"


class CvePublicationError(ValueError):
    """A CVE Record that cannot be published (or not completely): the message says which reports, and why."""


class CveNotConfiguredError(CvePublicationError):
    """Raised when CVE Services is to be called for an organization without a CNA account."""

    def __init__(self) -> None:
        """Say where the account is set."""
        super().__init__(
            "The organization of the CVD Report has no CVE Services account (Configuration -> Organizations -> GCVE & CVE)",
        )


def credentials(organization_id: int | None, api_key: str | None = None) -> Credentials:
    """The credentials of an organization's CNA account.

    Raises:
        CveNotConfiguredError: When the organization has no account saved.
        CveServicesError: When it is incomplete.
    """
    account = CveServicesAccount.get(organization_id)
    if account is None:
        raise CveNotConfiguredError
    return Credentials.of(account, api_key)


def credentials_for(report_item: ReportItem) -> Credentials:
    """The credentials of the CNA account of a CVD Report's organization.

    Raises:
        CveNotConfiguredError: When its organization has no account saved.
        CveServicesError: When it is incomplete.
    """
    return credentials(getattr(report_item, "organization_id", None))


def cna_uuid(credentials: Credentials) -> str:
    """The CNA's UUID, asked of CVE Services once and kept with the account.

    Raises:
        CveServicesError: When CVE Services does not say.
    """
    account = CveServicesAccount.get(credentials.organization_id)
    if account is not None and account.org_uuid:
        return account.org_uuid
    info = cve_services.org_info(credentials)
    uuid = info.get("uuid")
    if not uuid:
        msg = f"CVE Services did not give the UUID of the CNA {credentials.short_name}"
        raise CveServicesError(msg)
    if account is not None:
        account.org_uuid = str(uuid)
        db.session.commit()
    return str(uuid)


# -- the CVE field -------------------------------------------------------------------------


def cve_field_value(report_item: ReportItem) -> str | None:
    """What the report's CVE field holds; None when it is empty."""
    return gcve_publication.Fields(report_item).first(CVE_FIELD) or None


def is_cve_field(attribute: ReportItemAttribute) -> bool:
    """Whether an attribute is a CVD Report's CVE field."""
    group_item = getattr(attribute, "attribute_group_item", None)
    title = group_item.title if group_item is not None else getattr(attribute, "attribute_group_item_title", None)
    return title == gcve.cvd_fields()[CVE_FIELD].title


def cve_field_locked(report_item: ReportItem, attribute: ReportItemAttribute, value: object = None) -> str | None:
    """Why the CVE field cannot be changed to ``value`` (None: removed); None when it can.

    The CVE ID this CNA reserved for the report stays in its field while it is live: it is freed
    by rejecting it.
    """
    assignment = getattr(report_item, "cve_assignment", None)
    if assignment is None or not is_cve_field(attribute):
        return None
    if isinstance(value, str) and value.strip() == assignment.cve_id:
        return None
    return f"CVE: {assignment.cve_id} is reserved for this report; reject it to free the field"


def _set_cve_field(report_item: ReportItem, cve_id: str | None) -> None:
    """Write the CVE ID into the report's CVE field (empty it for None), adding the field if it has no value."""
    from model.report_item import ReportItemAttribute  # noqa: PLC0415 (model.report_item imports this module)

    attributes = [attribute for attribute in report_item.attributes if is_cve_field(attribute)]
    now = datetime.now(UTC)
    if attributes:
        for attribute in attributes:
            attribute.value = cve_id or ""
            attribute.last_updated = now
            attribute.version = (attribute.version or 1) + 1
        return
    if cve_id is None:
        return
    title = gcve.cvd_fields()[CVE_FIELD].title
    group_item = next(
        (
            item
            for group in getattr(report_item.report_item_type, "attribute_groups", None) or []
            for item in group.attribute_group_items
            if item.title == title
        ),
        None,
    )
    if group_item is None:
        return
    report_item.attributes.append(ReportItemAttribute(None, cve_id, "", None, 0, None, group_item.id, None))


# -- reserving and rejecting -----------------------------------------------------------------


def record_type(report_item: ReportItem) -> str:
    """The report's GCVE record type (its Record type field; advisory when it has none)."""
    return gcve_publication.Fields(report_item).first("record_type") or gcve.DEFAULT_RECORD_TYPE


def _not_an_advisory(report_item: ReportItem) -> str | None:
    """Why the report is no CVE record: one describes a vulnerability, which only an advisory does."""
    kind = record_type(report_item)
    if kind == gcve.CVE_RECORD_TYPE:
        return None
    assignment = getattr(report_item, "cve_assignment", None)
    if kind == "deprecation" and assignment is not None:
        return f"Record type: a deprecated report's CVE ID is withdrawn by rejecting it, not published again ({assignment.cve_id})"
    return f"Record type: a CVE record is published for an advisory only, and this report is a '{kind}'"


def can_get_cve(report_item: ReportItem) -> str | None:
    """Why the report cannot get a CVE ID reserved; None when it can."""
    if not getattr(report_item, "is_cvd", False):
        return "only a CVD Report gets a CVE ID"
    kind = record_type(report_item)
    if kind != gcve.CVE_RECORD_TYPE:
        return f"only an advisory gets a CVE ID, and this report is a '{kind}'"
    if report_item.cve_assignment is not None:
        return f"it has the CVE ID {report_item.cve_assignment.cve_id}"
    held = cve_field_value(report_item)
    if held:
        return f"its CVE field holds {held}, assigned by another CNA: a CVE record of it would be a duplicate"
    return None


def reserve(report_item: ReportItem, credentials: Credentials, now: datetime | None = None) -> CveAssignment:
    """Reserve a CVE ID for the report and write it into its CVE field (committed).

    Raises:
        CvePublicationError: When the report cannot get one.
        CveServicesError: When CVE Services refuses.
    """
    reason = can_get_cve(report_item)
    if reason is not None:
        raise CvePublicationError(reason)
    now = now or datetime.now(UTC)
    cve_id = cve_services.reserve(credentials, now.year)
    assignment = CveAssignment.reserve(report_item, cve_id, now)
    _set_cve_field(report_item, cve_id)
    _touch_gcve_record(report_item)
    db.session.commit()
    logger.info(f"CVE ID {cve_id} reserved for report item {report_item.id}")
    return assignment


def reject(report_item: ReportItem, reason: str, credentials: Credentials) -> CveAssignment:
    """Reject the report's CVE ID at CVE Services, and free its CVE field (committed).

    Raises:
        CvePublicationError: When it has none, or no reason is given.
        CveServicesError: When CVE Services refuses.
    """
    assignment = report_item.cve_assignment
    if assignment is None:
        msg = "the report has no CVE ID to reject"
        raise CvePublicationError(msg)
    reason = (reason or "").strip()
    if not reason:
        msg = "a CVE ID is rejected with a reason"
        raise CvePublicationError(msg)
    try:
        _send_rejection(credentials, assignment, reason, cna_uuid(credentials))
    except CveServicesError as error:
        assignment.failed(str(error))
        db.session.commit()
        raise
    assignment.reject(reason)
    _set_cve_field(report_item, None)
    _touch_gcve_record(report_item)
    db.session.commit()
    logger.info(f"CVE ID {assignment.cve_id} of report item {report_item.id} rejected")
    return assignment


def _upstream_state(credentials: Credentials, cve_id: str, refusal: CveServicesError) -> str | None:
    """Where an ID stands at CVE Services after it refused a call about it; None when that cannot be told.

    A refusal may only mean that Taranis is behind: an earlier call went through there while its
    answer was lost. Nothing is asked when CVE Services did not answer at all, or refused the
    credentials: asking again would tell nothing.
    """
    if refusal.status is None or refusal.status == HTTPStatus.UNAUTHORIZED:
        return None
    try:
        return cve_services.id_state(credentials, cve_id)
    except CveServicesError as error:
        logger.warning(f"Where {cve_id} stands at CVE Services cannot be told: {error}")
        return None


def _send_rejection(credentials: Credentials, assignment: CveAssignment, reason: str, org_uuid: str) -> None:
    """Reject an ID at CVE Services, catching up with a record or a rejection that is there already.

    Raises:
        CveServicesError: When CVE Services refuses, and the ID is not rejected there either.
    """
    try:
        cve_services.reject(credentials, assignment.cve_id, reason, published=assignment.published, org_uuid=org_uuid)
    except CveServicesError as error:
        state = _upstream_state(credentials, assignment.cve_id, error)
        if state == REJECTED:
            # Rejected there already (an earlier rejection whose answer was lost): taken over as it is.
            logger.info(f"CVE ID {assignment.cve_id} is already rejected at CVE Services")
            return
        if not (state == PUBLISHED and not assignment.published):
            raise
        # Its record was published there after all: a published record is rejected with PUT.
        cve_services.reject(credentials, assignment.cve_id, reason, published=True, org_uuid=org_uuid)


def _touch_gcve_record(report_item: ReportItem) -> None:
    """A published GCVE record names the CVE ID: it changed with it."""
    gcve_assignment = getattr(report_item, "gcve_assignment", None)
    if gcve_assignment is not None:
        gcve_assignment.touch()


# -- the record ------------------------------------------------------------------------------


def cna_container(report_item: ReportItem, assignment: CveAssignment | None, org_uuid: str) -> dict:
    """The CNA container of the report's CVE record, as CVE Services takes it.

    Raises:
        gcve_publication.RecordProblemError: When a CVSS value is not a vector.
    """
    fields = gcve_publication.Fields(report_item)
    container: dict[str, Any] = {"providerMetadata": {"orgId": org_uuid}}
    if assignment is not None:
        container["dateAssigned"] = gcve_publication.timestamp(assignment.date_reserved)
    container.update(gcve_publication.cna_content(report_item, fields))
    gcve_assignment = getattr(report_item, "gcve_assignment", None)
    if gcve_assignment is not None and gcve_assignment.published:
        container["x_gcve"] = [gcve_publication.x_gcve(fields, gcve_assignment)]
    return container


def problems(report_item: ReportItem, org_uuid: str | None = None) -> list[str]:
    """Why a report cannot be published as a CVE record of this CNA; empty when it can."""
    found = gcve_publication.content_problems(report_item, gcve.CVE_PRESET_NAME)
    if found and found[0].startswith("only CVD Reports"):
        return found
    reason = _not_an_advisory(report_item)
    if reason is not None:
        found.append(reason)
    assignment = report_item.cve_assignment
    held = cve_field_value(report_item)
    if assignment is None and held:
        found.append(f"CVE: {held} was not reserved by this CNA; clear the field, and a CVE ID is reserved when it is published")
    elif assignment is not None and held != assignment.cve_id:
        found.append(f"CVE: the field must hold the CVE ID reserved for the report, {assignment.cve_id}")
    if found:
        return found
    try:
        container = cna_container(report_item, assignment, org_uuid or _CHECK_ORG_UUID)
    except gcve_publication.RecordProblemError as error:
        return [f"CVSS: {error}"]
    return [f"record: {message}" for message in gcve_publication.schema_errors(container, pointer=CONTAINER_POINTER)]


def _send_record(credentials: Credentials, report_item: ReportItem, assignment: CveAssignment, org_uuid: str) -> None:
    """Send a report's record: published for a reserved ID, updated for a published one.

    A reserved ID whose record CVE Services has already (an earlier publication went through, its
    answer lost) is updated instead.

    Raises:
        CveServicesError: When CVE Services refuses the record.
        CvePublicationError: When the ID is rejected at CVE Services.
    """
    container = cna_container(report_item, assignment, org_uuid)
    first = assignment.state == RESERVED
    try:
        if first:
            cve_services.publish(credentials, assignment.cve_id, container)
        else:
            cve_services.update(credentials, assignment.cve_id, container)
    except CveServicesError as error:
        state = _upstream_state(credentials, assignment.cve_id, error)
        if state == REJECTED:
            msg = (
                f"{assignment.cve_id} is rejected at CVE Services: reject it here too, and the report gets a new CVE ID when it is published"
            )
            raise CvePublicationError(msg) from error
        if not (first and state == PUBLISHED):
            raise
        logger.info(f"CVE record {assignment.cve_id} is published at CVE Services already: it is updated instead")
        cve_services.update(credentials, assignment.cve_id, container)


def _label(report_item: ReportItem) -> str:
    assignment = report_item.cve_assignment
    return assignment.cve_id if assignment is not None else (report_item.title or f"report {report_item.id}")


def publish(report_items: list[ReportItem]) -> list[str]:
    """Publish the reports of a CVE Record product to CVE Services: each new record, each changed one.

    Every report is checked before anything is sent. Then each one without a CVE ID gets one, and
    its record is published, or updated when the report changed since it was last sent; a record
    that is up to date is left alone. Each success is committed at once.

    Returns:
        list[str]: The CVE IDs whose records were sent.

    Raises:
        CvePublicationError: When a report cannot be published (nothing was sent), or when CVE
            Services refused some (the others were sent; the message says which).
    """
    if not report_items:
        return []
    organizations = {getattr(item, "organization_id", None) for item in report_items}
    if len(organizations) > 1:
        msg = "A CVE Record holds the CVD Reports of one organization"
        raise CvePublicationError(msg)
    try:
        account_credentials = credentials(next(iter(organizations), None))
        uuid = cna_uuid(account_credentials)
    except CveServicesError as error:
        raise CvePublicationError(str(error)) from error

    reasons = [f"{_label(item)}: {'; '.join(found)}" for item in report_items if (found := problems(item, uuid))]
    if reasons:
        raise CvePublicationError("The CVE Record cannot be published. " + " | ".join(reasons))

    sent: list[str] = []
    failed: list[str] = []
    for item in report_items:
        assignment = item.cve_assignment
        try:
            if assignment is None:
                assignment = reserve(item, account_credentials)
            if assignment.state != RESERVED and not (assignment.out_of_date or assignment.date_submitted is None):
                continue
            _send_record(account_credentials, item, assignment, uuid)
        except (CveServicesError, CvePublicationError) as error:
            if assignment is not None:
                assignment.failed(str(error))
                db.session.commit()
            failed.append(f"{_label(item)}: {error}")
            continue
        assignment.submitted()
        db.session.commit()
        sent.append(assignment.cve_id)
        logger.info(f"CVE record {assignment.cve_id} sent to CVE Services")

    if failed:
        done = f" Sent: {', '.join(sent)}." if sent else ""
        raise CvePublicationError(f"CVE Services refused {len(failed)} record(s).{done} " + " | ".join(failed))
    return sent
