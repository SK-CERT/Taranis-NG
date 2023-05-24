from shared.schema.presenter import PresenterSchema
from managers import log_manager
import json
import datetime
import types
import re


class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    parameters = []

    # helper class
    @staticmethod
    def json_default(value):
        if isinstance(value, datetime.date):
            return dict(year=value.year, month=value.month, day=value.day)
        elif isinstance(value, types.MappingProxyType):
            return dict(value)
        else:
            return value.__dict__

    # helper class
    class AttributesObject:
        def toJSON(self):
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

    # helper class
    class ReportItemObject:
        def toJSON(self):
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

        def __init__(self, report_item, report_types, attribute_map):
            # report item itself
            self.name = report_item.title
            self.name_prefix = report_item.title_prefix
            self.uuid = report_item.uuid
            self.created = report_item.created
            self.last_updated = report_item.last_updated

            # info about the report type
            type_id = report_item.report_item_type_id
            report_type = report_types[type_id]

            self.type = report_type.title
            self.type_description = report_type.description
            # self.type_attribute_groups = report_type.attribute_groups

            # embedded news items
            self.news_items = list()
            for news_item_aggregate in report_item.news_item_aggregates:
                for news_item in news_item_aggregate['news_items']:
                    self.news_items.append(news_item['news_item_data'])

            self.attrs = BasePresenter.AttributesObject()

            for attribute in report_item.attributes:
                if attribute.value is not None:
                    attr_type = attribute_map[attribute.attribute_group_item_id]
                    attr_key = attr_type.title.lower().replace(" ", "_")
                    if hasattr(self.attrs, attr_key):
                        if attribute_map[attribute.attribute_group_item_id].max_occurrence > 1:
                            attr = getattr(self.attrs, attr_key)
                            attr.append(attribute.value)
                    else:
                        if attribute_map[attribute.attribute_group_item_id].max_occurrence == 1:
                            setattr(self.attrs, attr_key, attribute.value)
                        else:
                            setattr(self.attrs, attr_key, [attribute.value])

    # object holding all that we received from the CORE
    class InputDataObject:
        def toJSON(self):
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

        def get_max_tlp(self, reports):
            """Returns the highest TLP value from a list of reports

            Args:
                reports (list): list of reports

            Returns:
                max_tlp: Highest TLP value from the list of reports
            """
            color_values = {
                            'WHITE': 0,
                            'CLEAR': 1,
                            'GREEN': 2,
                            'AMBER': 3,
                            'AMBER+STRICT': 4,
                            'RED': 5
                            }
            colors = []

            for report in reports:
                colors.append(report.attrs.tlp)

            max_tlp = max(colors, key=lambda color: color_values.get(color, 0))
            if not max_tlp:
                max_tlp = "CLEAR"
            return max_tlp

        def add_link_prefix(self, report, letter):
            pattern = r'\[(\d+)\]'
            description = re.sub(pattern, lambda match: f"[{letter}{match.group(1)}]", report.attrs.description)
            recommendations = re.sub(pattern, lambda match: f"[{letter}{match.group(1)}]", report.attrs.recommendations)
            log_manager.log_info(description)

            return description, recommendations

        def __init__(self, presenter_input):
            # types of report items (e.g. vuln report, disinfo report)
            report_types = dict()
            for report_type in presenter_input.report_types:
                # index by ID
                report_types[report_type.id] = report_type

            # attributes that can be used in report items (for internal use)
            attribute_map = dict()
            for report_type in presenter_input.report_types:
                for attribute_group in report_type.attribute_groups:
                    for attribute_group_item in attribute_group.attribute_group_items:
                        attribute_map[attribute_group_item.id] = attribute_group_item

            self.product = presenter_input.product
            self.report_items = list()

            for report in presenter_input.reports:
                self.report_items.append(BasePresenter.ReportItemObject(report, report_types, attribute_map))

            letter = 'A'
            for report in self.report_items:
                report.attrs.description, report.attrs.recommendations = self.add_link_prefix(report, letter)
                report.attrs.link_prefix = letter
                letter = chr(ord(letter) + 1)

            self.product.max_tlp = self.get_max_tlp(self.report_items)

    def get_info(self):
        info_schema = PresenterSchema()
        return info_schema.dump(self)

    def print_exception(self, error):
        log_manager.log_debug_trace("[{0}] {1}".format(self.name, error))

    @staticmethod
    def generate_input_data(presenter_input):
        data = BasePresenter.InputDataObject(presenter_input)
        data_json = data.toJSON()
        log_manager.log_info("=== TEMPLATING FROM THE FOLLOWING INPUT ===\n" + data_json)
        data_obj = json.loads(data_json)
        return data_obj

    def generate(self, presenter_input):
        pass
