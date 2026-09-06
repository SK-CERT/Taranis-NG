"""Contains the CollectorsManager class, which manages the collectors."""

import os
import threading
import time
from http import HTTPStatus
from pathlib import Path

from remote.core_api import CoreApi
from shared.log_manager import logger

from collectors.email_collector import EmailCollector
from collectors.manual_collector import ManualCollector
from collectors.rss_collector import RSSCollector
from collectors.scheduled_tasks_collector import ScheduledTasksCollector
from collectors.slack_collector import SlackCollector
from collectors.twitter_collector import TwitterCollector
from collectors.web_collector import WebCollector

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

        report_schedule()
        time.sleep(55)


def report_schedule() -> None:
    """Tell core when each source is next due, so the GUI can count down to it.

    Piggybacks on the status heartbeat rather than adding a timer: the schedule only changes on a
    refresh or when a job runs, so a value up to a minute old is fine for a countdown measured in
    minutes or hours.
    """
    due = {}
    for collector in collectors.values():
        due.update(collector.next_run_by_source())
    if not due:
        return
    response, status_code = CoreApi.update_sources_schedule(due)
    if status_code != HTTPStatus.OK:
        logger.error(f"Core schedule update failed, Code: {status_code}, response: {response}")


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
    collectors[collector.collector_type] = collector

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


def refresh_collector(collector_type: str, *, collect_now: bool = True) -> HTTPStatus:
    """Refresh the specified collector.

    Parameters:
        collector_type (str): The type of the collector to refresh.
        collect_now (bool): Whether the refresh should also collect every source straight away.

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
                collectors[collector_type].refresh(collect_now=collect_now)

        refresh_thread = RefreshThread()
        refresh_thread.start()
        return HTTPStatus.OK

    return HTTPStatus.FORBIDDEN


def collect_source_now(collector_type: str, source_id: str) -> tuple[dict, HTTPStatus]:
    """Collect one OSINT source straight away.

    Parameters:
        collector_type (str): The type of the collector owning the source.
        source_id (str): The id of the source to collect.

    Returns:
        (dict, HTTPStatus): The collector's answer, or 403 when the type is not registered here.
    """
    if collector_type not in collectors:
        return {"error": "unknown collector type"}, HTTPStatus.FORBIDDEN
    return collectors[collector_type].collect_source_now(source_id)


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
