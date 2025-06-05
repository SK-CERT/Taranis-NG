"""Module for Base collector."""

import datetime
import hashlib
import pytz
import socket
import socks
import time
import urllib.request
import uuid
from sockshandler import SocksiPyHandler
from urllib.parse import urlparse
from dateutil.parser import parse as date_parse
from shared.log_manager import logger, create_logger
from remote.core_api import CoreApi
from shared import common, time_manager
from shared.schema import collector, osint_source, news_item


class BaseCollector:
    """Base abstract type for all collectors.

    Attributes:
        type (str): The type of the collector.
        name (str): The name of the collector.
        description (str): The description of the collector.
        parameters (list): A list of parameters for the collector.
    """

    type = "BASE_COLLECTOR"
    name = "Base Collector"
    description = "Base abstract type for all collectors"
    parameters = []

    def __init__(self):
        """Initialize the BaseCollector object."""
        self.osint_sources = []

    def get_info(self):
        """Get information about the collector.

        Returns:
            (dict): A dictionary containing information about the collector.
        """
        info_schema = collector.CollectorSchema()
        return info_schema.dump(self)

    @staticmethod
    def update_last_attempt(source):
        """Update the last attempt for a collector.

        Parameters:
            source: The source object representing the collector.
        """
        response, status_code = CoreApi.update_collector_last_attempt(source.id)
        if status_code != 200:
            source.logger.error(
                f"Update last attempt failed, Code: {status_code}" f"{', response: ' + str(response) if response is not None else ''}"
            )

    @staticmethod
    def update_last_error_message(source):
        """Update the last error message for a collector.

        Parameters:
            source: The source object representing the collector.
        """
        response, status_code = CoreApi.update_collector_last_error_message(source.id, source.logger.stored_message)
        if status_code != 200:
            source.logger.error(
                f"Update last error message failed, Code: {status_code}" f"{', response: ' + str(response) if response is not None else ''}"
            )

    @staticmethod
    def history(interval):
        """Calculate the limit for retrieving historical data based on the given interval.

        Parameters:
            interval (str or int): The interval for retrieving historical data. It can be a string representing a time unit
              (e.g., '1d' for 1 day, '1w' for 1 week) or an integer representing the number of minutes.
        Returns:
            limit (datetime.datetime): The limit for retrieving historical data.
        """
        if interval[0].isdigit() and ":" in interval:
            limit = datetime.datetime.now() - datetime.timedelta(days=1)
        elif interval[0].isalpha():
            limit = datetime.datetime.now() - datetime.timedelta(weeks=1)
        else:
            if int(interval) > 60:
                hours = int(interval) // 60
                minutes = int(interval) - hours * 60
                limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)
            else:
                limit = datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))

        return limit

    @staticmethod
    def filter_by_word_list(news_items, source):
        """Filter the given news_items based on the word lists defined in the source.

        Parameters:
            news_items (list): A list of news items to be filtered.
            source (object): The source object containing word lists.
        Returns:
            news_items (list): A filtered list of news items based on the word lists. If no word lists are defined,
              the original list is returned.
        """
        if source.word_lists:
            one_word_list = set()

            for word_list in source.word_lists:
                if word_list.use_for_stop_words is False:
                    for category in word_list.categories:
                        for entry in category.entries:
                            one_word_list.add(entry.value.lower())

            filtered_news_items = []
            if one_word_list:
                for item in news_items:
                    for word in one_word_list:
                        if word in item.title.lower() or word in item.review.lower() or word in item.content.lower():
                            filtered_news_items.append(item)
                            break

                return filtered_news_items
            else:
                return news_items
        else:
            return news_items

    @staticmethod
    def sanitize_news_items(news_items, source):
        """Sanitize the given news_items by setting default values for any missing attributes.

        Parameters:
            news_items (list): A list of news items to be sanitized.
            source: The source of the news items.
        """
        for item in news_items:
            if item.id is None:
                item.id = uuid.uuid4()
            if item.title is None:
                item.title = ""
            if item.review is None:
                item.review = ""
            if item.source is None:
                item.source = ""
            if item.link is None:
                item.link = ""
            if item.author is None:
                item.author = ""
            if item.content is None:
                item.content = ""
            if item.published is None:
                item.published = datetime.datetime.now()
            if item.collected is None:
                item.collected = datetime.datetime.now()
            if item.hash is None:
                for_hash = item.author + item.title + item.link
                item.hash = hashlib.sha256(for_hash.encode()).hexdigest()
            if item.osint_source_id is None:
                item.osint_source_id = source.id
            if item.attributes is None:
                item.attributes = []
            item.title = common.strip_html(item.title)
            item.review = common.strip_html(item.review)
            item.content = common.strip_html(item.content)
            item.author = common.strip_html(item.author)

    def publish(self, news_items):
        """Publish the collected news items to the CoreApi.

        Parameters:
            news_items (list): A list of news items to be published.
        """
        self.source.logger.debug(f"Collected {len(news_items)} news items")
        self.sanitize_news_items(news_items, self.source)
        filtered_news_items = self.filter_by_word_list(news_items, self.source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        CoreApi.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self):
        """Refresh the OSINT sources for the collector."""
        logger.debug(f"{self.name}: Awaiting initialization of CORE (timeout: 20s)")
        time.sleep(20)  # wait for the CORE
        logger.info(f"Core API requested a refresh of OSINT sources for {self.name}...")

        time_manager.cancel_all_jobs()
        self.osint_sources = []

        # get new node configuration
        response, code = CoreApi.get_osint_sources(self.type)
        try:
            # if configuration was successfully received
            if code == 200 and response is not None:
                source_schema = osint_source.OSINTSourceSchema(many=True)
                self.osint_sources = source_schema.load(response)

                logger.debug(f"{self.name}: {len(self.osint_sources)} sources loaded")

                # start collection
                for source in self.osint_sources:
                    source.last_error_message = None
                    source.log_prefix = f"{self.name} '{source.name}'"
                    source.logger = create_logger(log_prefix=source.log_prefix)
                    source.logger.stored_message_levels = ["error", "exception", "warning", "critical"]
                    interval = source.parameter_values["REFRESH_INTERVAL"]
                    # do not schedule if no interval is set
                    if interval == "" or interval == "0":
                        source.logger.info("Disabled")
                        continue

                    self.run_collector(source)

                    # run task every day at XY
                    if interval[0].isdigit() and ":" in interval:
                        source.logger.debug(f"Scheduling for {interval} daily")
                        source.scheduler_job = time_manager.schedule_job_every_day(interval, self.run_collector, source)
                    # run task at a specific day (XY, ZZ:ZZ:ZZ)
                    elif interval[0].isalpha():
                        interval = interval.split(",")
                        day = interval[0].strip()
                        at = interval[1].strip()
                        source.logger.debug(f"Scheduling for {day} {at}")
                        if day == "Monday":
                            source.scheduler_job = time_manager.schedule_job_on_monday(at, self.run_collector, source)
                        elif day == "Tuesday":
                            source.scheduler_job = time_manager.schedule_job_on_tuesday(at, self.run_collector, source)
                        elif day == "Wednesday":
                            source.scheduler_job = time_manager.schedule_job_on_wednesday(at, self.run_collector, source)
                        elif day == "Thursday":
                            source.scheduler_job = time_manager.schedule_job_on_thursday(at, self.run_collector, source)
                        elif day == "Friday":
                            source.scheduler_job = time_manager.schedule_job_on_friday(at, self.run_collector, source)
                        elif day == "Saturday":
                            source.scheduler_job = time_manager.schedule_job_on_saturday(at, self.run_collector, source)
                        elif day == "Sunday":
                            source.scheduler_job = time_manager.schedule_job_on_sunday(at, self.run_collector, source)
                    # run task every XY minutes
                    else:
                        source.scheduler_job = time_manager.schedule_job_minutes(int(interval), self.run_collector, source)
                        source.logger.debug(f"Scheduling for {source.scheduler_job.next_run} (in {interval} minutes)")
            else:
                logger.error(f"OSINT sources not received, Code: {code}" f"{', response: ' + str(response) if response is not None else ''}")

        except Exception as error:
            logger.exception(f"Refreshing of sources failed: {error}")

    def get_proxy_handler(self) -> object:
        """Get the proxy handler for the collector.

        Returns:
            (object): The proxy handler for the collector.
        """
        if self.source.parsed_proxy.scheme in ["http", "https"]:
            return urllib.request.ProxyHandler(
                {
                    "http": f"{self.source.parsed_proxy.scheme}://{self.source.parsed_proxy.hostname}:{self.source.parsed_proxy.port}",
                    "https": f"{self.source.parsed_proxy.scheme}://{self.source.parsed_proxy.hostname}:{self.source.parsed_proxy.port}",
                }
            )
        elif self.source.parsed_proxy.scheme in ["socks4", "socks5"]:
            socks_type = socks.SOCKS5 if self.source.parsed_proxy.scheme == "socks5" else socks.SOCKS4
            return SocksiPyHandler(socks_type, self.source.parsed_proxy.hostname, int(self.source.parsed_proxy.port))
        else:
            self.source.logger.warning(f"Invalid proxy server: {self.source.proxy}. Not using proxy.")
            return None

    def get_parsed_proxy(self) -> object:
        """Get the parsed proxy URL for the collector.

        Returns:
            (urlparse object): The parsed proxy URL for the collector.
        """
        if self.source.proxy in [None, ""] or self.source.proxy.lower() == "none":
            return None
        parsed_proxy = urlparse(self.source.proxy)
        if parsed_proxy.scheme in ["http", "https", "socks4", "socks5"]:
            self.source.logger.debug(f"Using {parsed_proxy.scheme} proxy: {parsed_proxy.hostname}:{parsed_proxy.port}")
            return parsed_proxy
        else:
            self.source.logger.warning(f"Invalid proxy server: {self.source.proxy}. Not using proxy.")
            return None

    def run_collector(self, source) -> None:
        """Run the collector on the given source.

        Parameters:
            source: The source to collect data from.
        """
        runner = self.__class__()  # get right type of collector
        source.logger.info("Start")
        self.update_last_attempt(source)
        runner.source = source
        runner.collect()
        source.logger.info("End")
        self.update_last_error_message(source)

    def initialize(self):
        """Initialize the collector."""
        self.refresh()


