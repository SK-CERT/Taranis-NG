"""Grouping bot."""

import json
import re

from remote.core_api import CoreApi

from shared.common import ignore_exceptions
from shared.config_bot import ConfigBot

from .base_bot import BaseBot


class GroupingBot(BaseBot):
    """GroupingBot is a bot that processes news items from a specified source group.

    It applies a regular expression to find specific patterns in the content, and
    groups news items based on the findings.

    Attributes:
        type (str): The type of the bot, set to "GROUPING_BOT".
        config (Config): Configuration object for the bot.
        name (str): The name of the bot.
        description (str): The description of the bot.
        parameters (dict): The parameters for the bot.
    """

    type = "GROUPING_BOT"
    config = ConfigBot().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @ignore_exceptions
    def execute(self):
        """Execute the grouping bot with the given preset.

        Raises:
            Exception: If an error occurs during execution, it is caught and logged.
        """
        try:
            source_group = self.preset.param_key_values["SOURCE_GROUP"]
            regexp = self.preset.param_key_values["REGULAR_EXPRESSION"]
            interval = self.preset.param_key_values["REFRESH_INTERVAL"]

            limit = BaseBot.history(interval)

            data = CoreApi.get_news_items_aggregate(source_group, limit)
            data = json.loads(data)

            if data:
                data_findings = []  # noqa F841

                for aggregate in data:
                    findings = []

                    for news_item in aggregate["news_items"]:
                        content = news_item["news_item_data"]["content"]

                        analyzed_content = "".join(content).split()
                        analyzed_content = [item.replace(".", "") if item.endswith(".") else item for item in analyzed_content]
                        analyzed_content = [item.replace(",", "") if item.endswith(",") else item for item in analyzed_content]

                        analyzed_content = set(analyzed_content)

                        for element in analyzed_content:
                            finding = re.search("(" + regexp + ")", element)

                            if finding:
                                finding = [news_item["id"], finding.group(1)]
                                findings.append(finding)

                    # NEXT PART OF CODE IS FOR FINDINGS IN ONE AGGREGATE
                    # IT WILL GROUP NEWS_ITEMS TOGETHER FROM ONE AGGREGATE

                    if findings:
                        grouped_ids = []
                        values = {}

                        for k, val in findings:
                            if val in values:
                                grouped = [x for x in grouped_ids if len(x) != 1]
                                x_flat = [k for sublist in grouped for k in sublist]

                                if str(k) not in x_flat:
                                    grouped_ids[values[val]].extend(str(k))

                            else:
                                grouped_ids.append([str(k)])
                                values[val] = len(values)

                        grouped_ids = [x for x in grouped_ids if len(x) != 1]

                        marker_set = set()
                        corrected_grouped_ids = []

                        for sublist in grouped_ids:
                            for element in sublist:
                                if element not in marker_set:
                                    marker_set.add(element)
                                else:
                                    break
                            else:
                                corrected_grouped_ids.append(sublist)

                        for sublist in corrected_grouped_ids:
                            items = []

                            for element in sublist:
                                item = {"type": "ITEM", "id": int(element)}
                                items.append(item)

                            data = {"action": "GROUP", "items": items}
                            CoreApi.news_items_grouping(data)

                # NEXT PART OF CODE IS FOR FINDINGS IN ALL AGGREGATES
                # IT WILL GROUP NEWS_ITEMS TOGETHER FROM VARIOUS AGGREGATES

                #     data_findings.append(findings)
                #
                # data_findings = [item for sublist in data_findings for item in sublist]
                #
                # if data_findings:
                #
                #     grouped_ids = []
                #     values = {}
                #
                #     for k, val in data_findings:
                #
                #         if val in values:
                #
                #             grouped = [x for x in grouped_ids if len(x) != 1]
                #             x_flat = [k for sublist in grouped for k in sublist]
                #
                #             if str(k) not in x_flat:
                #
                #                 grouped_ids[values[val]].extend(str(k))
                #
                #         else:
                #             grouped_ids.append([str(k)])
                #             values[val] = len(values)
                #
                #     grouped_ids = [x for x in grouped_ids if len(x) != 1]
                #
                #     marker_set = set()
                #     corrected_grouped_ids = []
                #
                #     for sublist in grouped_ids:
                #         for element in sublist:
                #             if element not in marker_set:
                #                 marker_set.add(element)
                #             else:
                #                 break
                #         else:
                #             corrected_grouped_ids.append(sublist)
                #
                #     for sublist in corrected_grouped_ids:
                #
                #         items = []
                #
                #         for element in sublist:
                #
                #             item = {
                #                 'type': 'ITEM',
                #                 'id': int(element)
                #             }
                #             items.append(item)
                #
                #         data = {
                #             'action': 'GROUP',
                #             'items': items
                #         }
                #         CoreApi.news_items_grouping(data)

        except Exception as error:
            self.preset.logger.exception(f"Grouping failed: {error}")

    def execute_on_event(self, preset, event_type, data):
        """Execute actions based on the given event.

        Args:
            preset (object): The preset configuration containing parameter values.
            event_type (str): The type of event that triggered this execution.
            data (dict): Additional data related to the event.

        Raises:
            Exception: If there is an error accessing the parameter values in the preset.
        """
        try:
            source_group = preset.param_key_values["SOURCE_GROUP"]  # noqa F841
            regexp = preset.param_key_values["REGULAR_EXPRESSION"]  # noqa F841

        except Exception as error:
            self.preset.logger.exception(f"Execute on event failed: {error}")
