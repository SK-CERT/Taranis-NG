"""Schema for presenter.

Returns:
    _type_: _description_
"""
from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.report_item import ReportItemSchema
from shared.schema.report_item_type import ReportItemTypeSchema


class PresenterSchema(Schema):
    """Presenter schema class.

    Args:
        Schema (_type_): _description_
    """

    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class PresenterInputProductSchema(Schema):
    """Schema for "presenter input product".

    A dumbed down product suitable for presenters

    Args:
        Schema (_type_): _description_

    Returns:
        _type_: _description_
    """

    title = fields.Str()
    description = fields.Str()
    product_type = fields.Str()
    product_type_description = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        """Create new instance of PresenterInputProduct."""
        return PresenterInputProduct(**data)


class PresenterInputSchema(Schema):
    """Schema for "presenter input".

    A complex package of data for presenters

    Args:
        Schema (_type_): _description_

    Returns:
        _type_: _description_
    """

    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    reports = fields.List(fields.Nested(ReportItemSchema))
    report_types = fields.List(fields.Nested(ReportItemTypeSchema))
    product = fields.Nested(PresenterInputProductSchema)

    @post_load
    def make(self, data, **kwargs):
        """Create new instance of PresenterInput."""
        return PresenterInput(**data)


class PresenterInputProduct:
    """Real data holding object presented by PresenterInputProductSchema."""

    def __init__(self, title, description, product_type, product_type_description):
        """Init for PresenterInputProduct class.

        Args:
            title (_type_): _description_
            description (_type_): _description_
            product_type (_type_): _description_
            product_type_description (_type_): _description_
        """
        self.title = title
        self.description = description
        self.product_type = product_type
        self.product_type_description = product_type_description

    @classmethod
    def make_from_product(cls, product):
        """Create new instance of PresenterInputProduct from product."""
        return PresenterInputProduct(product.title, product.description, product.product_type.title, product.product_type.description)


class PresenterInput:
    """Class for "presenter input"."""

    def __init__(self, type, product, parameter_values=None, reports=None, report_types=None):
        """Init for PresenterInput class.

        Args:
            type (_type_): _description_
            product (_type_): _description_
            parameter_values (_type_, optional): _description_. Defaults to None.
            reports (_type_, optional): _description_. Defaults to None.
            report_types (_type_, optional): _description_. Defaults to None.
        """
        # creating from JSON data
        if parameter_values is not None:
            self.load(type, product, parameter_values, reports, report_types)
            return
        # creating from OBJECTS

        # PRESENTER
        # - which presenter to use (e.g. PDF presenter)
        self.type = type
        # - arguments for the presenter (e.g. template path)
        self.parameter_values = product.product_type.parameter_values

        # REPORT ITEMS
        # - report items themselves
        self.reports = product.report_items
        # - description of the report item types used
        report_types = {}
        for report in self.reports:
            report_types[report.report_item_type.id] = report.report_item_type
        self.report_types = list(report_types.values())

        # PRODUCT
        self.product = PresenterInputProduct.make_from_product(product)

    def load(self, type, product, parameter_values, reports, report_types):
        """Load data.

        Args:
            type (_type_): _description_
            product (_type_): _description_
            parameter_values (_type_): _description_
            reports (_type_): _description_
            report_types (_type_): _description_
        """
        self.type = type
        self.parameter_values = parameter_values
        # - the same arguments, parsed differently
        self.parameter_values_map = dict()
        for parameter_value in self.parameter_values:
            self.parameter_values_map.update({parameter_value.parameter.key: parameter_value.value})
        self.reports = reports
        self.report_types = report_types
        self.product = product


class PresenterOutputSchema(Schema):
    """Schema for "presenter output".

    Args:
        Schema (_type_): _description_

    Returns:
        _type_: _description_
    """

    mime_type = fields.Str()
    data = fields.Str()
    message_body = fields.Str()
    message_title = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        """Create new instance of PresenterOutput."""
        return PresenterOutput(**data)


class PresenterOutput:
    """Class for "presenter output"."""

    def __init__(self, mime_type, data, message_body, message_title):
        """Init for PresenterOutput class.

        Args:
            mime_type (_type_): _description_
            data (_type_): _description_
            message_body (_type_): _description_
            message_title (_type_): _description_
        """
        self.mime_type = mime_type
        self.data = data
        self.message_body = message_body
        self.message_title = message_title