def not_modified(source) -> bool:
    """Check if the content has been modified since the given date using the If-Modified-Since and Last-Modified headers.

    Parameters:
        source (object): The source object for logging.

    Returns:
        bool: True if the content has not been modified since the given date, False otherwise.
    """
    # Ensure last_collected is offset-aware
    if source.last_collected.tzinfo is None:
        source.last_collected = source.last_collected.replace(tzinfo=pytz.UTC)

    last_collected_str = source.last_collected.strftime("%a, %d %b %Y %H:%M:%S GMT")
    headers = {"If-Modified-Since": last_collected_str}
    if source.user_agent:
        headers["User-Agent"] = source.user_agent

    request = urllib.request.Request(source.url, method="HEAD", headers=headers)
    log_prefix = "Check-if-modified:"

    last_collected_str = source.last_collected.strftime("%Y-%m-%d %H:%M")
    try:
        with source.opener(request, timeout=5) as response:
            last_modified = response.headers.get("Last-Modified")
            if response.status == 304:
                source.logger.debug(f"{log_prefix} NOT modified since {last_collected_str}")
                return True
            elif last_modified:
                last_modified = date_parse(last_modified)
                last_modified_str = last_modified.strftime("%Y-%m-%d %H:%M")
                if source.last_collected >= last_modified:
                    source.logger.debug(f"{log_prefix} NOT modified since {last_collected_str} (Last-Modified: {last_modified_str})")
                    return True
                else:
                    source.logger.debug(f"{log_prefix} YES, modified since {last_collected_str} (Last-Modified: {last_modified_str})")
                    return False
            else:
                source.logger.debug(f"{log_prefix} Unable to determine modification since {last_collected_str} (Last-Modified: not received)")
                return False
    except urllib.error.HTTPError as error:
        if error.code == 304:
            source.logger.debug(f"{log_prefix} NOT modified since {last_collected_str}")
            return True
        else:
            source.logger.exception(f"{log_prefix} HTTP error occurred: {error}")
            return False
    except socket.timeout:
        source.logger.debug(f"{log_prefix} Request timed out for {request.full_url}")
        return False
    except Exception as error:
        source.logger.exception(f"{log_prefix} An error occurred: {error}")
        return False
