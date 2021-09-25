from bots.base_bot import BaseBot
from taranisng.schema.parameter import Parameter, ParameterType


class GroupingBot(BaseBot):
    type = "GROUPING_BOT"
    name = "Grouping Bot"
    description = "Bot for grouping news items into aggregates"

    parameters = [Parameter(0, "SOURCE_GROUP", "Source Group", "OSINT Source group to inspect", ParameterType.STRING),
                  Parameter(0, "REGULAR_EXPRESSION", "Regular Expression", "Regular expression for items matching",
                            ParameterType.STRING)
                  ]

    parameters.extend(BaseBot.parameters)

    def execute(self, preset):
        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION']

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            source_group = preset.parameter_values['SOURCE_GROUP']
            regexp = preset.parameter_values['REGULAR_EXPRESSION']

        except Exception as error:
            BaseBot.print_exception(preset, error)
