"""Add cascade delete, Add new reports

Revision ID: 1c4eed243364
Revises: 4f24c634cd22
Create Date: 2023-08-30 08:53:19.704085

"""

from alembic import op
from datetime import datetime
from sqlalchemy import orm, Column, ForeignKey, String, Integer, DateTime, Boolean, Enum, text
from sqlalchemy.orm import declarative_base
import sqlalchemy as sa

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "1c4eed243364"
down_revision = "4f24c634cd22"
branch_labels = None
depends_on = None

# from sqlalchemy.orm import relationship
# metadata = Base.metadata


class ReportItemType_1c4eed243364(Base):
    __tablename__ = "report_item_type"
    id = Column(Integer, primary_key=True, server_default=text("nextval('report_item_type_id_seq'::regclass)"))
    title = Column(String)
    description = Column(String)

    def __init__(self, title, description):
        self.id = None
        self.title = title
        self.description = description


class ProductType_1c4eed243364(Base):
    __tablename__ = "product_type"

    id = Column(Integer, primary_key=True, server_default=text("nextval('product_type_id_seq'::regclass)"))
    title = Column(String(64), nullable=False, unique=True)
    description = Column(String, nullable=False)
    created = Column(DateTime)
    presenter_id = Column(ForeignKey("presenter.id"))

    def __init__(self, title, description, created, presenter_id):
        self.id = None
        self.title = title
        self.description = description
        self.created = created
        self.presenter_id = presenter_id


class Parameter_1c4eed243364(Base):
    __tablename__ = "parameter"

    id = Column(Integer, primary_key=True, server_default=text("nextval('parameter_id_seq'::regclass)"))
    key = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(Enum("STRING", "NUMBER", "BOOLEAN", name="parametertype"))


class ProductTypeParameterValue_1c4eed243364(Base):
    __tablename__ = "product_type_parameter_value"
    product_type_id = Column(Integer, ForeignKey("product_type.id"), primary_key=True, nullable=False)
    parameter_value_id = Column(Integer, ForeignKey("parameter_value.id"), primary_key=True, nullable=False)

    def __init__(self, product_type_id, parameter_value_id):
        self.id = None
        self.product_type_id = product_type_id
        self.parameter_value_id = parameter_value_id


class ParameterValue_1c4eed243364(Base):
    __tablename__ = "parameter_value"

    id = Column(Integer, primary_key=True, server_default=text("nextval('parameter_value_id_seq'::regclass)"))
    value = Column(String, nullable=False)
    parameter_id = Column(ForeignKey("parameter.id"))

    def __init__(self, value, parameter_id):
        self.id = None
        self.value = value
        self.parameter_id = parameter_id


class AttributeGroup_1c4eed243364(Base):
    __tablename__ = "attribute_group"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_group_id_seq'::regclass)"))
    title = Column(String)
    description = Column(String)
    section = Column(Integer)
    section_title = Column(String)
    index = Column(Integer)
    report_item_type_id = Column(ForeignKey("report_item_type.id"))

    def __init__(self, title, description, section, section_title, index, report_item_type_id):
        self.id = None
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.report_item_type_id = report_item_type_id


class AttributeGroupItem_1c4eed243364(Base):
    __tablename__ = "attribute_group_item"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_group_item_id_seq'::regclass)"))
    title = Column(String)
    description = Column(String)
    index = Column(Integer)
    min_occurrence = Column(Integer)
    max_occurrence = Column(Integer)
    attribute_group_id = Column(ForeignKey("attribute_group.id"))
    attribute_id = Column(ForeignKey("attribute.id"))

    def __init__(self, title, description, index, min_occurrence, max_occurrence, attribute_group_id, attribute_id):
        self.id = None
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_group_id = attribute_group_id
        self.attribute_id = attribute_id


