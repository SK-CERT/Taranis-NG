"""Base presenter.

Returns:
    _description_

"""

from __future__ import annotations

import datetime
import json
import os
import re
import types
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    import jinja2
from pathlib import Path

from cvss import CVSS2, CVSS3, CVSS4

from shared.common import TZ
from shared.log_manager import logger
from shared.schema.presenter import PresenterSchema

from . import jinja_filters


class BasePresenter:
    """Base presenter class."""

    type = "BASE_PRESENTER"
    name = "Base Presenter"
    description = "Base abstract type for all presenters"

    parameters: ClassVar[list] = []
    JINJA_TEMPLATES_ROOT = os.getenv("JINJA_TEMPLATES_ROOT", "/app/templates")

    @staticmethod
    def json_default(value: any) -> dict:
        """Serialize a value to JSON.

        Args:
            value: value to serialize

        Returns:
            dict: serialized value

        """
        if isinstance(value, datetime.date):
            return {"year": value.year, "month": value.month, "day": value.day}
        if isinstance(value, types.MappingProxyType):
            return dict(value)
        return value.__dict__

    class AttributesObject:
        """Helper class: object holding all attributes of a report item."""

        def to_json(self) -> str:
            """Serialize the object to JSON.

            Returns:
                json.dumps(self): serialized object

            """
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

    class ReportItemObject:
        """Helper class: object holding all data about a report item."""

        def to_json(self) -> str:
            """Serialize the object to JSON.

            Returns:
                json.dumps(self): serialized object

            """
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

        def __init__(self, report_item: any, report_types: any, attribute_map: any) -> None:
            """Initialize the object.

            Parameters
            Args:
                report_item: report item to initialize the object with
                report_types: report types
                attribute_map: attribute map

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

            # embedded news items
            self.news_items = []
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

            for (
                attribute_group_item_id,
                attribute_group_item,
            ) in attribute_group_items.items():
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

        def to_json(self) -> str:
            """Serialize the object to JSON.

            Returns:
                json.dumps(self): serialized object

            """
            return json.dumps(self, default=BasePresenter.json_default, sort_keys=True, indent=4)

        def get_max_tlp(self, reports: list) -> str:
            """Get the highest TLP value from a list of reports.

            Parameters
            Args:
                reports (list): list of reports

            Returns:
                max_tlp: Highest TLP value from the list of reports

            """
            color_values = {
                "WHITE": 0,
                "CLEAR": 1,
                "GREEN": 2,
                "AMBER": 3,
                "AMBER+STRICT": 4,
                "RED": 5,
            }
            colors = [report.attrs.tlp for report in reports if hasattr(report.attrs, "tlp")]
            return max(colors, key=lambda color: color_values.get(color, 1)) if colors else "CLEAR"

        def get_max_cvss(self, reports: list) -> float | None:
            """Get the highest CVSS value from a list of reports.

            Parameters
            Args:
                reports (list): list of reports

            Returns:
                max_cvss: Highest CVSS value from the list of reports

            """
            max_cvss = None
            for report in reports:
                if hasattr(report.attrs, "cvss"):
                    report_cvss = report.attrs.cvss.get("baseScore")
                    if report_cvss is not None and (max_cvss is None or report_cvss > max_cvss):
                        max_cvss = report_cvss
            return max_cvss

        def calculate_cvss(self, cvss_vector: str) -> dict:
            """Calculate the CVSS score from the CVSS vector.

            Parameters
            Args:
                cvss_vector (str): The CVSS vector to calculate the score from or base score value.

            Returns:
                dict: The standardized CVSS JSON.

            """
            cvss_critical_threshold = 9
            cvss_high_threshold = 7
            cvss_medium_threshold = 4
            cvss_low_threshold = 0.1
            try:
                if cvss_vector.startswith("CVSS:3."):
                    c = CVSS3(cvss_vector)
                    cvss_dict = c.as_json()
                elif cvss_vector.startswith("CVSS:4.0/"):
                    c = CVSS4(cvss_vector)
                    cvss_dict = c.as_json()
                else:
                    c = CVSS2(cvss_vector)
                    cvss_dict = c.as_json()
            except Exception:
                try:
                    if cvss_vector == "":
                        cvss_dict = {}
                    else:
                        num = float(cvss_vector)
                        # based on CVSS 3.1
                        if num >= cvss_critical_threshold:
                            desc = "CRITICAL"
                        elif num >= cvss_high_threshold:
                            desc = "HIGH"
                        elif num >= cvss_medium_threshold:
                            desc = "MEDIUM"
                        elif num >= cvss_low_threshold:
                            desc = "LOW"
                        else:
                            desc = "NONE"
                        cvss_dict = {"baseScore": num, "baseSeverity": desc}
                except ValueError:
                    logger.error(f"CVSS parsing failed: '{cvss_vector}' is not a valid vector or number.")
                    cvss_dict = {}

            return cvss_dict

        def link_renumbering(self, text: str, report_links: list, product_links: list) -> str:
            """Replace the numbers enclosed in brackets in the given text with the corresponding indices from product_links.

            Parameters
            Args:
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
            def replace_match(match: re.Match) -> str:
                old_index = int(match.group(1))
                new_index = mapping.get(old_index, old_index)  # Use the old index as a fallback
                return f"[{new_index}]"

            return re.sub(pattern, replace_match, text)

        def __init__(self, presenter_input: any) -> None:
            """Initialize the object.

            Parameters
            Args:
                presenter_input: input data

            """
            self.product = presenter_input.product
            self.product.date = datetime.datetime.now(TZ)

            report_types = self._build_report_types(presenter_input.report_types)
            attribute_map = self._build_attribute_map(presenter_input.report_types)

            self.report_items = [BasePresenter.ReportItemObject(report, report_types, attribute_map) for report in presenter_input.reports]

            vul_report_count, product_links = self._process_vul_reports(self.report_items)

            if vul_report_count > 0:
                self.product.max_tlp = self.get_max_tlp(self.report_items)
                self.product.max_cvss = self.get_max_cvss(self.report_items)
                self.product.links = product_links

        def _build_report_types(self, report_types_input: list) -> dict:
            """Build report types dictionary."""
            return {rt.id: rt for rt in report_types_input}

        def _build_attribute_map(self, report_types_input: list) -> dict:
            """Build attribute map dictionary."""
            attribute_map = {}
            for report_type in report_types_input:
                for attribute_group in report_type.attribute_groups:
                    for attribute_group_item in attribute_group.attribute_group_items:
                        attribute_map[attribute_group_item.id] = attribute_group_item
            return attribute_map

        def _process_vul_reports(self, report_items: list) -> tuple[int, list]:
            """Process vulnerability reports, renumber links and calculate CVSS."""
            vul_report_count = 0
            product_links = []
            for report in report_items:
                if not report.type.startswith("Vulnerability Report"):
                    continue
                vul_report_count += 1
                self._update_product_links(report, product_links)
                self._renumber_report_links(report, product_links)
                self._update_cvss(report)
            return vul_report_count, product_links

        def _update_product_links(self, report: any, product_links: list) -> None:
            """Update product links from report links."""
            if hasattr(report.attrs, "links"):
                for link in report.attrs.links:
                    if link not in product_links:
                        product_links.append(link)

        def _renumber_report_links(self, report: any, product_links: list) -> None:
            """Renumber links in description and recommendations."""
            if hasattr(report.attrs, "links"):
                if hasattr(report.attrs, "description"):
                    report.attrs.description = self.link_renumbering(
                        report.attrs.description,
                        report.attrs.links,
                        product_links,
                    )
                if hasattr(report.attrs, "recommendations"):
                    report.attrs.recommendations = self.link_renumbering(
                        report.attrs.recommendations,
                        report.attrs.links,
                        product_links,
                    )

        def _update_cvss(self, report: any) -> None:
            """Update CVSS value."""
            if hasattr(report.attrs, "cvss"):
                report.attrs.cvss = self.calculate_cvss(report.attrs.cvss)

    def get_info(self) -> dict:
        """Get info about the presenter.

        Returns:
            info_schema.dump(self): info about the presenter

        """
        info_schema = PresenterSchema()
        return info_schema.dump(self)

    def print_exception(self, error: Exception) -> None:
        """Print exception.

        Args:
            error: exception to print

        """
        # FIX: this should probably use regular logger
        logger.exception(f"[{self.name}] {error}")

    @staticmethod
    def generate_input_data(presenter_input: dict) -> dict:
        """Generate input data for the presenter.

        Args:
            presenter_input: input data

        Returns:
            data_obj: input data object

        """
        data = BasePresenter.InputDataObject(presenter_input)
        data_json = data.to_json()
        logger.debug(f"=== TEMPLATING FROM THE FOLLOWING INPUT ===\n{data_json}")
        return json.loads(data_json)

    @staticmethod
    def load_filters(env: jinja2.Environment) -> None:
        """Load custom filters into the Jinja2 environment.

        Args:
            env (jinja2.Environment): The Jinja2 environment to load filters into.

        """
        env.filters["strfdate"] = jinja_filters.filter_strfdate
        env.filters["regex_replace"] = jinja_filters.filter_regex_replace
        env.filters["truncate_on_symbol"] = jinja_filters.filter_truncate_on_symbol
        env.filters["tlp_color"] = jinja_filters.filter_tlp_color

    @classmethod
    def resolve_template_path(cls, template_path: str) -> tuple[str, str]:
        """Safely resolve the template path, ensuring it's within the allowed templates directory.

        Args:
            template_path (str): The user-supplied template path.
            templates_root (str): The root directory for templates (relative or absolute).

        Returns:
            (head, tail): Tuple of directory and filename for Jinja2 loading.

        Raises:
            ValueError: If the template path is outside the allowed directory.
        """
        templates_root_abs = Path(cls.JINJA_TEMPLATES_ROOT).resolve()
        template_abs = Path(template_path).resolve()
        if templates_root_abs not in template_abs.parents:
            msg = f"Template path '{template_path}' is outside the allowed templates directory '{cls.JINJA_TEMPLATES_ROOT}'"
            raise ValueError(msg)
        return str(template_abs.parent), template_abs.name
