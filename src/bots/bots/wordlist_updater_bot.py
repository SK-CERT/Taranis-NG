"""Wordlist updater bot."""

import requests

from .base_bot import BaseBot
from shared.config_bot import ConfigBot
from shared.schema import word_list
from shared.common import ignore_exceptions
from remote.core_api import CoreApi


class WordlistUpdaterBot(BaseBot):
    """A bot that updates word lists based on a given preset configuration.

    Attributes:
        type (str): The type of the bot, set to "WORDLIST_UPDATER_BOT".
        config (Config): The configuration object for the bot.
        name (str): The name of the bot.
        description (str): The description of the bot.
        parameters (dict): The parameters for the bot.
    """

    type = "WORDLIST_UPDATER_BOT"
    config = ConfigBot().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def __load_file(self, source, word_list_format):
        """Load a word list from a given source.

        Args:
            source (str): The path to the file or URL to load the word list from.
            word_list_format (str): The format of the word list. Currently supports 'txt'.
        Returns:
            list: A list of words loaded from the specified source.
        """
        if "http" in source and word_list_format == "txt":
            response = requests.get(source)
            content = response.text.strip().split("\r\n")
            content = [word for word in content]
        else:
            with open(source) as file:
                content = [line.rstrip() for line in file]

        return content

    @ignore_exceptions
    def execute(self):
        """Execute the word list updater bot with the given preset.

        Raises:
            Exception: If an error occurs during execution, it is caught and logged.
        """
        try:
            data_url = self.preset.param_key_values["DATA_URL"]
            data_format = self.preset.param_key_values["FORMAT"]
            word_list_id = self.preset.param_key_values["WORD_LIST_ID"]
            word_list_category_name = self.preset.param_key_values["WORD_LIST_CATEGORY"]
            delete_word_entries = self.preset.param_key_values["DELETE"].lower()

            source_word_list = self.__load_file(data_url, data_format)

            categories = CoreApi.get_categories(word_list_id)

            if not any(category["name"] == word_list_category_name for category in categories):

                name = word_list_category_name
                description = "Stop word list category created by Updater Bot."
                entries = []

                category = word_list.WordListCategory(name, description, "", entries)
                word_list_category_schema = word_list.WordListCategorySchema()

                CoreApi.add_word_list_category(word_list_id, word_list_category_schema.dump(category))

            if delete_word_entries == "yes":
                CoreApi.delete_word_list_category_entries(word_list_id, word_list_category_name)

            entries = []

            for word in source_word_list:

                value = word
                description = ""

                entry = word_list.WordListEntry(value, description)
                entries.append(entry)

            word_list_entries_schema = word_list.WordListEntrySchema(many=True)
            CoreApi.update_word_list_category_entries(word_list_id, word_list_category_name, word_list_entries_schema.dump(entries))

        except Exception as error:
            self.preset.logger.exception(f"Word list updater failed: {error}")

    def execute_on_event(self, preset, event_type, data):
        """Execute an action based on the given event.

        Args:
            preset (object): The preset configuration object containing parameters.
            event_type (str): The type of event that triggered this action.
            data (dict): Additional data associated with the event.
        Raises:
            Exception: If there is an error accessing the parameters in the preset.
        """
        try:
            data_url = preset.param_key_values["DATA_URL"]  # noqa F841
            format = preset.param_key_values["FORMAT"]  # noqa F841

        except Exception as error:
            self.preset.logger.exception(f"Execute on event failed: {error}")
