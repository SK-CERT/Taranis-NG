"""GCVE identifiers this Taranis allocated as a GCVE Numbering Authority (see shared.gcve).

A CVD Report gets ``GCVE-<GNA>-<year>-<number>`` from the GNA number of its organization (see
model.organization_gna): when it is created, if the organization has one then, otherwise when it is
first published in a GCVE Advisory. The number is the next of its year: ``gcve_counter`` keeps the
last one per GNA and year, incremented in the transaction that allocates it, so two reports never
share a number and a report that fails to be created gives its number back. An identifier is never
reused (GCVE-BCP-06): its row in ``gcve_assignment`` stays when the report is deleted, marked
REJECTED.

A record is RESERVED until a GCVE Advisory holding its report is published, PUBLISHED from then on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from managers.db_manager import db
from shared.gcve import gcve_id
from sqlalchemy import CheckConstraint, UniqueConstraint, text

if TYPE_CHECKING:
    from model.report_item import ReportItem

RESERVED = "RESERVED"
PUBLISHED = "PUBLISHED"
REJECTED = "REJECTED"
STATES = (RESERVED, PUBLISHED, REJECTED)


class GcveCounter(db.Model):
    """The last number allocated, per GNA and year."""

    __tablename__ = "gcve_counter"

    gna_id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    year = db.Column(db.Integer, primary_key=True, autoincrement=False)
    last_number = db.Column(db.Integer, nullable=False)


class GcveAssignment(db.Model):
    """A GCVE identifier and the CVD Report it was allocated to.

    Attributes:
        gcve_id: ``GCVE-<GNA>-<year>-<number>``.
        report_item_id: The CVD Report; None once it is deleted.
        state: RESERVED, PUBLISHED or REJECTED.
        date_reserved: When the identifier was allocated.
        date_published: When a GCVE Advisory holding the report was first published.
        date_updated: When the published record last changed.
    """

    __tablename__ = "gcve_assignment"
    __table_args__ = (
        UniqueConstraint("gna_id", "year", "number", name="uq_gcve_assignment_number"),
        CheckConstraint("state IN ('RESERVED', 'PUBLISHED', 'REJECTED')", name="ck_gcve_assignment_state"),
    )

    id = db.Column(db.Integer, primary_key=True)
    gcve_id = db.Column(db.String(255), nullable=False, unique=True)
    gna_id = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="SET NULL"), nullable=True, unique=True)
    state = db.Column(db.String(16), nullable=False, default=RESERVED)
    date_reserved = db.Column(db.DateTime(timezone=True), nullable=False)
    date_published = db.Column(db.DateTime(timezone=True), nullable=True)
    date_updated = db.Column(db.DateTime(timezone=True), nullable=True)

    report_item = db.relationship("ReportItem", back_populates="gcve_assignment")

    @classmethod
    def allocate(cls, report_item: ReportItem, gna_id: int, now: datetime | None = None) -> GcveAssignment:
        """Give ``report_item`` the next identifier of this year, in the caller's transaction.

        The counter row is locked by the upsert until the transaction ends, so concurrent
        allocations wait for each other; a rollback gives the number back.

        Args:
            report_item: The CVD Report being created.
            gna_id: The GNA number.
            now: The moment of allocation (UTC); now when left out.

        Returns:
            GcveAssignment: The assignment, added to the session.
        """
        now = now or datetime.now(UTC)
        number = db.session.execute(
            text(
                "INSERT INTO gcve_counter (gna_id, year, last_number) VALUES (:gna_id, :year, 1) "
                "ON CONFLICT (gna_id, year) DO UPDATE SET last_number = gcve_counter.last_number + 1 "
                "RETURNING last_number",
            ),
            {"gna_id": gna_id, "year": now.year},
        ).scalar_one()
        assignment = cls(
            gcve_id=gcve_id(gna_id, now.year, number),
            gna_id=gna_id,
            year=now.year,
            number=number,
            state=RESERVED,
            date_reserved=now,
        )
        assignment.report_item = report_item
        db.session.add(assignment)
        return assignment

    @classmethod
    def any_exists(cls, gna_id: int) -> bool:
        """Whether identifiers have been allocated with a GNA number (it is fixed from then on)."""
        return db.session.query(cls.id).filter(cls.gna_id == gna_id).limit(1).first() is not None

    @classmethod
    def find_by_report_item(cls, report_item_id: int) -> GcveAssignment | None:
        """The assignment of a report item, if it has one."""
        return cls.query.filter_by(report_item_id=report_item_id).first()

    @property
    def published(self) -> bool:
        """Whether its record has been published."""
        return self.state == PUBLISHED

    def publish(self, now: datetime | None = None) -> None:
        """Mark the record published, the first time a GCVE Advisory holding it is published."""
        if self.state == RESERVED:
            self.state = PUBLISHED
            self.date_published = now or datetime.now(UTC)

    def reject(self) -> None:
        """Mark the identifier unused for good: its report was deleted before it was published."""
        self.state = REJECTED
        self.report_item = None

    def touch(self, now: datetime | None = None) -> None:
        """Note that the published record changed."""
        if self.state == PUBLISHED:
            self.date_updated = now or datetime.now(UTC)
