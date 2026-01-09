"""Contains the CollectorsManager class, which manages the collectors."""

import os
import threading
import time
from http import HTTPStatus
from pathlib import Path

from remote.core_api import CoreApi

from collectors.email_collector import EmailCollector
from collectors.manual_collector import ManualCollector
from collectors.rss_collector import RSSCollector
from collectors.scheduled_tasks_collector import ScheduledTasksCollector
from collectors.slack_collector import SlackCollector
from collectors.twitter_collector import TwitterCollector
from collectors.web_collector import WebCollector
from shared.log_manager import logger

collectors = {}
status_report_thread = None


def report_status() -> None:
    """Continuously send status updates to the Core API."""
    logger.debug("Report status: Awaiting initialization of CORE (timeout: 20s)")
    time.sleep(20)  # wait for the CORE
    while True:
        logger.debug("Sending status update...")
        response, status_code = CoreApi.update_collector_status()
        if status_code != HTTPStatus.OK:
            logger.error(
                f"Core status update response failed, Code: {status_code}{', response: ' + str(response) if response is not None else ''}",
            )

        time.sleep(55)


def initialize() -> None:
    """Initialize the collectors."""
    logger.info("Initializing collectors...")

    # inform core that this collector node is alive
    status_report_thread = threading.Thread(target=report_status)
    status_report_thread.daemon = True
    status_report_thread.start()

    register_collector(RSSCollector())
    register_collector(WebCollector())
    register_collector(TwitterCollector())
    register_collector(EmailCollector())
    register_collector(SlackCollector())
    register_collector(ManualCollector())
    register_collector(ScheduledTasksCollector())

    logger.info("Collectors initialized.")


def register_collector(collector: object) -> None:
    """Register a collector.

    Parameters:
        collector: The collector object to register.
    """
    collectors[collector.type] = collector

    class InitializeThread(threading.Thread):
        """A thread class for initializing the collector."""

        @classmethod
        def run(cls) -> None:
            """Run method for the collectors manager.

            Parameters:
                cls: The class object.
            """
            collector.initialize()

    initialize_thread = InitializeThread()
    initialize_thread.start()


def refresh_collector(collector_type: str) -> HTTPStatus:
    """Refresh the specified collector.

    Parameters:
        collector_type (str): The type of the collector to refresh.

    Returns:
        (int): The HTTP status code indicating the result of the refresh operation. Returns 200 if the collector was refreshed successfully,
             or 403 if the collector type is not found in the collectors dictionary.
    """
    if collector_type in collectors:

        class RefreshThread(threading.Thread):
            """A thread class for refreshing the collector."""

            @classmethod
            def run(cls) -> None:
                """Run method for the collectors manager.

                Parameters:
                    cls: The class object.
                """
                collectors[collector_type].refresh()

        refresh_thread = RefreshThread()
        refresh_thread.start()
        return HTTPStatus.OK

    return HTTPStatus.FORBIDDEN


def get_registered_collectors_info(collector_id: str) -> list:
    """Retrieve information about registered collectors.

    Parameters:
        id (str): The ID of the collector.

    Returns:
        collectors_info (list): A list of collector information.
    """
    config_file = Path(os.getenv("COLLECTOR_CONFIG_FILE"))
    with config_file.open("w") as file:
        file.write(collector_id)

    return [c.get_info() for c in collectors.values()]
