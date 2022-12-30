from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.report_item import ReportItemSchema
from shared.schema.report_item_type import ReportItemTypeSchema


class PresenterSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))

# schema for "presenter input product" - a dumbed down product suitable for presenters
class PresenterInputProductSchema(Schema):
    title = fields.Str()
    description = fields.Str()
    product_type = fields.Str()
    product_type_description = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return PresenterInputProduct(**data)

# schema for "presenter input" - a complex package of data for presenters
class PresenterInputSchema(Schema):
    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    reports = fields.List(fields.Nested(ReportItemSchema))
    report_types = fields.List(fields.Nested(ReportItemTypeSchema))
    product = fields.Nested(PresenterInputProductSchema)

    @post_load
    def make(self, data, **kwargs):
        return PresenterInput(**data)

# real data holding object presented by PresenterInputProductSchema
class PresenterInputProduct:
    def __init__(self, title, description, product_type, product_type_description):
        self.title = title
        self.description = description
        self.product_type = product_type
        self.product_type_description = product_type_description

    @classmethod
    def make_from_product(cls, product):
        return PresenterInputProduct(
            product.title,
            product.description,
            product.product_type.title,
            product.product_type.description
        )

class PresenterInput:
    def __init__(self, type, product, parameter_values = None, reports = None, report_types = None):
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
    mime_type = fields.Str()
    data = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return PresenterOutput(**data)


class PresenterOutput:
    def __init__(self, mime_type, data):
        self.mime_type = mime_type
        self.data = data
