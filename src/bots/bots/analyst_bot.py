from bots.base_bot import BaseBot
from taranisng.schema.parameter import Parameter, ParameterType
from taranisng.schema.news_item import NewsItemData, NewsItemAttribute
from remote.core_api import CoreApi
import re


class AnalystBot(BaseBot):
    type = "ANALYST_BOT"
    name = "Analyst Bot"
    description = "Bot for news items analysis"

    parameters = [Parameter(0, "SOURCE_GROUP", "Source Group", "OSINT Source group to inspect", ParameterType.STRING),
                  Parameter(0, "REGULAR_EXPRESSION", "Regular Expression", "Regular expression for data analysis",
                            ParameterType.STRING),
                  Parameter(0, "ATTRIBUTE_NAME", "Attribute name", "Name of attribute for extracted data",
                            ParameterType.STRING)
                  ]

    parameters.extend(BaseBot.parameters)

    regexp = []
    attr_name = []
    news_items = []
    news_items_data = []

    def execute(self, preset):
        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION'].replace(' ', '')
            attr_name = preset.parameter_values['ATTRIBUTE_NAME'].replace(' ', '')
            interval = preset.parameter_values['REFRESH_INTERVAL']

            regexp = regexp.split(',')
            attr_name = attr_name.split(',')

            bots_params = dict(zip(attr_name, regexp))

            news_items_data = CoreApi.get_news_items_data()
            limit = BaseBot.history(interval)

            for key, value in bots_params.items():

                for item in news_items_data:

                    collected = item['collected']
                    news_item_data_id = item['id']

                    # TODO change condition to bigger then...
                    if collected < str(limit):
                        title = item['title']
                        preview = item['review']
                        content = item['content']

                        analyzed_text = ''.join([title, preview, content]).split()
                        analyzed_text = [item.replace('.', '') if item.endswith('.') else item
                                         for item in analyzed_text]
                        analyzed_text = [item.replace(',', '') if item.endswith(',') else item
                                         for item in analyzed_text]

                        for element in analyzed_text:
                            finding = re.search("(" + value + ")", element)
                            if finding:
                                found_value = finding.group(1)

                                data = {
                                    'id': item['id'],
                                    'hash': item['hash'],
                                    'title': item['title'],
                                    'review': item['review'],
                                    'source': item['source'],
                                    'link': item['link'],
                                    'published': item['published'],
                                    'author': item['author'],
                                    'collected': item['collected'],
                                    'content': item['content'],
                                    'osint_source_id': item['osint_source_id'],
                                    'attributes': [
                                        {
                                            'key': key,
                                            'value': found_value,
                                            'binary_mime_type': '',
                                            'binary_value': ''
                                        }
                                    ]
                                }

                                # print(data)
                                BaseBot.update(news_item_data_id, data)

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION']
            attr_name = preset.parameter_values['ATTRIBUTE_NAME']

        except Exception as error:
            BaseBot.print_exception(preset, error)
