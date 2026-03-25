"""Wordlist updater bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.schema.bot_preset import BotPreset

from pathlib import Path

import requests
from remote.core_api import CoreApi
from shared.common import ignore_exceptions
from shared.config_bot import ConfigBot
from shared.schema import word_list

from .base_bot import BaseBot


class WordlistUpdaterBot(BaseBot):
    """A bot that updates word lists based on a given preset configuration."""

    bot_type = "WORDLIST_UPDATER_BOT"

    def __init__(self) -> None:
        """Initialize the class."""
        self.config = ConfigBot().get_config_by_type(self.bot_type)
        self.name = self.config.name
        self.description = self.config.description
        self.parameters = self.config.parameters

    def __load_file(self, source: str, word_list_format: str) -> list[str]:
        """Load a word list from a given source.

        Args:
            source (str): The path to the file or URL to load the word list from.
            word_list_format (str): The format of the word list. Currently supports 'txt'.

        Returns:
            list: A list of words loaded from the specified source.
        """
        if "http" in source and word_list_format == "txt":
            response = requests.get(source, timeout=10)
            content = response.text.strip().splitlines()
        else:
            with Path(source).open() as file:
                content = [line.rstrip() for line in file]

        return content

    @ignore_exceptions
    def execute(self) -> None:
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

    def execute_on_event(self, preset: BotPreset, event_type: str, data: dict) -> None:  # noqa: ARG002
        """Execute an action based on the given event.

        Args:
            preset (BotPreset): The preset configuration object containing parameters.
            event_type (str): The type of event that triggered this action.
            data (dict): Additional data associated with the event.

        Raises:
            Exception: If there is an error accessing the parameters in the preset.
        """
        try:
            data_url = preset.param_key_values["DATA_URL"]  # noqa: F841
            data_format = preset.param_key_values["FORMAT"]  # noqa: F841

        except Exception as error:
            self.preset.logger.exception(f"Execute on event failed: {error}")
