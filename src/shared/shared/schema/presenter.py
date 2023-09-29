"""Schema for presenters.

Returns:
    _type_: _description_
"""
from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.report_item import ReportItemSchema
from shared.schema.report_item_type import ReportItemTypeSchema
from shared.schema.user import UserSchemaBase


class PresenterSchema(Schema):
    """Schema for presenter.

    Args:
        Schema (_type_): Base schema class.
    """

    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class PresenterInputProductSchema(Schema):
    """Schema for "presenter input product".

    A dumbed down product suitable for presenters.

    Args:
        Schema (_type_): Base schema class.

    Returns:
        _type_: _description_
    """

    title = fields.Str()
    description = fields.Str()
    product_type = fields.Str()
    product_type_description = fields.Str()
    user = fields.Nested(UserSchemaBase, exclude=("password",))

    @post_load
    def make(self, data, **kwargs):
        """Make a PresenterInputProduct object from JSON data.

        Args:
            data (_type_): JSON data.

        Returns:
            _type_: PresenterInputProduct object.
        """
        return PresenterInputProduct(**data)


class PresenterInputSchema(Schema):
    """Schema for "presenter input".

    A complex package of data for presenters.

    Args:
        Schema (_type_): Base schema class.

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
        """Make a PresenterInput object from JSON data.

        Args:
            data (_type_): JSON data.

        Returns:
            _type_: PresenterInput object.
        """
        return PresenterInput(**data)


class PresenterInputProduct:
    """Real data holding object presented by PresenterInputProductSchema."""

    def __init__(self, title, description, product_type, product_type_description, user):
        """Initialize the "presenter input product".

        Args:
            title (_type_): Title of the product.
            description (_type_): Description of the product.
            product_type (_type_): Basicaly name of the product.
            product_type_description (_type_): Product description.
            user (_type_): Data about the user who created the product.
        """
        self.title = title
        self.description = description
        self.product_type = product_type
        self.product_type_description = product_type_description
        self.user = user

    @classmethod
    def make_from_product(cls, product):
        """Make a PresenterInputProduct object from a Product object.

        Args:
            product (_type_): Product object.

        Returns:
            _type_: PresenterInputProduct object.
        """
        return PresenterInputProduct(
            product.title, product.description, product.product_type.title, product.product_type.description, product.user
        )


class PresenterInput:
    """Class for "presenter input"."""

    def __init__(self, type, product, parameter_values=None, reports=None, report_types=None):
        """Initialize the "presenter input".

        Args:
            type (_type_): Which presenter to use (e.g. PDF presenter)
            product (_type_): Product consisting of report items.
            parameter_values (_type_, optional): Arguments for the presenter (e.g. template path). Defaults to None.
            reports (_type_, optional): Report items themselves. Defaults to None.
            report_types (_type_, optional): Description of the report item types used. Defaults to None.
        """
        # Creating from JSON data.
        if parameter_values is not None:
            self.load(type, product, parameter_values, reports, report_types)
            return
        # Creating from OBJECTS
        self.type = type
        self.parameter_values = product.product_type.parameter_values
        self.reports = product.report_items
        report_types = {}
        for report in self.reports:
            report_types[report.report_item_type.id] = report.report_item_type
        self.report_types = list(report_types.values())
        self.product = PresenterInputProduct.make_from_product(product)

    def load(self, type, product, parameter_values, reports, report_types):
        """Load data from JSON.

        Args:
            type (_type_): _description_
            product (_type_): _description_
            parameter_values (_type_): The same arguments, parsed differently.
            reports (_type_): _description_
            report_types (_type_): _description_
        """
        self.type = type
        self.parameter_values = parameter_values
        self.parameter_values_map = dict()
        for parameter_value in self.parameter_values:
            self.parameter_values_map.update({parameter_value.parameter.key: parameter_value.value})
        self.reports = reports
        self.report_types = report_types
        self.product = product


class PresenterOutputSchema(Schema):
    """Schema for "presenter output".

    Args:
        Schema (_type_): Base schema class.

    Returns:
        _type_: _description_
    """

    mime_type = fields.Str()
    data = fields.Str()
    message_body = fields.Str()
    message_title = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        """Make a PresenterOutput object from JSON data.

        Args:
            data (_type_): JSON data.

        Returns:
            _type_: PresenterOutput object.
        """
        return PresenterOutput(**data)


class PresenterOutput:
    """Class for "presenter output"."""

    def __init__(self, mime_type, data, message_body, message_title):
        """Initialize the "presenter output".

        Args:
            mime_type (_type_): MIME type of the output.
            data (_type_): The data itself.
            message_body (_type_): Body of the message.
            message_title (_type_): Title of the message.
        """
        self.mime_type = mime_type
        self.data = data
        self.message_body = message_body
        self.message_title = message_title
