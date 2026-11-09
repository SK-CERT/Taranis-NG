"""Presenter model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from managers.db_manager import db
from marshmallow import fields, post_load
from model.parameter import NewParameterSchema
from shared.schema.presenter import PresenterSchema

if TYPE_CHECKING:
    from model.parameter import Parameter


class NewPresenterSchema(PresenterSchema):
    """New presenter schema.

    Attributes:
        parameters: List of parameters
    """

    parameters = fields.List(fields.Nested(NewParameterSchema))

    @post_load
    def make(self, data: dict, **kwargs) -> Presenter:  # noqa: ARG002, ANN003
        """Create a new presenter.

        Args:
            data: Presenter data
            **kwargs: Additional arguments.

        Returns:
            Presenter: New presenter
        """
        return Presenter(**data)


class Presenter(db.Model):
    """Presenter model: one presenter of a presenters node.

    Attributes:
        id: Presenter GUID
        name: Presenter name
        description: Presenter description
        type: Presenter type
        parameters: List of parameters
        node_id: Presenters node GUID
        node: Presenters node
        product_formats: The product formats rendered by this presenter
    """

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    type = db.Column(db.String(), nullable=False)

    parameters = db.relationship("Parameter", secondary="presenter_parameter")

    node_id = db.Column(db.String, db.ForeignKey("presenters_node.id"))
    node = db.relationship("PresentersNode", back_populates="presenters")

    product_formats = db.relationship("ProductFormat", back_populates="presenter")

    def __init__(self, name: str, description: str, type: str, parameters: list[Parameter]) -> None:  # noqa: A002
        """Initialize presenter."""
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = parameters

    @classmethod
    def create_all(cls, presenters_data: list[dict]) -> list[Presenter]:
        """Create presenters from their data.

        Args:
            presenters_data: Presenters data

        Returns:
            List[Presenter]: New presenters
        """
        new_presenter_schema = NewPresenterSchema(many=True)
        return new_presenter_schema.load(presenters_data)


class PresenterParameter(db.Model):
    """Presenter parameter model.

    Attributes:
        presenter_id: Presenter GUID
        parameter_id: Parameter id
    """

    presenter_id = db.Column(db.String, db.ForeignKey("presenter.id"), primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey("parameter.id"), primary_key=True)
