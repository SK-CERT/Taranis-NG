"""Add CWE attribute

Revision ID: f0a4860000ff
Revises: dfc12c30395b
Create Date: 2024-02-08 12:53:03.830779

"""

from enum import Enum, auto
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ENUM


Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "f0a4860000ff"
down_revision = "dfc12c30395b"
branch_labels = None
depends_on = None


class AttributeTypeREVf0a4860000ff(Enum):
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    RADIO = auto()
    ENUM = auto()
    TEXT = auto()
    RICH_TEXT = auto()
    DATE = auto()
    TIME = auto()
    DATE_TIME = auto()
    LINK = auto()
    ATTACHMENT = auto()
    TLP = auto()
    CPE = auto()
    CVE = auto()
    CVSS = auto()
    CWE = auto()


class AttributeValidatorREV0a4860000ff(Enum):
    NONE = auto()
    EMAIL = auto()
    NUMBER = auto()
    RANGE = auto()
    REGEXP = auto()


class Attribute_f0a4860000ff(Base):
    __tablename__ = "attribute"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String())
    description = sa.Column(sa.String())
    type = sa.Column(sa.Enum(AttributeTypeREVf0a4860000ff))
    validator = sa.Column(sa.Enum(AttributeValidatorREV0a4860000ff))

    def __init__(self, name, description, type, validator):
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.validator = validator


class AttributeGroupItem_f0a4860000ff(Base):
    __tablename__ = "attribute_group_item"
    id = sa.Column(sa.Integer, primary_key=True, server_default=sa.text("nextval('attribute_group_item_id_seq'::regclass)"))
    title = sa.Column(sa.String)
    description = sa.Column(sa.String)
    index = sa.Column(sa.Integer)
    min_occurrence = sa.Column(sa.Integer)
    max_occurrence = sa.Column(sa.Integer)
    attribute_group_id = sa.Column(sa.ForeignKey("attribute_group.id"))
    attribute_id = sa.Column(sa.ForeignKey("attribute.id"))

    def __init__(self, title, description, index, min_occurrence, max_occurrence, attribute_group_id, attribute_id):
        self.id = None
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_group_id = attribute_group_id
        self.attribute_id = attribute_id


class AttributeGroup_f0a4860000ff(Base):
    __tablename__ = "attribute_group"
    id = sa.Column(sa.Integer, primary_key=True, server_default=sa.text("nextval('attribute_group_id_seq'::regclass)"))
    title = sa.Column(sa.String)
    description = sa.Column(sa.String)
    section = sa.Column(sa.Integer)
    section_title = sa.Column(sa.String)
    index = sa.Column(sa.Integer)
    report_item_type_id = sa.Column(sa.ForeignKey("report_item_type.id"))

    def __init__(self, title, description, section, section_title, index, report_item_type_id):
        self.id = None
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.report_item_type_id = report_item_type_id


class ReportItemType_f0a4860000ff(Base):
    __tablename__ = "report_item_type"
    id = sa.Column(sa.Integer, primary_key=True, server_default=sa.text("nextval('report_item_type_id_seq'::regclass)"))
    title = sa.Column(sa.String)
    description = sa.Column(sa.String)

    def __init__(self, title, description):
        self.id = None
        self.title = title
        self.description = description


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    new_enum = ENUM(
        "STRING",
        "NUMBER",
        "BOOLEAN",
        "RADIO",
        "ENUM",
        "TEXT",
        "RICH_TEXT",
        "DATE",
        "TIME",
        "DATE_TIME",
        "LINK",
        "ATTACHMENT",
        "TLP",
        "CPE",
        "CVE",
        "CVSS",
        "CWE",
        name="new_enum",
        create_type=False,
    )
    new_enum.create(op.get_bind(), checkfirst=False)

    with op.batch_alter_table("attribute") as batch_op:
        batch_op.alter_column(
            "type",
            type_=new_enum,
            existing_type=sa.Enum(
                "STRING",
                "NUMBER",
                "BOOLEAN",
                "RADIO",
                "ENUM",
                "TEXT",
                "RICH_TEXT",
                "DATE",
                "TIME",
                "DATE_TIME",
                "LINK",
                "ATTACHMENT",
                "TLP",
                "CPE",
                "CVE",
                "CVSS",
                name="old_enum",
            ),
            postgresql_using="type::text::new_enum",
        )

    # Drop the old Enum type if it exists
    if op.get_bind().dialect.has_type(op.get_bind(), "old_enum"):
        old_enum = sa.Enum(name="old_enum")
        old_enum.drop(op.get_bind(), checkfirst=False)

    attr = session.query(Attribute_f0a4860000ff).filter_by(name="CWE").first()
    if not attr:
        session.add(Attribute_f0a4860000ff("CWE", "Common Weakness Enumeration", AttributeTypeREVf0a4860000ff.CWE, "NONE"))
        session.commit()
        print("CWE attribute added...", flush=True)
    else:
        print("CWE attribute already exists...", flush=True)

    attr = session.query(Attribute_f0a4860000ff).filter_by(name="CWE").first()
    rit = session.query(ReportItemType_f0a4860000ff).filter_by(title="Vulnerability Report").first()
    if rit:
        ag = session.query(AttributeGroup_f0a4860000ff).filter_by(title="Vulnerability", report_item_type_id=rit.id).first()
        if ag:
            agi = session.query(AttributeGroupItem_f0a4860000ff).filter_by(title="CWE", attribute_group_id=ag.id).first()
            if not agi:
                last_group_item = (
                    session.query(AttributeGroupItem_f0a4860000ff)
                    .filter_by(attribute_group_id=ag.id)
                    .order_by(AttributeGroupItem_f0a4860000ff.index.desc())
                    .first()
                )
                session.add(AttributeGroupItem_f0a4860000ff("CWE", "", last_group_item.index + 1, 0, 1000, ag.id, attr.id))
                session.commit()
                print("Added CWE to attribute group...", flush=True)
            else:
                print("CWE already in attribute group...", flush=True)
        else:
            print("Vulnerability attribute group not found...", flush=True)
    else:
        print("Vulnerability report item type not found...", flush=True)


def downgrade():
    # can be complicated when already exists data joined with this record
    pass
