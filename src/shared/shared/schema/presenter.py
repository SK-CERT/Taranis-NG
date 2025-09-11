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
        Schema (Any): Base schema class.
    """

    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))


class PresenterInputProduct:
    """Real data holding object presented by PresenterInputProductSchema."""

    def __init__(self, title: str, description: str, product_type: str, product_type_description: str, user: UserSchemaBase, id: str) -> None:  # noqa: A002
        """Initialize the "presenter input product".

        Args:
            title (str): Title of the product.
            description (str): Description of the product.
            product_type (str): Basicaly name of the product.
            product_type_description (str): Product description.
            user (UserSchemaBase): Data about the user who created the product.
            id (str): Id.
        """
        self.title = title
        self.description = description
        self.product_type = product_type
        self.product_type_description = product_type_description
        self.user = user
        self.id = id

    @classmethod
    def make_from_product(cls, product: "PresenterInputProductSchema") -> "PresenterInputProduct":
        """Make a PresenterInputProduct object from a Product object.

        Args:
            product (PresenterInputProductSchema): Product object.

        Returns:
            PresenterInputProduct: Object.
        """
        return PresenterInputProduct(
            product.title,
            product.description,
            product.product_type.title,
            product.product_type.description,
            product.user,
            product.id,
        )


class PresenterInputProductSchema(Schema):
    """Schema for "presenter input product".

    Args:
        Schema (Any): Base schema class.
    """

    title = fields.Str()
    description = fields.Str()
    product_type = fields.Str()
    product_type_description = fields.Str()
    user = fields.Nested(UserSchemaBase, exclude=("password",))
    id = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> PresenterInputProduct:  # noqa: ANN003, ARG002
        """Make a PresenterInputProduct object from JSON data.

        Args:
            data (dict): JSON data.
            **kwargs: Additional arguments.

        Returns:
            PresenterInputProduct: Object.
        """
        return PresenterInputProduct(**data)


class PresenterInput:
    """Class for "presenter input"."""

    def __init__(
        self,
        type: str,  # noqa: A002
        product: PresenterInputProductSchema,
        parameter_values: list | None = None,
        reports: list | None = None,
        report_types: list | None = None,
    ) -> None:
        """Initialize the "presenter input".

        Args:
            type (str): Which presenter to use (e.g. PDF presenter)
            product (PresenterInputProductSchema): Product consisting of report items.
            parameter_values (list, optional): Arguments for the presenter (e.g. template path). Defaults to None.
            reports (list, optional): Report items themselves. Defaults to None.
            report_types (list, optional): Description of the report item types used. Defaults to None.
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

    def load(
        self,
        type: str,  # noqa: A002
        product: PresenterInputProductSchema,
        parameter_values: list,
        reports: list,
        report_types: list,
    ) -> None:
        """Load data from JSON.

        Args:
            type (str): Type
            product (PresenterInputProductSchema): Product
            parameter_values (list): The same arguments, parsed differently.
            reports (list): Reports
            report_types (list): Report types
        """
        self.type = type
        self.parameter_values = parameter_values
        self.param_key_values = {}
        for pv in parameter_values:
            self.param_key_values.update({pv.parameter.key: pv.value})
        self.reports = reports
        self.report_types = report_types
        self.product = product


class PresenterInputSchema(Schema):
    """Schema for "presenter input".

    Args:
        Schema (Any): Base schema class.
    """

    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    reports = fields.List(fields.Nested(ReportItemSchema))
    report_types = fields.List(fields.Nested(ReportItemTypeSchema))
    product = fields.Nested(PresenterInputProductSchema)

    @post_load
    def make(self, data: dict, **kwargs) -> PresenterInput:  # noqa: ANN003, ARG002
        """Make a PresenterInput object from JSON data.

        Args:
            data (dict): JSON data.
            **kwargs: Additional arguments.

        Returns:
            PresenterInput: Object.
        """
        return PresenterInput(**data)


class PresenterOutput:
    """Class for "presenter output"."""

    def __init__(self, mime_type: str, data: str, message_body: str, message_title: str, att_file_name: str) -> None:
        """Initialize the "presenter output".

        Args:
            mime_type (str): MIME type of the output.
            data (str): The data itself.
            message_body (str): Body of the message.
            message_title (str): Title of the message.
            att_file_name (str): Attached file name.
        """
        self.mime_type = mime_type
        self.data = data
        self.message_body = message_body
        self.message_title = message_title
        self.att_file_name = att_file_name


class PresenterOutputSchema(Schema):
    """Schema for "presenter output".

    Args:
        Schema (Any): Base schema class.
    """

    mime_type = fields.Str()
    data = fields.Str()
    message_body = fields.Str()
    message_title = fields.Str()
    att_file_name = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> PresenterOutput:  # noqa: ANN003, ARG002
        """Make a PresenterOutput object from JSON data.

        Args:
            data (dict): JSON data.
            **kwargs: Additional arguments.

        Returns:
            PresenterOutput: Object.
        """
        return PresenterOutput(**data)
