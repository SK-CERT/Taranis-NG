"""Affected systems to text area

Revision ID: dfc12c30395b
Revises: e87b34c74db0
Create Date: 2024-01-31 13:35:10.639848

"""

from alembic import op
from sqlalchemy import Column, ForeignKey, Integer, String, orm, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "dfc12c30395b"
down_revision = "e87b34c74db0"
branch_labels = None
depends_on = None


class ReportItemType_dfc12c30395b(Base):
    __tablename__ = "report_item_type"
    id = Column(Integer, primary_key=True, server_default=text("nextval('report_item_type_id_seq'::regclass)"))
    title = Column(String)


class AttributeGroup_dfc12c30395b(Base):
    __tablename__ = "attribute_group"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_group_id_seq'::regclass)"))
    title = Column(String)
    report_item_type_id = Column(ForeignKey("report_item_type.id"))


class AttributeGroupItem_dfc12c30395b(Base):
    __tablename__ = "attribute_group_item"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_group_item_id_seq'::regclass)"))
    title = Column(String)
    attribute_group_id = Column(ForeignKey("attribute_group.id"))
    attribute_id = Column(ForeignKey("attribute.id"))


class Attribute_dfc12c30395b(Base):
    __tablename__ = "attribute"
    id = Column(Integer, primary_key=True, server_default=text("nextval('attribute_id_seq'::regclass)"))
    name = Column(String, nullable=False)


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # ======= Update existing old report =======
    rit = session.query(ReportItemType_dfc12c30395b).filter_by(title="Vulnerability Report").first()
    if rit:
        ag = session.query(AttributeGroup_dfc12c30395b).filter_by(title="Identify and Act", report_item_type_id=rit.id).first()
        if ag:
            atr_text_id = session.query(Attribute_dfc12c30395b).filter_by(name="Text").first().id
            agi = (
                session.query(AttributeGroupItem_dfc12c30395b)
                .filter_by(title="Affected systems", attribute_group_id=ag.id, attribute_id=atr_text_id)
                .first()
            )
            if agi:
                atr_text_area_id = session.query(Attribute_dfc12c30395b).filter_by(name="Text Area").first().id
                agi.attribute_id = atr_text_area_id
                session.add(agi)
                session.commit()
            else:
                print("Nothing to upgrade...", flush=True)
        else:
            print("No report attribute group to upgrade...", flush=True)
    else:
        print("No report to upgrade...", flush=True)


def downgrade():
    pass
