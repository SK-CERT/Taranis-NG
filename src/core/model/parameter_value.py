"""The value a record (source, bot preset, product format, publishing channel) gives a module parameter."""

from __future__ import annotations

from typing import Any

from managers.db_manager import db
from marshmallow import fields, post_load
from shared.schema.parameter_value import ParameterValueSchema


class NewParameterValueSchema(ParameterValueSchema):
    """A parameter value as a dialog submits it.

    A stored secret is never sent to the GUI, so saving it empty keeps it; ``clear_stored`` is
    the dialog asking to remove it (see ``managers.stored_secrets.keep_secret_parameter``).
    """

    clear_stored = fields.Bool(load_default=False, load_only=True)

    @post_load
    def make_parameter_value(self, data: dict, **_kwargs: Any) -> ParameterValue:  # noqa: ANN401 - marshmallow's hook signature
        """Build the (unsaved) parameter value, carrying the remove request alongside it."""
        clear_stored = data.pop("clear_stored", False)
        parameter_value = ParameterValue(**data)
        parameter_value.clear_stored = clear_stored
        return parameter_value


class ParameterValue(db.Model):
    """The value of one module parameter."""

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)

    parameter_id = db.Column(db.Integer, db.ForeignKey("parameter.id"))
    parameter = db.relationship("Parameter")

    def __init__(self, value: str, parameter: Any) -> None:  # noqa: ANN401 - a Parameter row or its schema object
        """Create a value for a parameter."""
        self.id = None
        self.value = value
        self.parameter_id = parameter.id
