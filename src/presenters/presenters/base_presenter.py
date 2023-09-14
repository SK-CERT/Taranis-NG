from shared.schema.presenter import PresenterSchema
from managers import log_manager
import json, datetime, types

class BasePresenter:
    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    parameters = list()

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

            # group the values ; identify attributes with the same names
            attribute_group_items = dict()
            attribute_group_items_by_name = dict()
            
            # print (dir(report_item), flush=True)

            for attribute in report_item.attributes:
                attribute_group_item_id = attribute.attribute_group_item_id
                if attribute_group_item_id not in attribute_group_items:
                    attribute_group_items[attribute_group_item_id] = list()
                attribute_group_items[attribute_group_item_id].append(attribute)  ######

                attr_type = attribute_map[attribute_group_item_id]
                attr_key = attr_type.title.lower().replace(" ", "_")
                if attr_key not in attribute_group_items_by_name:
                    attribute_group_items_by_name[attr_key] = 1
                else:
                    attribute_group_items_by_name[attr_key] += 1
                # print(">>>", attr_key + ":", attribute.value, flush=True)

            for attribute_group_item_id in attribute_group_items.keys():
                attr_type = attribute_map[attribute_group_item_id]
                attr_key = attr_type.title.lower().replace(" ", "_")

                attribute_group_item = attribute_group_items[attribute_group_item_id]
                # print("=>>", attribute_group_item, flush=True)

                min_occurrence = attribute_map[attribute_group_item_id].min_occurrence
                max_occurrence = attribute_map[attribute_group_item_id].max_occurrence

                value_to_add = None
                if max_occurrence == 1:
                    if len(attribute_group_item) > 0:
                        value_to_add = attribute_group_item[0].value
                else:
                    value_to_add = list()
                    for attribute in attribute_group_item:
                        value_to_add.append(attribute.value)

                how_many_with_the_same_name = attribute_group_items_by_name[attr_key]
                # print("===", attr_key + ":", value_to_add, how_many_with_the_same_name, flush=True)
                if how_many_with_the_same_name == 1:
                    setattr(self.attrs, attr_key, value_to_add)
                else:
                    if not hasattr(self.attrs, attr_key):
                        setattr(self.attrs, attr_key, list())
                    getattr(self.attrs, attr_key).append(value_to_add)

    # object holding all that we received from the CORE
    class InputDataObject:
        def toJSON(self):
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

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

    # used in JINJA templating for formating "string date" to "date"
    def _filter_datetime(date, fmtin=None, fmtout=None):
        if date == "":
            return ""
        if not fmtin:
            fmtin = "%Y.%m.%d"
        date = datetime.datetime.strptime(date, fmtin)
        native = date.replace(tzinfo=None)
        if not fmtout:
            fmtout = "%-d.%-m.%Y"
        return native.strftime(fmtout)