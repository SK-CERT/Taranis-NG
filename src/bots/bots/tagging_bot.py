import json
import re

from .base_bot import BaseBot
from schema.parameter import Parameter, ParameterType
from remote.core_api import CoreApi
from managers import log_manager
import datetime

class TaggingBot(BaseBot):
    type = "TAGGING_BOT"
    name = "Tagging Bot"
    description = "Bot for tagging news items"

    parameters = [
        Parameter(
            0,
            "SOURCE_GROUP",
            "Source Group",
            "OSINT Source group to inspect",
            ParameterType.STRING,
        ),
        Parameter(
            0,
            "KEYWORDS",
            "Keywords",
            "Keywords to Tag on seperated by ','",
            ParameterType.STRING,
        ),
    ]
    parameters.extend(BaseBot.parameters)

    def execute(self, preset):
        try:
            source_group = preset.parameter_values["SOURCE_GROUP"]
            interval = preset.parameter_values["REFRESH_INTERVAL"]
            keywords = preset.parameter_values["KEYWORDS"]

            limit = BaseBot.history(interval)
            limit = datetime.datetime.now() - datetime.timedelta(weeks=5)
            log_manager.log_debug(f"LIMIT: {limit}")

            data, status = CoreApi.get_news_items_aggregate(source_group, limit)
            if status != 200:
              return

            if data:
                for aggregate in data:
                    findings = {}
                    for news_item in aggregate["news_items"]:
                        content = news_item["news_item_data"]["content"]

                        for keyword in keywords.split(","):
                            if keyword in content:
                                if news_item["id"] in findings:
                                    findings[news_item["id"]] = findings[
                                        news_item["id"]
                                    ].add(keyword)
                                else:
                                    findings[news_item["id"]] = {keyword}
                    for news_id, keyword in findings.items():
                      log_manager.log_debug(f"news_id: {news_id}, keyword: {keyword}")
                      CoreApi.update_news_item_tags(news_id, list(keyword))

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            source_group = preset.parameter_values["SOURCE_GROUP"]
            keywords = preset.parameter_values["KEYWORDS"]

        except Exception as error:
            BaseBot.print_exception(preset, error)
