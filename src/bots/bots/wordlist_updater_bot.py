"""Wordlist updater bot."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.schema.bot_preset import BotPreset

import os
import re
import urllib.request
from http import HTTPStatus
from pathlib import Path

from remote.core_api import CoreApi
from shared.common import ignore_exceptions
from shared.config_bot import ConfigBot
from shared.schema import word_list
from shared.url_guard import build_guarded_opener

from .base_bot import BaseBot

# Where a preset may name a local word list file: a directory an operator mounts on purpose.
# Anything else on the node (its Docker secrets, its code) must never become word list entries
# that core then shows to whoever can read word lists.
WORDLIST_DIR = Path(os.getenv("TARANIS_WORDLIST_DIR", "/app/wordlists"))
# A word list is text; anything bigger is a mistake or an attack on the node's memory.
MAX_WORDLIST_BYTES = 10 * 1024 * 1024
# The bytes alone do not bound the work: every entry goes to core in one request and becomes a row
# there, and 10 MiB of two-character lines are some 3.5 million of them. The list's host is a
# third party, so the number of entries and the length of each are capped too.
MAX_WORDLIST_ENTRIES = 200_000
MAX_WORD_LENGTH = 500
FETCH_TIMEOUT = 30
_URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


class WordlistUpdaterBot(BaseBot):
    """A bot that updates word lists based on a given preset configuration."""

    bot_type = "WORDLIST_UPDATER_BOT"

    def __init__(self) -> None:
        """Initialize the class."""
        self.config = ConfigBot().get_config_by_type(self.bot_type)
        self.name = self.config.name
        self.description = self.config.description
        self.parameters = self.config.parameters

    @staticmethod
    def load_words(source: str, word_list_format: str) -> list[str]:
        """Load a word list from a URL or from a file in the word list directory.

        A URL is fetched only when it is http(s) and its host - and that of every redirect -
        resolves to public addresses (``shared.url_guard``, as for collectors). A file is read
        only from ``WORDLIST_DIR``. Either is capped at ``MAX_WORDLIST_BYTES``, at
        ``MAX_WORDLIST_ENTRIES`` lines and at ``MAX_WORD_LENGTH`` characters a line; a list
        over any cap is refused, not cut short.

        Args:
            source (str): A URL, or a file name relative to ``WORDLIST_DIR``.
            word_list_format (str): The format of the word list. Only "txt" (one word per line).

        Returns:
            list: The words, one per line.

        Raises:
            ValueError: For an unsupported format, a refused URL or path, or a list over a cap.
        """
        if (word_list_format or "txt").strip().lower() != "txt":
            msg = f"Unsupported word list format '{word_list_format}'; only txt is supported"
            raise ValueError(msg)
        source = (source or "").strip()
        if not source:
            msg = "No word list source is set"
            raise ValueError(msg)
        data = WordlistUpdaterBot._download(source) if _URL_SCHEME.match(source) else WordlistUpdaterBot._read_file(source)
        if len(data) > MAX_WORDLIST_BYTES:
            msg = f"The word list is larger than {MAX_WORDLIST_BYTES} bytes"
            raise ValueError(msg)
        words = [line.rstrip() for line in data.decode("utf-8", errors="replace").strip().splitlines()]
        if len(words) > MAX_WORDLIST_ENTRIES:
            msg = f"The word list has more than {MAX_WORDLIST_ENTRIES} entries"
            raise ValueError(msg)
        too_long = next((number for number, word in enumerate(words, 1) if len(word) > MAX_WORD_LENGTH), None)
        if too_long:
            msg = f"Entry {too_long} of the word list is longer than {MAX_WORD_LENGTH} characters"
            raise ValueError(msg)
        return words

    @staticmethod
    def _download(url: str) -> bytes:
        """Fetch a word list over http(s) from a public address (raises BlockedUrlError otherwise)."""
        request = urllib.request.Request(url, headers={"User-Agent": "Taranis-NG wordlist updater"})  # noqa: S310 - checked by the guard
        with build_guarded_opener()(request, timeout=FETCH_TIMEOUT) as response:
            return response.read(MAX_WORDLIST_BYTES + 1)

    @staticmethod
    def _read_file(name: str) -> bytes:
        """Read a word list file, which must lie inside ``WORDLIST_DIR``."""
        root = WORDLIST_DIR.resolve()
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            msg = f"A word list file must be a file in {root}; '{name}' is not"
            raise ValueError(msg)
        with path.open("rb") as file:
            return file.read(MAX_WORDLIST_BYTES + 1)

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

            source_word_list = self.load_words(data_url, data_format)

            categories, status = CoreApi.get_categories(word_list_id)
            if status != HTTPStatus.OK or not isinstance(categories, list):
                self.preset.logger.error(f"Word list updater: could not read the categories of word list {word_list_id}")
                return

            if not any(category.get("name") == word_list_category_name for category in categories):
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
