"""Attribute extraction rules.

Detect vulnerability identifiers in news item text during collection and store each hit as a
news item attribute. Creates the rule table and its source-group scoping table, seeds the
preconfigured patterns, and adds the config permissions.

Revision ID: d4f1c8a70b62
Revises: d5c81f60a473
Create Date: 2026-08-29 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "d4f1c8a70b62"
down_revision = "d5c81f60a473"
branch_labels = None
depends_on = None

PERMISSIONS = [
    ("CONFIG_ATTRIBUTE_EXTRACTION_ACCESS", "Config attribute extraction access", "Access to attribute extraction rules"),
    ("CONFIG_ATTRIBUTE_EXTRACTION_CREATE", "Config attribute extraction create", "Create attribute extraction rules"),
    ("CONFIG_ATTRIBUTE_EXTRACTION_UPDATE", "Config attribute extraction update", "Update attribute extraction rules"),
    ("CONFIG_ATTRIBUTE_EXTRACTION_DELETE", "Config attribute extraction delete", "Delete attribute extraction rules"),
]

# (name, attribute_key, pattern, description)
#
# EPSS is deliberately absent: it is a score published by FIRST.org and keyed off a CVE, so
# it never appears in article text and cannot be matched by a regular expression. A CVSS
# *vector* is a literal string and is matched below; a CVSS *score* usually is not.
SEEDED_RULES = [
    # \b: without it the tail of a GCVE ID with a four-digit GNA (GCVE-1337-2025-0001) reads as CVE-1337-2025.
    ("CVE", "CVE", r"\bCVE-\d{4}-\d{4,}", "Common Vulnerabilities and Exposures identifier"),
    ("CWE", "CWE", r"CWE-\d+", "Common Weakness Enumeration identifier"),
    (
        "GHSA",
        "GHSA",
        r"GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}",
        "GitHub Security Advisory identifier",
    ),
    ("RHSA", "RHSA", r"RHSA-\d{4}:\d+", "Red Hat Security Advisory identifier"),
    ("EUVD", "EUVD", r"EUVD-\d{4}-\d+", "European Union Vulnerability Database identifier"),
    # A GCVE identifier is GCVE-<GNA ID>-<local ID>. Each GNA picks its own local IDs, so the local
    # ID is any printable ASCII from \x22 to \x7E, and the whole identifier is 8 to 255 characters:
    # ^(?=.{8,255}$)GCVE-[0-9]+-[\x22-\x7E]+$ as a validation expression. This rule searches inside
    # news item text, so it keeps that character set and length but has no anchors, stops at HTML
    # delimiters (< > " '), and leaves trailing sentence punctuation (. , ; : ! ? )) out of the value.
    # An identifier over 255 characters yields nothing rather than a truncated prefix. The minimum
    # of 8 needs no check: GCVE-, a digit, - and one character.
    (
        "GCVE",
        "GCVE",
        (
            # From GCVE-: at most 250 more characters up to the last one that is not trailing
            # punctuation, so the identifier is at most 255 long; the run then ends, apart from
            # trailing punctuation.
            r"""GCVE-(?=(?:(?![<>"'])[\x22-\x7E]){0,249}(?![<>"'.,;:!?)])[\x22-\x7E][.,;:!?)]*(?:[<>"']|[^\x22-\x7E]|$))"""
            # The identifier itself: GNA ID, then the local ID ending on a character that is not
            # trailing punctuation.
            r"""[0-9]+-(?:(?![<>"'])[\x22-\x7E])*(?![<>"'.,;:!?)])[\x22-\x7E]"""
        ),
        "Global CVE identifier: GCVE-<GNA ID>-<local ID>, printable ASCII, 8 to 255 characters",
    ),
    # The CPE 2.3 formatted-string character set (NISTIR 7695; NVD's cpe23Uri pattern): letters, digits,
    # _ - . and the * ? wildcards unescaped, anything else only after a backslash. So < > " ' end the
    # value, as HTML around it needs, and a period only counts when more of the value follows it, so
    # a sentence's full stop is left out. Vendor and product are required, then up to eight more fields.
    (
        "CPE",
        "CPE",
        r"cpe:2\.3:[aho](?::(?:[A-Za-z0-9_\-*?]|\\[^\s]|\.(?=[A-Za-z0-9_\-*?\\]))+){2,10}",
        "Common Platform Enumeration 2.3 name",
    ),
    (
        "CVSS v2 vector",
        "CVSS",
        # v2 temporal and environmental values are up to three letters; longer ones are tried first.
        r"\bAV:[LAN]/AC:[HML]/Au:[MSN]/C:[NPC]/I:[NPC]/A:[NPC](?:/(?:E|RL|RC|CDP|TD|CR|IR|AR):(?:POC|ND|OF|TF|UC|UR|LM|MH|[A-Z]))*\b",
        (
            "CVSS v2 vector, including any temporal or environmental metrics. It carries no CVSS: prefix, so the full six-metric "
            "base is required; Au: appears only in v2."
        ),
    ),
    (
        "CVSS v3.x vector",
        "CVSS",
        # Metric names are up to three letters (MAV, MAC, MPR, MUI), values one letter.
        r"CVSS:3\.[01]/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH](?:/[A-Z]{1,3}:[A-Z])*",
        "CVSS v3.0 and v3.1 vector, including any trailing temporal or environmental metrics",
    ),
    (
        "CVSS v4.0 vector",
        "CVSS",
        # Threat, environmental and supplemental metrics follow the base. U: takes a word, tried before
        # the single letter so that U:Clear is not cut to U:C.
        (
            r"CVSS:4\.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/VC:[HLN]/VI:[HLN]/VA:[HLN]/SC:[HLN]/SI:[HLN]/SA:[HLN]"
            r"(?:/[A-Z]{1,3}:(?:Clear|Green|Amber|Red|[A-Z]))*"
        ),
        "CVSS v4.0 vector, including any threat, environmental or supplemental metrics",
    ),
]


class PermissionAER(Base):
    """Minimal permission mapping for seeding."""

    __tablename__ = "permission"
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())

    def __init__(self, id: str, name: str, description: str) -> None:  # noqa: A002
        """Create a permission row."""
        self.id = id
        self.name = name
        self.description = description

    @staticmethod
    def add(session: Session, id: str, name: str, description: str) -> None:  # noqa: A002
        """Insert a permission when it is not already present."""
        if not session.query(PermissionAER).filter_by(id=id).first():
            session.add(PermissionAER(id, name, description))

    @staticmethod
    def delete(session: Session, id: str) -> None:  # noqa: A002
        """Remove a permission and, by cascade, its role and user grants."""
        perm = session.query(PermissionAER).filter_by(id=id).first()
        if perm:
            session.delete(perm)


