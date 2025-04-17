"""AnalystBot class."""

import re

from .base_bot import BaseBot
from managers.log_manager import logger
from shared.config_bot import ConfigBot
from shared.schema import news_item
from remote.core_api import CoreApi


class AnalystBot(BaseBot):
    """AnalystBot class.

    This class represents a bot for news items analysis.
    Attributes:
        type (str): The type of the bot.
        name (str): The name of the bot.
        description (str): The description of the bot.
        parameters (list): The list of parameters for the bot.
        regexp (list): The list of regular expressions for data analysis.
        attr_name (list): The list of attribute names for extracted data.
        news_items (list): The list of news items.
        news_items_data (list): The list of news items data.
    Methods:
        execute(preset): Executes the bot with the given preset.
        execute_on_event(preset, event_type, data): Executes the bot on an event with the given preset, event type, and data.
    """

    type = "ANALYST_BOT"
    config = ConfigBot().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters
    regexp = []
    attr_name = []
    news_items = []
    news_items_data = []

    def execute(self, preset):
        """Execute the analyst bot with the given preset.

        Parameters:
            preset (Preset): The preset containing the parameter values.
        Raises:
            Exception: If an error occurs during execution.
        """
        self.log_prefix = f"{self.name} {preset.name}"
        try:
            source_group = preset.parameter_values["SOURCE_GROUP"]  # noqa F841
            regexp = preset.parameter_values["REGULAR_EXPRESSION"]
            attr_name = preset.parameter_values["ATTRIBUTE_NAME"]
            interval = preset.parameter_values["REFRESH_INTERVAL"]

            # support for multiple regexps
            regexp = regexp.split(";;;")
            attr_name = attr_name.split(";;;")
            if len(regexp) > len(attr_name):
                regexp = regexp[: len(attr_name)]
            elif len(attr_name) > len(regexp):
                attr_name = attr_name[: len(regexp)]

            bots_params = dict(zip(attr_name, regexp))
            limit = BaseBot.history(interval)
            news_items_data, code = CoreApi.get_news_items_data(limit)
            if code == 200 and news_items_data is not None:
                logger.debug(f"News items found: {len(news_items_data)}, since {limit}")
                for item in news_items_data:
                    if item:
                        news_item_id = item["id"]
                        title = item["title"]
                        preview = item["review"]
                        content = item["content"]
                        analyzed_text = " ".join([title, preview, content])
                        attributes = []
                        for key, value in bots_params.items():
                            uniq_list = []
                            # print('Key:', key, 'Regex:', value, flush=True)
                            for finding in re.finditer(value, analyzed_text):
                                if len(finding.groups()) > 0:
                                    found_value = finding.group(1)
                                else:
                                    found_value = finding.group(0)
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
                            logger.debug(f"Found: {len(attributes)}, {title}, {item['collected']}")
                            news_item_attributes_schema = news_item.NewsItemAttributeSchema(many=True)
                            CoreApi.update_news_item_attributes(news_item_id, news_item_attributes_schema.dump(attributes))
            else:
                logger.error(
                    f"News items not received, Code: {code}" f"{', response: ' + str(news_items_data) if news_items_data is not None else ''}"
                )

        except Exception as error:
            logger.exception(f"Failed to parse attributes: {error}")

    def execute_on_event(self, preset, event_type, data):
        """Execute the specified preset on the given event.

        Parameters:
            preset (Preset): The preset to execute.
            event_type (str): The type of the event.
            data (dict): The data associated with the event.
        Raises:
            Exception: If there is an error while executing the preset.
        """
        try:
            source_group = preset.parameter_values["SOURCE_GROUP"]  # noqa F841
            regexp = preset.parameter_values["REGULAR_EXPRESSION"]  # noqa F841
            attr_name = preset.parameter_values["ATTRIBUTE_NAME"]  # noqa F841

        except Exception as error:
            logger.exception(f"Execute on event failed: {error}")
