"""An organization as a GCVE Numbering Authority (GNA), and what it publishes CVD Reports as.

gcve.eu gives a GNA its number. The GNA's short and full name are in the GNA directory gcve.eu
publishes (see managers.gna_directory): they are copied from there, never typed in, and the
records name the GNA by that short name. The organization also says what licence its records are
published under, and what its conformance document (GCVE-BCP-06) adds.

A CVD Report belongs to the organization of its author (``report_item.organization_id``): it gets
its GCVE identifier from that organization's GNA number and its CVE ID from that organization's
CVE Services account (model.cve_services_account). An organization a CVD Report can be written for
has at least one of them.

The GNA number is fixed once identifiers were allocated with it (GCVE-BCP-06: one is never
given again), and no two organizations have the same one.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from managers.db_manager import db
from model.cve_services_account import CveServicesAccount
from model.gcve_assignment import GcveAssignment
from shared.common import TZ
from shared.gcve import DEFAULT_RECORDS_LICENSE, GNA_ID_MAX, GNA_ID_MIN
from sqlalchemy import CheckConstraint

if TYPE_CHECKING:
    from model.organization import Organization
    from model.user import User

MAX_LICENSE = 255


class GnaSettingsError(ValueError):
    """A GNA setting of an organization that is not acceptable; the message says why."""

    def __init__(self, message: str, conflict: bool = False) -> None:
        """Keep whether it conflicts with what exists (another GNA, allocated identifiers)."""
        super().__init__(message)
        self.conflict = conflict


class CvdNotConfiguredError(ValueError):
    """Raised when a CVD Report is written by a user none of whose organizations can publish one.

    A CVD Report is published as a GCVE record (its organization needs a GNA number) or a CVE
    record (its organization needs a CVE Services account).
    """

    def __init__(self) -> None:
        """Say what is missing and where to set it."""
        super().__init__(
            "A CVD Report is published as a GCVE or a CVE record of its author's organization: none of your "
            "organizations has a GNA number or a CVE Services account yet (Configuration -> Organizations).",
        )


class OrganizationGna(db.Model):
    """An organization's GNA.

    Attributes:
        organization_id: The organization.
        gna_id: The GNA number gcve.eu allocated.
        short_name: The GNA's short name, from the GNA directory; None while the directory has not
            confirmed the number.
        directory: The directory's entry for the number (names, registered addresses).
        directory_checked_at: When the directory was last asked about it.
        records_license: The licence the records are published under.
        conformance: What the conformance document adds (governance, contacts, ...).
    """

    __tablename__ = "organization_gna"

    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True, autoincrement=False)
    gna_id = db.Column(db.Integer, nullable=False, unique=True)
    short_name = db.Column(db.String(32), nullable=True)
    directory = db.Column(db.JSON, nullable=True)
    directory_checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    records_license = db.Column(db.String(MAX_LICENSE), nullable=False, default=DEFAULT_RECORDS_LICENSE)
    conformance = db.Column(db.JSON, nullable=True)
    updated_by = db.Column(db.String(), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    organization = db.relationship("Organization")

    __table_args__ = (CheckConstraint(f"gna_id BETWEEN {GNA_ID_MIN} AND {GNA_ID_MAX}", name="ck_organization_gna_gna_id"),)

    @classmethod
    def for_organization(cls, organization_id: int | None) -> OrganizationGna | None:
        """The GNA of an organization; None when it has no GNA number."""
        return db.session.get(cls, organization_id) if organization_id is not None else None

    @classmethod
    def find_by_gna(cls, gna_id: int | None) -> OrganizationGna | None:
        """The organization's GNA holding a number; None when no organization holds it."""
        return cls.query.filter_by(gna_id=gna_id).first() if gna_id is not None else None

    @classmethod
    def all(cls) -> list[OrganizationGna]:
        """Every organization's GNA, by number."""
        return cls.query.order_by(cls.gna_id).all()

    @property
    def frozen(self) -> bool:
        """Whether identifiers were allocated with its number: then the number stays."""
        return GcveAssignment.any_exists(self.gna_id)

    def to_json(self) -> dict:
        """The GNA as the organization's settings show it."""
        return {
            "gna_id": self.gna_id,
            "short_name": self.short_name,
            "directory": self.directory,
            "directory_checked_at": self.directory_checked_at.isoformat() if self.directory_checked_at else None,
            "records_license": self.records_license,
            "conformance": self.conformance,
            "frozen": self.frozen,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def save(
        cls,
        organization_id: int,
        gna_id: int | None,
        records_license: str | None,
        conformance: dict | None,
        user_name: str,
    ) -> OrganizationGna | None:
        """Set (or, with no number, remove) an organization's GNA, in the caller's transaction.

        Raises:
            GnaSettingsError: For a number out of range, one another organization holds, or a
                change of a number identifiers were allocated with.
        """
        gna = cls.for_organization(organization_id)
        if gna_id is not None and not GNA_ID_MIN <= gna_id <= GNA_ID_MAX:
            msg = f"The GNA number is a whole number from {GNA_ID_MIN} to {GNA_ID_MAX}"
            raise GnaSettingsError(msg)
        if gna is not None and gna.gna_id != gna_id and gna.frozen:
            msg = f"GCVE identifiers have been allocated with the GNA number {gna.gna_id}: it cannot change any more"
            raise GnaSettingsError(msg, conflict=True)
        if gna_id is None:
            if gna is not None:
                db.session.delete(gna)
            return None
        holder = cls.find_by_gna(gna_id)
        if holder is not None and holder.organization_id != organization_id:
            name = holder.organization.name if holder.organization is not None else holder.organization_id
            msg = f"The GNA number {gna_id} is the one of the organization {name}"
            raise GnaSettingsError(msg, conflict=True)
        license_name = (records_license or "").strip() or DEFAULT_RECORDS_LICENSE
        if len(license_name) > MAX_LICENSE:
            msg = f"The licence is at most {MAX_LICENSE} characters"
            raise GnaSettingsError(msg)
        if conformance is not None and not isinstance(conformance, dict):
            msg = "The conformance details are a JSON object"
            raise GnaSettingsError(msg)
        if gna is None:
            gna = cls(organization_id=organization_id, gna_id=gna_id)
            db.session.add(gna)
        if gna.gna_id != gna_id:
            # Another number: what the directory said about the old one no longer applies.
            gna.gna_id = gna_id
            gna.short_name = None
            gna.directory = None
            gna.directory_checked_at = None
        gna.records_license = license_name
        gna.conformance = conformance or None
        gna.updated_by = user_name
        gna.updated_at = datetime.now(TZ)
        return gna


# -- the organizations a CVD Report can belong to ----------------------------------------------


def cvd_targets(organization: Organization) -> dict:
    """What a CVD Report of the organization is published as: ``{id, name, gna_id, short_name, gna_configured, cna_configured}``."""
    gna = OrganizationGna.for_organization(organization.id)
    return {
        "id": organization.id,
        "name": organization.name,
        "gna_id": gna.gna_id if gna is not None else None,
        "short_name": gna.short_name if gna is not None else None,
        "gna_configured": gna is not None,
        "cna_configured": CveServicesAccount.configured(organization.id) is not None,
    }


def cvd_organizations(user: User) -> list[dict]:
    """The user's organizations a CVD Report can be written for (see cvd_targets), by name."""
    targets = [cvd_targets(organization) for organization in sorted(user.organizations or [], key=lambda org: (org.name or "", org.id))]
    return [target for target in targets if target["gna_configured"] or target["cna_configured"]]


def cvd_organization_for(user: User, organization_id: object) -> int:
    """The organization a CVD Report the user writes belongs to: the one asked for, or their only one.

    Args:
        user: The author.
        organization_id: The organization picked in the form; None: the author's only one.

    Returns:
        int: The organization's id.

    Raises:
        CvdNotConfiguredError: When none of the user's organizations can publish a CVD Report.
        ValueError: When the one asked for is not one of them, or none was picked among several.
    """
    eligible = cvd_organizations(user)
    if not eligible:
        raise CvdNotConfiguredError
    if organization_id in (None, ""):
        if len(eligible) == 1:
            return eligible[0]["id"]
        msg = "Pick the organization the CVD Report is published by: you are a member of several"
        raise ValueError(msg)
    try:
        wanted = int(organization_id)
    except (TypeError, ValueError):
        wanted = None
    if wanted not in {target["id"] for target in eligible}:
        msg = "A CVD Report belongs to one of your organizations that has a GNA number or a CVE Services account"
        raise ValueError(msg)
    return wanted


def organization_delete_refused(organization_id: int) -> str | None:
    """Why an organization cannot be deleted for its GCVE and CVE publications; None when it can."""
    from model.public_web import PublicWeb  # noqa: PLC0415 (model.public_web imports a lot)
    from model.report_item import ReportItem  # noqa: PLC0415 (model.report_item imports this module)

    if db.session.query(ReportItem.id).filter(ReportItem.organization_id == organization_id).limit(1).first() is not None:
        return "It owns CVD Reports"
    gna = OrganizationGna.for_organization(organization_id)
    if gna is not None and gna.frozen:
        return f"GCVE identifiers have been allocated with its GNA number {gna.gna_id}"
    names = [web.name or web.hostname for web in PublicWeb.query.all() if web.gcve_organization_id == organization_id]
    if names:
        return f"The public web {', '.join(sorted(names))} publishes its GCVE records"
    return None
