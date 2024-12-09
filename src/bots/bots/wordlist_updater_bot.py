"""Wordlist updater bot."""

import requests

from .base_bot import BaseBot
from shared.config_bot import ConfigBot
from shared.schema import word_list
from remote.core_api import CoreApi


class WordlistUpdaterBot(BaseBot):
    """XXX_2069."""

    type = "WORDLIST_UPDATER_BOT"
    config = ConfigBot().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def execute(self, preset):
        """XXX_2069."""

        def load_file(source, word_list_format):
            """XXX_2069."""
            if "http" in source and word_list_format == "txt":
                response = requests.get(source)
                content = response.text.strip().split("\r\n")
                content = [word for word in content]
            else:
                with open(source) as file:
                    content = [line.rstrip() for line in file]

            return content

        try:
            data_url = preset.parameter_values["DATA_URL"]
            data_format = preset.parameter_values["FORMAT"]
            word_list_id = preset.parameter_values["WORD_LIST_ID"]
            word_list_category_name = preset.parameter_values["WORD_LIST_CATEGORY"]
            delete_word_entries = preset.parameter_values["DELETE"].lower()

            source_word_list = load_file(data_url, data_format)

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
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        """XXX_2069."""
        try:
            data_url = preset.parameter_values["DATA_URL"]  # noqa F841
            format = preset.parameter_values["FORMAT"]  # noqa F841

        except Exception as error:
            BaseBot.print_exception(preset, error)