class RoleAER(Base):
    """Minimal role mapping for granting the new permissions to Admin."""

    __tablename__ = "role"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    permissions = orm.relationship(PermissionAER, secondary="role_permission")


class RolePermissionAER(Base):
    """Minimal role/permission association."""

    __tablename__ = "role_permission"
    role_id = sa.Column(sa.Integer, sa.ForeignKey("role.id"), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey("permission.id"), primary_key=True)


RULE_TABLE = "attribute_extraction_rule"
SCOPE_TABLE = "attribute_extraction_rule_osint_source_group"


def _drop_empty_premature_tables() -> set[str]:
    """Drop the tables a core started before this migration created on its own.

    `create_app()` runs `db.create_all()`, so a core that started with the attribute extraction
    model while the database was still at the previous revision has already created both tables:
    empty, and without the ON DELETE CASCADE declared below. `op.create_table` then failed on every
    start with DuplicateTable. Empty ones are dropped and recreated, so the result matches a clean
    upgrade. A table that holds rows is kept rather than lose them.

    Returns:
        set[str]: The tables that still exist.
    """
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table in (SCOPE_TABLE, RULE_TABLE):  # the scope table references the rule table, so it goes first
        if table in existing and bind.execute(sa.select(sa.literal(1)).select_from(sa.table(table)).limit(1)).first() is None:
            op.drop_table(table)
            existing.discard(table)
    return existing


def upgrade() -> None:
    """Create the tables, seed the rules, and add the permissions."""
    kept = _drop_empty_premature_tables()
    if RULE_TABLE not in kept:
        op.create_table(
            RULE_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("attribute_key", sa.String(), nullable=False),
            sa.Column("pattern", sa.String(), nullable=False),
            sa.Column("description", sa.String(), server_default="", nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("capture_group", sa.Integer(), server_default="0", nullable=False),
            sa.Column("max_matches", sa.Integer(), server_default="100", nullable=False),
            sa.Column("updated_by", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    if SCOPE_TABLE not in kept:
        op.create_table(
            SCOPE_TABLE,
            sa.Column("attribute_extraction_rule_id", sa.Integer(), nullable=False),
            sa.Column("osint_source_group_id", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["attribute_extraction_rule_id"], ["attribute_extraction_rule.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["osint_source_group_id"], ["osint_source_group.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("attribute_extraction_rule_id", "osint_source_group_id"),
        )

    session = Session(bind=op.get_bind())

    rules = sa.table(
        RULE_TABLE,
        sa.column("name", sa.String),
        sa.column("attribute_key", sa.String),
        sa.column("pattern", sa.String),
        sa.column("description", sa.String),
    )
    # Only the missing ones: a kept table may already hold some of these names, which are unique.
    present = {name for (name,) in op.get_bind().execute(sa.select(rules.c.name))}
    missing = [
        {"name": name, "attribute_key": key, "pattern": pattern, "description": description}
        for name, key, pattern, description in SEEDED_RULES
        if name not in present
    ]
    if missing:
        op.bulk_insert(rules, missing)

    for permission_id, name, description in PERMISSIONS:
        PermissionAER.add(session, permission_id, name, description)
    session.commit()

    role = session.query(RoleAER).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(PermissionAER).all()
        session.add(role)
        session.commit()


def downgrade() -> None:
    """Drop the tables and remove the permissions."""
    session = Session(bind=op.get_bind())

    for permission_id, _name, _description in PERMISSIONS:
        PermissionAER.delete(session, permission_id)
    session.commit()

    op.drop_table(SCOPE_TABLE)
    op.drop_table(RULE_TABLE)
