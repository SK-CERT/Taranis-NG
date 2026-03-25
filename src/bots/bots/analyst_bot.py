"""AnalystBot class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.schema.bot_preset import BotPreset


import re
from http import HTTPStatus

from remote.core_api import CoreApi
from shared.common import ignore_exceptions
from shared.config_bot import ConfigBot
from shared.schema import news_item

from .base_bot import BaseBot


class AnalystBot(BaseBot):
    """This class represents a bot for news items analysis."""

    bot_type = "ANALYST_BOT"

    def __init__(self) -> None:
        """Initialize the class."""
        self.config = ConfigBot().get_config_by_type(self.bot_type)
        self.name = self.config.name
        self.description = self.config.description
        self.parameters = self.config.parameters
        self.regexp = []
        self.attr_name = []
        self.news_items = []
        self.news_items_data = []

    @ignore_exceptions
    def execute(self) -> None:
        """Execute the analyst bot with the given preset.

        Raises:
            Exception: If an error occurs during execution.
        """
        try:
            source_group = self.preset.param_key_values["SOURCE_GROUP"]  # noqa: F841
            regexp = self.preset.param_key_values["REGULAR_EXPRESSION"]
            attr_name = self.preset.param_key_values["ATTRIBUTE_NAME"]
            interval = self.preset.param_key_values["REFRESH_INTERVAL"]

            # support for multiple regexps
            regexp = regexp.split(";;;")
            attr_name = attr_name.split(";;;")
            if len(regexp) > len(attr_name):
                regexp = regexp[: len(attr_name)]
            elif len(attr_name) > len(regexp):
                attr_name = attr_name[: len(regexp)]

            bots_params = dict(zip(attr_name, regexp, strict=False))
            limit = BaseBot.history(interval)
            news_items_data, code = CoreApi.get_news_items_data(limit)
            if code != HTTPStatus.OK or news_items_data is None:
                self.preset.logger.error(
                    f"News items not received, Code: {code}{', response: ' + str(news_items_data) if news_items_data is not None else ''}",
                )
                return

            self.preset.logger.debug(f"News items found: {len(news_items_data)}, since {limit}")
            for item in news_items_data:
                if item:
                    news_item_id = item["id"]
                    title = item["title"]
                    preview = item["review"]
                    content = item["content"]
                    analyzed_text = f"{title} {preview} {content}"
                    attributes = []
                    for key, value in bots_params.items():
                        uniq_list = []
                        # print('Key:', key, 'Regex:', value, flush=True)
                        for finding in re.finditer(value, analyzed_text):
                            found_value = finding.group(1) if len(finding.groups()) > 0 else finding.group(0)
                            # print('Found:', found_value, flush=True)
                            if found_value not in uniq_list:
                                uniq_list.append(found_value)

                        # app is checking combination ID + Value in DB before INSERT (attribute_value_identical)
                        # so check for some duplicity here (faster)
                        for found_value in uniq_list:
                            binary_mime_type = ""
                            binary_value = ""
                            news_attribute = news_item.NewsItemAttribute(key, found_value, binary_mime_type, binary_value)
                            attributes.append(news_attribute)

                    if len(attributes) > 0:
                        self.preset.logger.debug(f"Found: {len(attributes)}, {title}, {item['collected']}")
                        news_item_attributes_schema = news_item.NewsItemAttributeSchema(many=True)
                        CoreApi.update_news_item_attributes(news_item_id, news_item_attributes_schema.dump(attributes))

        except Exception as error:
            self.preset.logger.exception(f"Failed to parse attributes: {error}")

    def execute_on_event(self, preset: BotPreset, event_type: str, data: dict) -> None:  # noqa: ARG002
        """Execute the specified preset on the given event.

        Parameters:
            preset (BotPreset): The preset to execute.
            event_type (str): The type of the event.
            data (dict): The data associated with the event.

        Raises:
            Exception: If there is an error while executing the preset.
        """
        try:
            source_group = preset.param_key_values["SOURCE_GROUP"]  # noqa: F841
            regexp = preset.param_key_values["REGULAR_EXPRESSION"]  # noqa: F841
            attr_name = preset.param_key_values["ATTRIBUTE_NAME"]  # noqa: F841

        except Exception as error:
            self.preset.logger.exception(f"Execute on event failed: {error}")
