"""Base presenter.

Returns:
    _description_
"""

from shared.schema.presenter import PresenterSchema
from managers.log_manager import logger
import json
import datetime
import types
import re


class BasePresenter:
    """Base presenter class."""

    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    parameters = list()

    @staticmethod
    def json_default(value):
        """Serialize a value to JSON.

        Parameters:
            value -- value to serialize

        Returns:
            dict: serialized value
        """
        if isinstance(value, datetime.date):
            return dict(year=value.year, month=value.month, day=value.day)
        elif isinstance(value, types.MappingProxyType):
            return dict(value)
        else:
            return value.__dict__

    class AttributesObject:
        """Helper class: object holding all attributes of a report item."""

        def toJSON(self):
            """Serialize the object to JSON.

            Returns:
                json.dumps(self): serialized object
            """
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

    class ReportItemObject:
        """Helper class: object holding all data about a report item."""

        def toJSON(self):
            """Serialize the object to JSON.

            Returns:
                json.dumps(self): serialized object
            """
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

        def __init__(self, report_item, report_types, attribute_map):
            """Initialize the object.

            Parameters:
                report_item -- report item to initialize the object with
                report_types -- report types
                attribute_map -- attribute map
            """
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
                for news_item in news_item_aggregate["news_items"]:
                    self.news_items.append(news_item["news_item_data"])

            self.attrs = BasePresenter.AttributesObject()

            attribute_group_items = {}
            attribute_groups = {}

            for attribute in report_item.attributes:
                attribute_group_item_id = attribute.attribute_group_item_id
                attribute_group_items.setdefault(attribute_group_item_id, []).append(attribute)

                attr_type = attribute_map[attribute_group_item_id]
                attr_key = attr_type.title.lower().replace(" ", "_")

                attribute_groups.setdefault(attr_key, set()).add(attribute_group_item_id)

            for attribute_group_item_id, attribute_group_item in attribute_group_items.items():
                attr_type = attribute_map[attribute_group_item_id]
                attr_key = attr_type.title.lower().replace(" ", "_")

                if attr_key.startswith("cwe"):
                    value_to_add = {attribute.value: attribute.value_description for attribute in attribute_group_item}
                else:
                    max_occurrence = attr_type.max_occurrence
                    value_to_add = (
                        attribute_group_item[0].value
                        if max_occurrence == 1 and attribute_group_item
                        else [attribute.value for attribute in attribute_group_item]
                    )

                how_many_with_the_same_name = len(attribute_groups[attr_key])
                if how_many_with_the_same_name == 1:
                    setattr(self.attrs, attr_key, value_to_add)
                else:
                    if not hasattr(self.attrs, attr_key):
                        setattr(self.attrs, attr_key, [])
                    getattr(self.attrs, attr_key).append(value_to_add)

    class InputDataObject:
        """Object holding all that we received from the CORE."""

        def toJSON(self):
            """Serialize the object to JSON.

            Returns:
                json.dumps(self): serialized object
            """
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

        def get_max_tlp(self, reports):
            """Get the highest TLP value from a list of reports.

            Parameters:
                reports (list): list of reports

            Returns:
                max_tlp: Highest TLP value from the list of reports
            """
            color_values = {"WHITE": 0, "CLEAR": 1, "GREEN": 2, "AMBER": 3, "AMBER+STRICT": 4, "RED": 5}
            colors = []
            for report in reports:
                if hasattr(report.attrs, "tlp"):
                    colors.append(report.attrs.tlp)
            if colors:
                max_tlp = max(colors, key=lambda color: color_values.get(color, 1))
            else:
                max_tlp = "CLEAR"
            return max_tlp

        def link_renumbering(self, text, report_links, product_links):
            """Replace the numbers enclosed in brackets in the given text with the corresponding indices from product_links.

            Parameters:
                text (str): The text in which the numbers enclosed in brackets will be replaced.
                report_links (list): The list of report links.
                product_links (list): The list of product links.

            Returns:
                str: The updated text with the numbers enclosed in brackets replaced by the corresponding indices from product_links.
            """
            pattern = r"\[(\d+)\]"

            # Create a mapping from old indices to new indices
            mapping = {old_index + 1: product_links.index(item) + 1 for old_index, item in enumerate(report_links)}

            # Use a regular expression to find all instances of numbers enclosed in brackets
            def replace_match(match):
                old_index = int(match.group(1))
                new_index = mapping.get(old_index, old_index)  # Use the old index as a fallback
                return f"[{new_index}]"

            return re.sub(pattern, replace_match, text)

        def __init__(self, presenter_input):
            """Initialize the object.

            Parameters:
                presenter_input -- input data
            """
            # types of report items (e.g. vuln report, disinfo report)
            report_types = {}
            for report_type in presenter_input.report_types:
                # index by ID
                report_types[report_type.id] = report_type

            # attributes that can be used in report items (for internal use)
            attribute_map = {}
            for report_type in presenter_input.report_types:
                for attribute_group in report_type.attribute_groups:
                    for attribute_group_item in attribute_group.attribute_group_items:
                        attribute_map[attribute_group_item.id] = attribute_group_item

            self.product = presenter_input.product
            self.product.date = datetime.datetime.now()
            self.report_items = []

            for report in presenter_input.reports:
                self.report_items.append(BasePresenter.ReportItemObject(report, report_types, attribute_map))

            vul_report_count = 0
            product_links = []
            # If there are multiple vulnerability reports, we need to renumber the links
            for report in self.report_items:
                if report.type.startswith("Vulnerability Report"):
                    vul_report_count += 1
                    if hasattr(report.attrs, "links"):
                        for link in report.attrs.links:
                            if link not in product_links:
                                product_links.append(link)
                        if hasattr(report.attrs, "description"):
                            report.attrs.description = self.link_renumbering(report.attrs.description, report.attrs.links, product_links)
                        if hasattr(report.attrs, "recommendations"):
                            report.attrs.recommendations = self.link_renumbering(
                                report.attrs.recommendations, report.attrs.links, product_links
                            )
            # If there are vulnerability reports, set the max TLP and product links
            if vul_report_count > 0:
                self.product.max_tlp = self.get_max_tlp(self.report_items)
                self.product.links = product_links

    def get_info(self):
        """Get info about the presenter.

        Returns:
            info_schema.dump(self): info about the presenter
        """
        info_schema = PresenterSchema()
        return info_schema.dump(self)

    def print_exception(self, error):
        """Print exception.

        Parameters:
            error -- exception to print
        """
        logger.exception(f"[{self.name}] {error}")

    @staticmethod
    def generate_input_data(presenter_input):
        """Generate input data for the presenter.

        Parameters:
            presenter_input -- input data

        Returns:
            data_obj: input data object
        """
        data = BasePresenter.InputDataObject(presenter_input)
        data_json = data.toJSON()
        logger.debug(f"=== TEMPLATING FROM THE FOLLOWING INPUT ===\n{data_json}")
        data_obj = json.loads(data_json)
        return data_obj

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
