"""Correct old presenter template details

Revision ID: d776f47ce040
Revises: 1c4eed243364
Create Date: 2023-11-24 12:58:32.377642

"""

from alembic import op
from sqlalchemy import Column, ForeignKey, Integer, String, orm, text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "d776f47ce040"
down_revision = "1c4eed243364"
branch_labels = None
depends_on = None


class Presenter_d776f47ce040(Base):
    __tablename__ = "presenter"
    id = Column(String(64), primary_key=True)
    type = Column(String, nullable=False)


class PresenterParameter_d776f47ce040(Base):
    __tablename__ = "presenter_parameter"
    presenter_id = Column(String(64), ForeignKey("presenter.id"), primary_key=True, nullable=False)
    parameter_id = Column(Integer, ForeignKey("parameter.id"), primary_key=True, nullable=False)


class Parameter_d776f47ce040(Base):
    __tablename__ = "parameter"
    id = Column(Integer, primary_key=True, server_default=text("nextval('parameter_id_seq'::regclass)"))
    key = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)


class ParameterValue_d776f47ce040(Base):
    __tablename__ = "parameter_value"
    id = Column(Integer, primary_key=True, server_default=text("nextval('parameter_value_id_seq'::regclass)"))
    value = Column(String, nullable=False)
    parameter_id = Column(ForeignKey("parameter.id"))


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # add cascade delete
    delete_previous()
    # parameter -> presenter_parameter
    op.create_foreign_key(
        "presenter_parameter_parameter_id_fkey",
        "presenter_parameter",
        "parameter",
        ["parameter_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Correct old presenter template details
    presenters = session.query(Presenter_d776f47ce040).filter_by(type="PDF_PRESENTER").all()
    for pres in presenters:
        presenterParameters = session.query(PresenterParameter_d776f47ce040).filter_by(presenter_id=pres.id).all()
        for presParam in presenterParameters:
            parameters = session.query(Parameter_d776f47ce040).filter_by(id=presParam.parameter_id).all()
            for param in parameters:
                if param.key == "HEADER_TEMPLATE_PATH" or param.key == "FOOTER_TEMPLATE_PATH":
                    session.delete(param)
                    print(f"Old parameter deleted... ({param.key})", flush=True)
                elif param.key == "BODY_TEMPLATE_PATH":
                    param.key = "PDF_TEMPLATE_PATH"
                    param.name = "PDF template with its path"
                    param.description = "Path of pdf template file"
                    session.add(param)
                    val = session.query(ParameterValue_d776f47ce040).filter_by(parameter_id=param.id).first()
                    if val:
                        val.value = val.value.replace("pdf_body_template.html", "pdf_template.html")
                        session.add(val)
                        print(f"Old parameter updated... ({param.key})", flush=True)
                session.commit()


def downgrade():
    delete_previous()
    # parameter -> presenter_parameter
    op.create_foreign_key("presenter_parameter_parameter_id_fkey", "presenter_parameter", "parameter", ["parameter_id"], ["id"])


def delete_previous():
    print("Deleting previous constraints...", flush=True)
    op.drop_constraint("presenter_parameter_parameter_id_fkey", "presenter_parameter", type_="foreignkey")
    print("Adding new constraints...", flush=True)
