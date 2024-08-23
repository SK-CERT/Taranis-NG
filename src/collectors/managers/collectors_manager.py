"""Contains the CollectorsManager class, which manages the collectors."""

import os
import threading
import time

from managers.log_manager import logger
from collectors.atom_collector import AtomCollector
from collectors.email_collector import EmailCollector
from collectors.manual_collector import ManualCollector
from collectors.rss_collector import RSSCollector
from collectors.scheduled_tasks_collector import ScheduledTasksCollector
from collectors.slack_collector import SlackCollector
from collectors.twitter_collector import TwitterCollector
from collectors.web_collector import WebCollector
from remote.core_api import CoreApi

collectors = {}
status_report_thread = None


def reportStatus():
    """Continuously send status updates to the Core API."""
    while True:
        logger.log_debug(f"[{__name__}] Sending status update...")
        response, status_code = CoreApi.update_collector_status()
        if status_code != 200:
            logger.log_warning(f"[{__name__}] Core status update response: HTTP {status_code}, {response}")
        # for debugging scheduler tasks
        # for key in collectors:
        #     for source in collectors[key].osint_sources:
        #         if hasattr(source, "scheduler_job"):
        #             logger.log_debug("Last run: {}, Next run: {}, {}".format(source.scheduler_job.last_run or "never",
        #                source.scheduler_job.next_run or "never", source.name))
        time.sleep(55)


def initialize():
    """Initialize the collectors."""
    logger.log_system_activity_info(__name__, "Initializing collector...")

    # inform core that this collector node is alive
    status_report_thread = threading.Thread(target=reportStatus)
    status_report_thread.daemon = True
    status_report_thread.start()

    register_collector(RSSCollector())
    register_collector(WebCollector())
    register_collector(TwitterCollector())
    register_collector(EmailCollector())
    register_collector(SlackCollector())
    register_collector(AtomCollector())
    register_collector(ManualCollector())
    register_collector(ScheduledTasksCollector())

    logger.log_system_activity_info(__name__, "Collector initialized.")


def register_collector(collector):
    """Register a collector.

    Parameters:
        collector: The collector object to register.
    """
    collectors[collector.type] = collector

    class InitializeThread(threading.Thread):
        """A thread class for initializing the collector."""

        @classmethod
        def run(cls):
            """Run method for the collectors manager.

            Parameters:
                cls: The class object.
            """
            collector.initialize()

    initialize_thread = InitializeThread()
    initialize_thread.start()


def refresh_collector(collector_type):
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
            def run(cls):
                """Run method for the collectors manager.

                Parameters:
                    cls: The class object.
                """
                collectors[collector_type].refresh()

        refresh_thread = RefreshThread()
        refresh_thread.start()
        return 200
    else:
        return 403


def get_registered_collectors_info(id):
    """Retrieve information about registered collectors.

    Parameters:
        id (str): The ID of the collector.
    Returns:
        collectors_info (list): A list of collector information.
    """
    config_file = os.getenv("COLLECTOR_CONFIG_FILE")
    with open(config_file, "w") as file:
        file.write(id)

    collectors_info = []
    for key in collectors:
        collectors_info.append(collectors[key].get_info())

    return collectors_info
