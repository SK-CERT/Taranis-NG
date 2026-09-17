"""Attribute extraction rules.

Detect vulnerability identifiers in news item text during collection and store each hit as a
news item attribute. Creates the rule table and its source-group scoping table, seeds the
preconfigured patterns, adds the config permissions, and adds the global on/off switch.

Revision ID: d4f1c8a70b62
Revises: b8d3e6f5a417
Create Date: 2026-08-29 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "d4f1c8a70b62"
down_revision = "b8d3e6f5a417"
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
    ("CVE", "CVE", r"CVE-\d{4}-\d{4,}", "Common Vulnerabilities and Exposures identifier"),
    ("CWE", "CWE", r"CWE-\d+", "Common Weakness Enumeration identifier"),
    (
        "GHSA",
        "GHSA",
        r"GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}",
        "GitHub Security Advisory identifier",
    ),
    ("RHSA", "RHSA", r"RHSA-\d{4}:\d+", "Red Hat Security Advisory identifier"),
    ("EUVD", "EUVD", r"EUVD-\d{4}-\d+", "European Union Vulnerability Database identifier"),
    ("GCVE", "GCVE", r"GCVE-\d+-\d{4}-\d+", "Global CVE identifier"),
    ("CPE", "CPE", r"cpe:2\.3:[aho]:[^\s:]+:[^\s:]+(?::[^\s:]*){0,9}", "Common Platform Enumeration 2.3 name"),
    (
        "CVSS v2 vector",
        "CVSS",
        r"\bAV:[LAN]/AC:[HML]/Au:[MSN]/C:[NPC]/I:[NPC]/A:[NPC]\b",
        "CVSS v2 base vector. It carries no CVSS: prefix, so the full six-metric vector is required; Au: appears only in v2.",
    ),
    (
        "CVSS v3.x vector",
        "CVSS",
        r"CVSS:3\.[01]/AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH](?:/[A-Z]{1,2}:[A-Z]{1,2})*",
        "CVSS v3.0 and v3.1 vector, including any trailing temporal or environmental metrics",
    ),
    (
        "CVSS v4.0 vector",
        "CVSS",
        r"CVSS:4\.0/AV:[NALP]/AC:[LH]/AT:[NP]/PR:[NLH]/UI:[NPA]/VC:[HLN]/VI:[HLN]/VA:[HLN]/SC:[HLN]/SI:[HLN]/SA:[HLN]",
        "CVSS v4.0 base vector",
    ),
]

SETTING_KEY = "ATTRIBUTE_EXTRACTION_ENABLED"
SETTING_DESCRIPTION = (
    "Detect configured values in news item text during collection and store them as attributes. "
    "Collectors re-read the rules when they refresh, so switching this off takes effect at the next refresh."
)


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


class SettingAER(Base):
    """Minimal settings mapping for the global switch."""

    __tablename__ = "settings"
    id = sa.Column(sa.Integer, primary_key=True)
    key = sa.Column(sa.String(40), unique=True, nullable=False)
    type = sa.Column(sa.String(1), nullable=False)
    value = sa.Column(sa.String(), nullable=False)
    default_val = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String(), nullable=False)
    is_global = sa.Column(sa.Boolean(), nullable=False, default=True)
    options = sa.Column(sa.String())


def upgrade() -> None:
    """Create the tables, seed the rules and the switch, and add the permissions."""
    op.create_table(
        "attribute_extraction_rule",
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
    op.create_table(
        "attribute_extraction_rule_osint_source_group",
        sa.Column("attribute_extraction_rule_id", sa.Integer(), nullable=False),
        sa.Column("osint_source_group_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["attribute_extraction_rule_id"], ["attribute_extraction_rule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["osint_source_group_id"], ["osint_source_group.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("attribute_extraction_rule_id", "osint_source_group_id"),
    )

    session = Session(bind=op.get_bind())

    rules = sa.table(
        "attribute_extraction_rule",
        sa.column("name", sa.String),
        sa.column("attribute_key", sa.String),
        sa.column("pattern", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        rules,
        [
            {"name": name, "attribute_key": key, "pattern": pattern, "description": description}
            for name, key, pattern, description in SEEDED_RULES
        ],
    )

    for permission_id, name, description in PERMISSIONS:
        PermissionAER.add(session, permission_id, name, description)
    session.commit()

    role = session.query(RoleAER).filter_by(name="Admin").first()
    if role:
        role.permissions = session.query(PermissionAER).all()
        session.add(role)
        session.commit()

    if not session.query(SettingAER).filter_by(key=SETTING_KEY).first():
        session.add(
            SettingAER(
                key=SETTING_KEY,
                type="B",
                value="true",
                default_val="true",
                description=SETTING_DESCRIPTION,
                is_global=True,
            ),
        )
        session.commit()


def downgrade() -> None:
    """Drop the tables and remove the seeded switch and permissions."""
    session = Session(bind=op.get_bind())

    setting = session.query(SettingAER).filter_by(key=SETTING_KEY).first()
    if setting:
        session.delete(setting)

    for permission_id, _name, _description in PERMISSIONS:
        PermissionAER.delete(session, permission_id)
    session.commit()

    op.drop_table("attribute_extraction_rule_osint_source_group")
    op.drop_table("attribute_extraction_rule")
