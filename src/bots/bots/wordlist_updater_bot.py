from bots.base_bot import BaseBot
from taranisng.schema.parameter import Parameter, ParameterType


class WordlistUpdaterBot(BaseBot):
    type = "WORDLIST_UPDATER_BOT"
    name = "Wordlist Updater Bot"
    description = "Bot for updating word lists"

    parameters = [Parameter(0, "DATA_URL", "Data URL", "Source for words", ParameterType.STRING),
                  Parameter(0, "FORMAT", "Format", "Format of words source",
                            ParameterType.STRING)
                  ]

    parameters.extend(BaseBot.parameters)

    def execute(self, preset):
        try:
            data_url = preset.parameter_values['DATA_URL']
            format = preset.parameter_values['FORMAT']

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            data_url = preset.parameter_values['DATA_URL']
            format = preset.parameter_values['FORMAT']

        except Exception as error:
            BaseBot.print_exception(preset, error)
