"""This file contains the bots initialization functionality.

It provides methods to register and initialize bots, retrieve information
about registered bots, and process events using the registered bots.
"""

import threading

from bots.analyst_bot import AnalystBot
from bots.grouping_bot import GroupingBot
from bots.wordlist_updater_bot import WordlistUpdaterBot

bots = {}


def initialize() -> None:
    """Initialize and register all bots."""
    register_bot(AnalystBot())
    register_bot(GroupingBot())
    register_bot(WordlistUpdaterBot())


def register_bot(bot: object) -> None:
    """Register a bot and initialize it in a separate thread.

    Parameters:
        bot: The bot object to register.
    """
    bots[bot.bot_type] = bot

    class InitializeThread(threading.Thread):
        """A thread class for initializing the bot."""

        @classmethod
        def run(cls) -> None:
            """Run method for the bot manager.

            This method initializes the bot.
            """
            bot.initialize()

    initialize_thread = InitializeThread()
    initialize_thread.start()


def get_registered_bots_info() -> list:
    """Retrieve information about all registered bots.

    Returns:
        list: A list of information about each registered bot.
    """
    return [b.get_info() for b in bots.values()]


def process_event(event_type: str, data: dict) -> None:
    """Process an event by passing it to all registered bots.

    Parameters:
        event_type (str): The type of the event.
        data (dict): The data associated with the event.
    """
    for bot in bots.values():
        bot.process_event(event_type, data)