class Presenter_1c4eed243364(Base):
    __tablename__ = "presenter"
    id = Column(String(64), primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(String, nullable=False)
    node_id = Column(ForeignKey("presenters_node.id"))


class Attribute_1c4eed243364(Base):
    __tablename__ = "attribute"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_id_seq'::regclass)"))
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(String)
    default_value = Column(String)
    validator = Column(String)
    validator_parameter = Column(String)

    def __init__(self, name, description, type, default_value, validator, validator_parameter):
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter


class AttributeEnum_1c4eed243364(Base):
    __tablename__ = "attribute_enum"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_enum_id_seq'::regclass)"))
    index = Column(Integer)
    value = Column(String, nullable=False)
    description = Column(String)
    imported = Column(Boolean)
    attribute_id = Column(ForeignKey("attribute.id"))

    def __init__(self, index, value, description, imported, attribute_id):
        self.id = None
        self.index = index
        self.value = value
        self.description = description
        self.imported = imported
        self.attribute_id = attribute_id


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # ======= Add cascade delete =======

    delete_previous()
    # product_type -> product_type_parameter_value
    op.create_foreign_key(
        "product_type_parameter_value_product_type_id_fkey",
        "product_type_parameter_value",
        "product_type",
        ["product_type_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # parameter -> parameter_value -> product_type_parameter_value
    op.create_foreign_key("parameter_value_parameter_id_fkey", "parameter_value", "parameter", ["parameter_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key(
        "product_type_parameter_value_parameter_value_id_fkey",
        "product_type_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # attribute -> attribute_enum
    op.create_foreign_key("attribute_enum_attribute_id_fkey", "attribute_enum", "attribute", ["attribute_id"], ["id"], ondelete="CASCADE")
    # attribute -> attribute_group_item
    op.create_foreign_key(
        "attribute_group_item_attribute_id_fkey", "attribute_group_item", "attribute", ["attribute_id"], ["id"], ondelete="CASCADE"
    )
    # report_item_type -> attribute_group -> attribute_group_item
    op.create_foreign_key(
        "attribute_group_report_item_type_id_fkey", "attribute_group", "report_item_type", ["report_item_type_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "attribute_group_item_attribute_group_id_fkey",
        "attribute_group_item",
        "attribute_group",
        ["attribute_group_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ======= Init repeating id's (1/2 - existing) =======

    atr_text_id = session.query(Attribute_1c4eed243364).filter_by(name="Text").first().id
    atr_text_area_id = session.query(Attribute_1c4eed243364).filter_by(name="Text Area").first().id
    atr_tlp_id = session.query(Attribute_1c4eed243364).filter_by(name="TLP").first().id
    atr_date_id = session.query(Attribute_1c4eed243364).filter_by(name="Date").first().id
    atr_num_id = session.query(Attribute_1c4eed243364).filter_by(name="Number").first().id
    atr_sev_id = session.query(Attribute_1c4eed243364).filter_by(name="MISP Event Threat Level").first().id

    # ======= Update existing old report =======

    rit = session.query(ReportItemType_1c4eed243364).filter_by(title="Vulnerability Report").first()
    if rit:
        ag = session.query(AttributeGroup_1c4eed243364).filter_by(title="Identify and Act", report_item_type_id=rit.id).first()
        if ag:
            agi = (
                session.query(AttributeGroupItem_1c4eed243364).filter_by(title="Affected systems CPE Codes", attribute_group_id=ag.id).first()
            )
            # check if we already run this
            if not agi:
                agi = session.query(AttributeGroupItem_1c4eed243364).filter_by(title="Affected systems", attribute_group_id=ag.id).first()
                if agi:
                    agi.title = "Affected systems CPE Codes"
                    session.add(agi)

                    session.add(AttributeGroupItem_1c4eed243364("Affected systems", "", 1, 1, 1, ag.id, atr_text_id))

                    agi = session.query(AttributeGroupItem_1c4eed243364).filter_by(title="IOC", attribute_group_id=ag.id).first()
                    if agi:
                        agi.index = 2
                        session.add(agi)
                    agi = session.query(AttributeGroupItem_1c4eed243364).filter_by(title="Recommendations", attribute_group_id=ag.id).first()
                    if agi:
                        agi.index = 3
                        session.add(agi)
                    session.commit()
                else:
                    print("No report attribute group item to upgrade...", flush=True)
            else:
                print("Old report already updated...", flush=True)
        else:
            print("No report attribute group to upgrade...", flush=True)
    else:
        print("No report to upgrade...", flush=True)

    # ======= Product Types =======

    presenter = session.query(Presenter_1c4eed243364).filter_by(type="HTML_PRESENTER").first()
    if not presenter:
        print("HTML_PRESENTER id not found!", flush=True)
        return

    parameter_html = session.query(Parameter_1c4eed243364).filter_by(key="HTML_TEMPLATE_PATH").first()
    if not parameter_html:
        print("HTML_TEMPLATE_PATH id not found!", flush=True)
        return

    # ======= ProductType, ParameterValue, ProductTypeParameterValue =======

    pt = session.query(ProductType_1c4eed243364).filter_by(title="OSINT Weekly Report").first()
    # check if we already run this
    if not pt:
        print("Adding reports to the system...", flush=True)

        data = {
            "1": {
                "title": "Weekly Bulletin",
                "desc": "Weekly bulletin",
                "path": "/app/templates/weekly.html",
            },
            "2": {
                "title": "OSINT Weekly Report",
                "desc": "OSINT weekly report",
                "path": "/app/templates/template_osint.html",
            },
            "3": {
                "title": "Disinformation",
                "desc": "Disinformation from public source report",
                "path": "/app/templates/template_disinfo.html",
            },
            "4": {
                "title": "Offensive Content",
                "desc": "Offensive content report",
                "path": "/app/templates/template_content.html",
            },
        }

        for key, value in data.items():
            new_pt = ProductType_1c4eed243364(value["title"], value["desc"], datetime.now(), presenter.id)
            session.add(new_pt)
            new_pv = ParameterValue_1c4eed243364(value["path"], parameter_html.id)
            session.add(new_pv)
            session.commit()  # to get ID
            session.add(ProductTypeParameterValue_1c4eed243364(new_pt.id, new_pv.id))
            session.commit()

        # ======= Attributes, AttributeEnum =======

        data = {
            "1": {
                "name": "NIS Sector",
                "desc": "NIS Sectors",
                "type": "ENUM",
                "def": "Public administration",
                "enum": {
                    "0": {"val": "Energy", "des": ""},
                    "1": {"val": "Energy / Oil", "des": ""},
                    "2": {"val": "Energy / Gas", "des": ""},
                    "3": {"val": "Transport", "des": ""},
                    "4": {"val": "Transport / Air", "des": ""},
                    "5": {"val": "Transport / Rail", "des": ""},
                    "6": {"val": "Transport / Water", "des": ""},
                    "7": {"val": "Transport / Road", "des": ""},
                    "8": {"val": "Banking", "des": ""},
                    "9": {"val": "Financial market infrastructures", "des": ""},
                    "10": {"val": "Health", "des": ""},
                    "11": {"val": "Drinking water supply and distribution", "des": ""},
                    "12": {"val": "Digital Infrastructure", "des": ""},
                    "13": {"val": "Digital Infrastructure / IXPs", "des": ""},
                    "14": {"val": "Digital Infrastructure / DNS service providers", "des": ""},
                    "15": {"val": "Digital Infrastructure / TLD name registers", "des": ""},
                    "16": {"val": "Public administration", "des": ""},
                    "17": {"val": "Other", "des": ""},
                    "18": {"val": "Unknown", "des": ""},
                },
            },
            "2": {
                "name": "Attachment",
                "desc": "Attached file",
                "type": "ATTACHMENT",
                "def": "",
                "enum": {},
            },
            "3": {
                "name": "Disinfo type",
                "desc": "Types of disinformation",
                "type": "ENUM",
                "def": "",
                "enum": {
                    "0": {
                        "val": "Satire or parody",
                        "des": "Presenting humorous but false stores as if they are true",
                    },
                    "1": {
                        "val": "False connection",
                        "des": "Headlines, visuals or captions don't support the content",
                    },
                    "2": {
                        "val": "Misleading content",
                        "des": "Misleading use of information to frame an issue or individual, when facts/information are misrepresented or skewed",
                    },
                    "3": {
                        "val": "False context",
                        "des": "Genuine content is shared with false contextual information, e.g. real images which have been taken out of context",
                    },
                    "4": {
                        "val": "Imposter content",
                        "des": "Genuine sources, e.g. news outlets or government agencies, are impersonated",
                    },
                    "5": {
                        "val": "Fabricated content",
                        "des": "Content is made up and 100% false; designed to deceive and do harm",
                    },
                    "6": {
                        "val": "Manipulated content",
                        "des": "Genuine information or imagery is manipulated to deceive, e.g. deepfakes or other kinds of manipulation of audio and/or visuals",
                    },
                    "7": {
                        "val": "Ukraine",
                        "des": "Disinformation about war in Ukraine",
                    },
                    "8": {
                        "val": "COVID",
                        "des": "Disinformation about COVID-19",
                    },
                    "9": {
                        "val": "Cybesecurity",
                        "des": "Disinformation about Cybesecurity",
                    },
                    "10": {
                        "val": "Electronic signature",
                        "des": "Electronic signature",
                    },
                    "11": {
                        "val": "Classified information",
                        "des": "Classified information",
                    },
                    "12": {
                        "val": "NBU",
                        "des": "NBU",
                    },
                },
            },
            "4": {
                "name": "Boolean",
                "desc": "Yes / No",
                "type": "BOOLEAN",
                "def": "False",
                "enum": {},
            },
            "5": {
                "name": "Threat level",
                "desc": "Combo box for Threat level",
                "type": "ENUM",
                "def": "",
                "enum": {
                    "0": {
                        "val": "SEVERE",
                        "des": "It is almost certain that organizations are being targeted by threat actors. High severity vulnerabilities with no known remediation are being exploited and significant damage and outages are being observed across sectors.",
                    },
                    "1": {
                        "val": "HIGH",
                        "des": "It is highly likely that entities will be directly targeted by threat actors. Multiple entities will be, or are being, affected. Sector disruption is expected to be widespread, across multiple organizations.",
                    },
                    "2": {
                        "val": "ELEVATED",
                        "des": "It is likely that entities are being directly targeted by threat actors or could be exposed to breaches using recent vulnerabilities. Sector disruption is considered a realistic possibility.",
                    },
                    "3": {
                        "val": "GUARDED",
                        "des": "There is potential for some direct targeted threat actor activity but it is generally considered Unlikely. This activity could lead to some minor disruption.",
                    },
                    "4": {
                        "val": "LOW",
                        "des": "A low likelihood of threat actor targeting activity that could affect organizations/entities. Disruption is considered highly unlikely.",
                    },
                },
            },
            "6": {
                "name": "Trend",
                "desc": "Radio box for Trend",
                "type": "RADIO",
                "def": "",
                "enum": {
                    "0": {
                        "val": "High Increase",
                        "des": "The number of incidents related to this sector/threat, shows a sustained and significant upward movement over time",
                    },
                    "1": {
                        "val": "Increase",
                        "des": "The number of incidents related to this sector/threat, shows a sustained upward movement over time, but at a slower pace than a high increase",
                    },
                    "2": {
                        "val": "Stable",
                        "des": "The number of incidents related to this sector/threat shows little to no change over time",
                    },
                    "3": {
                        "val": "Low Decrease",
                        "des": "The number of incidents related to this sector/threat, shows a sustained downward movement over time, but at a slower pace than a decrease",
                    },
                    "4": {
                        "val": "Decrease",
                        "des": "The number of incidents related to this sector/threat, shows a sustained and significant downward movement over time",
                    },
                },
            },
            "7": {
                "name": "Source Reliability",
                "desc": "Radio box for source reliability",
                "type": "RADIO",
                "def": "",
                "enum": {
                    "0": {"val": "Completely reliable", "des": ""},
                    "1": {"val": "Usually reliable", "des": ""},
                    "2": {"val": "Fairly reliable", "des": ""},
                    "3": {"val": "Not usually reliable", "des": ""},
                    "4": {"val": "Unreliable", "des": ""},
                    "5": {"val": "Reliability cannot be judged", "des": ""},
                },
            },
            "8": {
                "name": "Information Credibility",
                "desc": "Radio box for information credibility",
                "type": "RADIO",
                "def": "",
                "enum": {
                    "0": {"val": "Confirmed by other sources", "des": ""},
                    "1": {"val": "Probably True", "des": ""},
                    "2": {"val": "Possibly True", "des": ""},
                    "3": {"val": "Doubtful", "des": ""},
                    "4": {"val": "Improbable", "des": ""},
                    "5": {"val": "Truth cannot be judged", "des": ""},
                },
            },
        }

        for key, value in data.items():
            new_atr = Attribute_1c4eed243364(value["name"], value["desc"], value["type"], value["def"], "NONE", "")
            session.add(new_atr)
            session.commit()
            for key2, value2 in value["enum"].items():
                session.add(AttributeEnum_1c4eed243364(key2, value2["val"], value2["des"], False, new_atr.id))
                session.commit()

        # ======= Init repeating id's (2/2 - add new) =======

        atr_nis_id = session.query(Attribute_1c4eed243364).filter_by(name="NIS Sector").first().id
        atr_att_id = session.query(Attribute_1c4eed243364).filter_by(name="Attachment").first().id
        atr_dis_id = session.query(Attribute_1c4eed243364).filter_by(name="Disinfo type").first().id
        atr_bool_id = session.query(Attribute_1c4eed243364).filter_by(name="Boolean").first().id
        atr_threat_id = session.query(Attribute_1c4eed243364).filter_by(name="Threat level").first().id
        atr_trend_id = session.query(Attribute_1c4eed243364).filter_by(name="Trend").first().id
        atr_src_id = session.query(Attribute_1c4eed243364).filter_by(name="Source Reliability").first().id
        atr_inf_id = session.query(Attribute_1c4eed243364).filter_by(name="Information Credibility").first().id

        # ======= ReportItemType, AttributeGroup, AttributeGroupItem =======

        data = {
            "1": {
                "tit": "OSINT Report - Summary",
                "desc": "Summary for OSINT Report",
                "ag": {
                    "0": {
                        "tit": "Summary for OSINT Report",
                        "des": "Summary for OSINT Report",
                        "agi": {
                            "0": {
                                "tit": "Title",
                                "des": "Report title",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "1": {
                                "tit": "Summary",
                                "des": "Report summary",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "2": {
                                "tit": "Sector trends",
                                "des": "New development in Sectors",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "3": {
                                "tit": "Vulnerabilities trends",
                                "des": "New development of vulnerabilities",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "4": {
                                "tit": "Ransomware trends",
                                "des": "New development of Ransomware",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "5": {
                                "tit": "Date published",
                                "des": "Date displayed on report",
                                "min": 1,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                            "6": {
                                "tit": "Threat level",
                                "des": "Report threat level",
                                "min": 1,
                                "max": 1,
                                "aid": atr_threat_id,
                            },
                            "7": {
                                "tit": "TLP",
                                "des": "Report TLP",
                                "min": 1,
                                "max": 1,
                                "aid": atr_tlp_id,
                            },
                        },
                    },
                },
            },
            "2": {
                "tit": "OSINT Report - Ransomware",
                "desc": "Ransomware part for OSINT Report",
                "ag": {
                    "0": {
                        "tit": "OSINT Report - Ransomware",
                        "des": "OSINT Report - Ransomware",
                        "agi": {
                            "0": {
                                "tit": "Ransomware",
                                "des": "Ransomware",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "1": {
                                "tit": "Actor",
                                "des": "Actor",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "2": {
                                "tit": "Sector",
                                "des": "Sector",
                                "min": 1,
                                "max": 1,
                                "aid": atr_nis_id,
                            },
                            "3": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "4": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                        },
                    },
                },
            },
            "3": {
                "tit": "OSINT Report - Sectors",
                "desc": "Sectors part for OSINT Report",
                "ag": {
                    "0": {
                        "tit": "Energy",
                        "des": "Energy",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "1": {
                        "tit": "Transport",
                        "des": "Transport",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "2": {
                        "tit": "Banking",
                        "des": "Banking",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "3": {
                        "tit": "Financial market infrastructures",
                        "des": "Financial market infrastructures",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "4": {
                        "tit": "Health",
                        "des": "Health",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "5": {
                        "tit": "Drinking water",
                        "des": "Drinking water",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "6": {
                        "tit": "Waste water",
                        "des": "Waste water",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "7": {
                        "tit": "Digital infrastructure",
                        "des": "Digital infrastructure",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "8": {
                        "tit": "ICT service management",
                        "des": "ICT service management",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "9": {
                        "tit": "Public administration",
                        "des": "Public administration",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "10": {
                        "tit": "Space",
                        "des": "Space",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                },
            },
            "4": {
                "tit": "OSINT Report - Threats",
                "desc": "Threats part for OSINT Report",
                "ag": {
                    "0": {
                        "tit": "Ransomware",
                        "des": "Ransomware",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "1": {
                        "tit": "Data Breach",
                        "des": "Data Breach",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "2": {
                        "tit": "DoS/DDoS",
                        "des": "DoS/DDoS",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "3": {
                        "tit": "Destruction",
                        "des": "Destruction",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                    "4": {
                        "tit": "APT",
                        "des": "APT",
                        "agi": {
                            "0": {
                                "tit": "Comment",
                                "des": "Comment",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Incidents",
                                "des": "Incidents",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "2": {
                                "tit": "Trend",
                                "des": "Trend",
                                "min": 1,
                                "max": 1,
                                "aid": atr_trend_id,
                            },
                        },
                    },
                },
            },
            "5": {
                "tit": "OSINT Report - Cyber Event",
                "desc": "Cyber event part for OSINT Report",
                "ag": {
                    "0": {
                        "tit": "Cyber Event Report",
                        "des": "",
                        "agi": {
                            "0": {
                                "tit": "Description",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "1": {
                                "tit": "Date",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                            "2": {
                                "tit": "Sector",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_nis_id,
                            },
                            "3": {
                                "tit": "Threat actor",
                                "des": "",
                                "min": 0,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "4": {
                                "tit": "Threat type",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "5": {
                                "tit": "Severity",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_sev_id,
                            },
                            "6": {
                                "tit": "Source Reliability",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_src_id,
                            },
                            "7": {
                                "tit": "Information Credibility",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_inf_id,
                            },
                            "8": {
                                "tit": "Links",
                                "des": "",
                                "min": 1,
                                "max": 100,
                                "aid": atr_text_id,
                            },
                            "9": {
                                "tit": "Recommendations",
                                "des": "",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                        },
                    },
                },
            },
            "6": {
                "tit": "Disinformation from public source",
                "desc": "Disinformation report type",
                "ag": {
                    "0": {
                        "tit": "Source",
                        "des": "This section of the analytic document contains objective data obtained from external sources. The purpose of this section is to provide a comprehensive and reliable source of information that can be used to support the analysis and evaluation in the second part of the report. It is important to ensure that the data included in this section is accurate, relevant, and up-to-date.",
                        "agi": {
                            "0": {
                                "tit": "Source (link)",
                                "des": "Link to the source of disinformation",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "1": {
                                "tit": "Title",
                                "des": "Disinformation title",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "2": {
                                "tit": "Quote",
                                "des": "A copy of selected passage of text from webpage",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "3": {
                                "tit": "Reach",
                                "des": "Number of exposed people",
                                "min": 1,
                                "max": 1,
                                "aid": atr_num_id,
                            },
                            "4": {
                                "tit": "Reach to date",
                                "des": "Reach to date",
                                "min": 1,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                            "5": {
                                "tit": "Proof",
                                "des": "Screenshots, files ...",
                                "min": 0,
                                "max": 99,
                                "aid": atr_att_id,
                            },
                        },
                    },
                    "1": {
                        "tit": "Analysis",
                        "des": "This section should be based on logical reasoning and supported by the data presented in the source section. The purpose of this section is to provide an interpretation and evaluation of the data and to draw conclusions based on the analysis. It is important to ensure that the analysis is objective, unbiased, and grounded in the data presented in the source section.",
                        "agi": {
                            "0": {
                                "tit": "Category",
                                "des": "Category of disinformation",
                                "min": 1,
                                "max": 1,
                                "aid": atr_dis_id,
                            },
                            "1": {
                                "tit": "Interpretation/evaluation",
                                "des": "Disinformation interpretation/evaluation",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "2": {
                                "tit": "Recommendation",
                                "des": "Recommendation actions",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                        },
                    },
                },
            },
            "7": {
                "tit": "Offensive content",
                "desc": "Offensive content report type",
                "ag": {
                    "0": {
                        "tit": "Offensive content",
                        "des": "Offensive content",
                        "agi": {
                            "0": {
                                "tit": "Who proposes blocking",
                                "des": "From whom the proposal for blocking came",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "1": {
                                "tit": "Summary",
                                "des": "Summary of the proposal",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "2": {
                                "tit": "Opinion",
                                "des": "Opinion of the NBU",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "3": {
                                "tit": "Blocking methods",
                                "des": "List of technical methods of blocking",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                            "4": {
                                "tit": "Block from",
                                "des": "Start date of blocking",
                                "min": 1,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                            "5": {
                                "tit": "Block to",
                                "des": "End date of blocking",
                                "min": 0,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                            "6": {
                                "tit": "The Court decided",
                                "des": "The Court decided",
                                "min": 1,
                                "max": 1,
                                "aid": atr_bool_id,
                            },
                            "7": {
                                "tit": "The date when court decided",
                                "des": "The date when court decided",
                                "min": 0,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                        },
                    },
                },
            },
            "8": {
                "tit": "News by Sector",
                "desc": "News item relevant for sector",
                "ag": {
                    "0": {
                        "tit": "Audience and Date",
                        "des": "Audience and Date",
                        "agi": {
                            "0": {
                                "tit": "NIS Sector",
                                "des": "Sector, for which this news piece is relevant",
                                "min": 1,
                                "max": 1,
                                "aid": atr_nis_id,
                            },
                            "1": {
                                "tit": "Date",
                                "des": "Date when this news piece was first published",
                                "min": 1,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                            "2": {
                                "tit": "Date updated",
                                "des": "Date when this news piece was last updated",
                                "min": 0,
                                "max": 1,
                                "aid": atr_date_id,
                            },
                        },
                    },
                    "1": {
                        "tit": "News Item",
                        "des": "News Item",
                        "agi": {
                            "0": {
                                "tit": "Headline",
                                "des": "Short title of the news piece",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_id,
                            },
                            "1": {
                                "tit": "Article",
                                "des": "Contents of the news article",
                                "min": 1,
                                "max": 1,
                                "aid": atr_text_area_id,
                            },
                        },
                    },
                },
            },
        }
        for key, value in data.items():
            rit = ReportItemType_1c4eed243364(value["tit"], value["desc"])
            session.add(rit)
            session.commit()
            for key2, value2 in value["ag"].items():
                ag = AttributeGroup_1c4eed243364(value2["tit"], value2["des"], -1, "", key2, rit.id)
                session.add(ag)
                session.commit()
                for key3, value3 in value2["agi"].items():
                    session.add(
                        AttributeGroupItem_1c4eed243364(
                            value3["tit"],
                            value3["des"],
                            key3,
                            value3["min"],
                            value3["max"],
                            ag.id,
                            value3["aid"],
                        )
                    )
                    session.commit()
    else:
        print("Reports already exist in the system...", flush=True)


def downgrade():
    delete_previous()
    # product_type -> product_type_parameter_value
    op.create_foreign_key(
        "product_type_parameter_value_product_type_id_fkey", "product_type_parameter_value", "product_type", ["product_type_id"], ["id"]
    )
    # parameter -> parameter_value -> product_type_parameter_value
    op.create_foreign_key("parameter_value_parameter_id_fkey", "parameter_value", "parameter", ["parameter_id"], ["id"])
    op.create_foreign_key(
        "product_type_parameter_value_parameter_value_id_fkey",
        "product_type_parameter_value",
        "parameter_value",
        ["parameter_value_id"],
        ["id"],
    )
    # attribute -> attribute_enum
    op.create_foreign_key("attribute_enum_attribute_id_fkey", "attribute_enum", "attribute", ["attribute_id"], ["id"])
    # attribute -> attribute_group_item
    op.create_foreign_key("attribute_group_item_attribute_id_fkey", "attribute_group_item", "attribute", ["attribute_id"], ["id"])
    # report_item_type -> attribute_group -> attribute_group_item
    op.create_foreign_key("attribute_group_report_item_type_id_fkey", "attribute_group", "report_item_type", ["report_item_type_id"], ["id"])
    op.create_foreign_key(
        "attribute_group_item_attribute_group_id_fkey", "attribute_group_item", "attribute_group", ["attribute_group_id"], ["id"]
    )

    # other things can be complicated when already exists data joined with these records
    pass


def delete_previous():
    print("Deleting previous constraints...", flush=True)
    op.drop_constraint("product_type_parameter_value_product_type_id_fkey", "product_type_parameter_value", type_="foreignkey")
    op.drop_constraint("parameter_value_parameter_id_fkey", "parameter_value", type_="foreignkey")
    op.drop_constraint("product_type_parameter_value_parameter_value_id_fkey", "product_type_parameter_value", type_="foreignkey")
    op.drop_constraint("attribute_enum_attribute_id_fkey", "attribute_enum", type_="foreignkey")
    op.drop_constraint("attribute_group_item_attribute_id_fkey", "attribute_group_item", type_="foreignkey")
    op.drop_constraint("attribute_group_report_item_type_id_fkey", "attribute_group", type_="foreignkey")
    op.drop_constraint("attribute_group_item_attribute_group_id_fkey", "attribute_group_item", type_="foreignkey")
    print("Adding new constraints...", flush=True)
