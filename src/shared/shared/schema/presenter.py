from marshmallow import Schema, fields, post_load

from shared.schema.parameter import ParameterSchema
from shared.schema.parameter_value import ParameterValueSchema
from shared.schema.report_item import ReportItemSchema
from shared.schema.report_item_type import ReportItemTypeSchema
from shared.schema.product import ProductSchemaBase


class PresenterSchema(Schema):
    id = fields.Str()
    type = fields.Str()
    name = fields.Str()
    description = fields.Str()
    parameters = fields.List(fields.Nested(ParameterSchema))

class PresenterInputSchema(Schema):
    type = fields.Str()
    parameter_values = fields.List(fields.Nested(ParameterValueSchema))
    reports = fields.List(fields.Nested(ReportItemSchema))
    report_types = fields.List(fields.Nested(ReportItemTypeSchema))
    product = fields.Nested(ProductSchemaBase)

    @post_load
    def make(self, data, **kwargs):
        return PresenterInput(**data)


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
        self.product = product

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
