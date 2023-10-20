import re

from .base_bot import BaseBot
from managers.log_manager import log_debug, log_bot_activity
from shared.schema import news_item
from shared.schema.parameter import Parameter, ParameterType
from remote.core_api import CoreApi


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
            regexp = preset.parameter_values['REGULAR_EXPRESSION']
            attr_name = preset.parameter_values['ATTRIBUTE_NAME']
            interval = preset.parameter_values['REFRESH_INTERVAL']

            # support for multiple regexps
            regexp = regexp.split(';;;')
            attr_name = attr_name.split(';;;')
            if len(regexp) > len(attr_name):
                regexp = regexp[:len(attr_name)]
            elif len(attr_name) > len(regexp):
                attr_name = attr_name[:len(regexp)]

            bots_params = dict(zip(attr_name, regexp))
            limit = BaseBot.history(interval)
            log_bot_activity(preset.name, 'running with date limit {}'.format(limit))
            news_items_data, code = CoreApi.get_news_items_data(limit)
            if code == 200 and news_items_data is not None:
                for item in news_items_data:
                    if item:
                        news_item_id = item['id']
                        title = item['title']
                        preview = item['review']
                        content = item['content']

                        analyzed_text = ' '.join([title, preview, content])

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
                            
                            # app is checking combination ID + Value in DB before INSERT (attribute_value_identical) so check for some duplicity here (faster)
                            for found_value in uniq_list:
                                binary_mime_type = ''
                                binary_value = ''
                                news_attribute = news_item.NewsItemAttribute(key, found_value, binary_mime_type, binary_value)
                                attributes.append(news_attribute)

                        if len(attributes) > 0:
                            log_debug('Processing item id: {}, {}, Found: {}'.format(news_item_id, item['collected'], len(attributes)))
                            news_item_attributes_schema = news_item.NewsItemAttributeSchema(many=True)
                            CoreApi.update_news_item_attributes(news_item_id, news_item_attributes_schema.dump(attributes))

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION']
            attr_name = preset.parameter_values['ATTRIBUTE_NAME']

        except Exception as error:
            BaseBot.print_exception(preset, error)
