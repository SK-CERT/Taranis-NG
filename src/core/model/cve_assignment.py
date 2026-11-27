"""CVE IDs this organisation reserved through CVE Services as a CNA, and their records' state.

A CVD Report gets a CVE ID from the CNA account (see model.cve_services_account), either when an
analyst reserves one for it or when a "CVE Record" product holding it is published. The ID is
RESERVED until its record is published to CVE Services, PUBLISHED from then on, and REJECTED once
the CNA rejected it (with the reason it gave). A rejected ID stays here, still linked to its report,
which may then get another one: at most one ID per report is live.

Edits to a published report do not reach CVE Services by themselves: ``date_changed`` notes them,
and the record is out of date until the next publication of a CVE Record product sends it again
(``date_submitted``). ``last_error`` keeps what CVE Services said when a call failed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from managers.db_manager import db
from sqlalchemy import CheckConstraint, Index, text

if TYPE_CHECKING:
    from model.report_item import ReportItem

RESERVED = "RESERVED"
PUBLISHED = "PUBLISHED"
REJECTED = "REJECTED"
STATES = (RESERVED, PUBLISHED, REJECTED)

# CVE Services' messages can be long (schema errors); what is kept of one.
MAX_ERROR_LENGTH = 2000


class CveAssignment(db.Model):
    """A CVE ID reserved for a CVD Report, and where its record stands at CVE Services.

    Attributes:
        cve_id: ``CVE-<year>-<number>``, as CVE Services reserved it.
        report_item_id: The CVD Report; None once it is deleted.
        state: RESERVED, PUBLISHED or REJECTED.
        rejected_reason: Why it was rejected (sent to CVE Services).
        date_reserved: When it was reserved.
        date_published: When its record was first published.
        date_submitted: When its record was last sent (published or updated).
        date_changed: When the published report last changed.
        last_error: What CVE Services said when the last call about it failed.
    """

    __tablename__ = "cve_assignment"
    __table_args__ = (
        CheckConstraint("state IN ('RESERVED', 'PUBLISHED', 'REJECTED')", name="ck_cve_assignment_state"),
        # One live (not rejected) CVE ID per report.
        Index(
            "uq_cve_assignment_live_report",
            "report_item_id",
            unique=True,
            postgresql_where=text("state <> 'REJECTED' AND report_item_id IS NOT NULL"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    cve_id = db.Column(db.String(64), nullable=False, unique=True)
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="SET NULL"), nullable=True, index=True)
    state = db.Column(db.String(16), nullable=False, default=RESERVED)
    rejected_reason = db.Column(db.Text, nullable=True)
    date_reserved = db.Column(db.DateTime(timezone=True), nullable=False)
    date_published = db.Column(db.DateTime(timezone=True), nullable=True)
    date_submitted = db.Column(db.DateTime(timezone=True), nullable=True)
    date_changed = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(db.Text, nullable=True)

    report_item = db.relationship("ReportItem", back_populates="cve_assignments")

    @classmethod
    def reserve(cls, report_item: ReportItem, cve_id: str, now: datetime | None = None) -> CveAssignment:
        """Note that ``cve_id`` was reserved for ``report_item``, in the caller's transaction."""
        assignment = cls(cve_id=cve_id, state=RESERVED, date_reserved=now or datetime.now(UTC))
        assignment.report_item = report_item
        db.session.add(assignment)
        return assignment

    @classmethod
    def find_by_cve_id(cls, cve_id: str) -> CveAssignment | None:
        """The assignment of a CVE ID, if this CNA reserved it here."""
        return cls.query.filter_by(cve_id=cve_id).first()

    @property
    def live(self) -> bool:
        """Whether the ID is still in use (not rejected)."""
        return self.state != REJECTED

    @property
    def published(self) -> bool:
        """Whether its record has been published to CVE Services."""
        return self.state == PUBLISHED

    @property
    def out_of_date(self) -> bool:
        """Whether the published record lags behind the report."""
        if self.state != PUBLISHED or self.date_changed is None:
            return False
        return self.date_submitted is None or self.date_changed > self.date_submitted

    def submitted(self, now: datetime | None = None) -> None:
        """Note that CVE Services accepted the record (first publication or update)."""
        now = now or datetime.now(UTC)
        if self.state == RESERVED:
            self.state = PUBLISHED
            self.date_published = now
        self.date_submitted = now
        self.last_error = None

    def failed(self, error: str) -> None:
        """Note what CVE Services said when a call about this ID failed."""
        self.last_error = error[:MAX_ERROR_LENGTH]

    def reject(self, reason: str) -> None:
        """Note that the CNA rejected the ID."""
        self.state = REJECTED
        self.rejected_reason = reason
        self.last_error = None

    def changed(self, now: datetime | None = None) -> None:
        """Note that the published report changed: its record is out of date."""
        if self.state == PUBLISHED:
            self.date_changed = now or datetime.now(UTC)

    def to_json(self) -> dict:
        """What the GUI shows of it."""
        return {
            "cve_id": self.cve_id,
            "state": self.state,
            "out_of_date": self.out_of_date,
            "last_error": self.last_error,
            "rejected_reason": self.rejected_reason,
            "date_reserved": self.date_reserved.isoformat() if self.date_reserved else None,
            "date_published": self.date_published.isoformat() if self.date_published else None,
            "date_submitted": self.date_submitted.isoformat() if self.date_submitted else None,
        }
