"""Module for Base collector."""

import datetime
import hashlib
import pytz
import socket
import socks
import time
import urllib.request
import uuid
from functools import wraps
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
    Methods:
        __init__(): Initializes the BaseCollector object.
        get_info(): Get information about the collector.
        update_last_attempt(source): Update the last attempt for a collector.
        ignore_exceptions(func): Decorator to wrap scheduled action with exception handling.
        history(interval): Calculate the limit for retrieving historical data based on the given interval.
        filter_by_word_list(news_items, source): Filter news items based on word lists defined in the source.
        sanitize_news_items(news_items, source): Sanitize news items by setting default values for any missing attributes.
        publish(news_items, source): Publish the collected news items to the CoreApi.
        refresh(): Refresh the OSINT sources for the collector.
        get_proxy_handler(source): Get the proxy handler for the collector.
        run_collector(source): Run the collector on the given source.
        initialize(): Initialize the collector.
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
    def ignore_exceptions(func):
        """Wrap scheduled action with exception handling."""

        @wraps(func)
        def wrapper(self, source):
            """Handle exceptions during scheduled collector runs.

            Parameters:
                source: The source of the collector.
            Raises:
                Exception: If an unhandled exception occurs during the collector run.
            """
            try:
                func(self, source)
            except Exception as error:
                logger.exception(f"An unhandled exception occurred during scheduled collector run: {error}")

        return wrapper

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

    @staticmethod
    def publish(news_items, source):
        """Publish the collected news items to the CoreApi.

        Parameters:
            news_items (list): A list of news items to be published.
            source (object): The source object from which the news items were collected.
        """
        source.logger.debug(f"Collected {len(news_items)} news items")
        BaseCollector.sanitize_news_items(news_items, source)
        filtered_news_items = BaseCollector.filter_by_word_list(news_items, source)
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
                    interval = source.param_key_values["REFRESH_INTERVAL"]
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

    @staticmethod
    def get_proxy_handler(parsed_proxy) -> object:
        """Get the proxy handler for the collector.

        Parameters:
            parsed_proxy (urlparse object): The parsed proxy URL.
        Returns:
            (object): The proxy handler for the collector.
        """
        if parsed_proxy.scheme in ["http", "https"]:
            return urllib.request.ProxyHandler(
                {
                    "http": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}",
                    "https": f"{parsed_proxy.scheme}://{parsed_proxy.hostname}:{parsed_proxy.port}",
                }
            )
        elif parsed_proxy.scheme in ["socks4", "socks5"]:
            socks_type = socks.SOCKS5 if parsed_proxy.scheme == "socks5" else socks.SOCKS4
            return SocksiPyHandler(socks_type, parsed_proxy.hostname, int(parsed_proxy.port))

    @staticmethod
    def get_parsed_proxy(proxy_string, log_prefix) -> object:
        """Get the parsed proxy URL for the collector.

        Parameters:
            proxy_string (str): The proxy URL string.
        Returns:
            (urlparse object): The parsed proxy URL for the collector.
        """
        if proxy_string in [None, ""] or proxy_string.lower() == "none":
            return None
        parsed_proxy = urlparse(proxy_string)
        if parsed_proxy.scheme in ["http", "https", "socks4", "socks5"]:
            logger.debug(f"{log_prefix}: Using {parsed_proxy.scheme} proxy: {parsed_proxy.hostname}:{parsed_proxy.port}")
            return parsed_proxy
        else:
            logger.warning(f"{log_prefix}: Invalid proxy server: {proxy_string}. Not using proxy.")
            return None

    @staticmethod
    def not_modified(url, last_collected, log_prefix, opener, user_agent=None) -> bool:
        """Check if the content has been modified since the given date using the If-Modified-Since and Last-Modified headers.

        Arguments:
            url (string): The URL of the content.
            last_collected (datetime): The datetime of the last collection.
            log_prefix (string): The log prefix.
            opener (function): The function to open the URL.
            user_agent (string): The User-Agent string to use for the request (default: None).

        Returns:
            bool: True if the content has not been modified since the given date, False otherwise.
        """
        # Ensure last_collected is offset-aware
        if last_collected.tzinfo is None:
            last_collected = last_collected.replace(tzinfo=pytz.UTC)

        last_collected_str = last_collected.strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {"If-Modified-Since": last_collected_str}
        if user_agent:
            headers["User-Agent"] = user_agent

        request = urllib.request.Request(url, method="HEAD", headers=headers)
        log_prefix += ": Check-if-modified -"

        last_collected_str = last_collected.strftime("%Y-%m-%d %H:%M")
        try:
            with opener(request, timeout=5) as response:
                last_modified = response.headers.get("Last-Modified")
                if response.status == 304:
                    logger.debug(f"{log_prefix} NOT modified since {last_collected_str}")
                    return True
                elif last_modified:
                    last_modified = date_parse(last_modified)
                    last_modified_str = last_modified.strftime("%Y-%m-%d %H:%M")
                    if last_collected >= last_modified:
                        logger.debug(f"{log_prefix} NOT modified since {last_collected_str} (Last-Modified: {last_modified_str})")
                        return True
                    else:
                        logger.debug(f"{log_prefix} YES, modified since {last_collected_str} (Last-Modified: {last_modified_str})")
                        return False
                else:
                    logger.debug(f"{log_prefix} Unable to determine modification since {last_collected_str} (Last-Modified: not received)")
                    return False
        except urllib.error.HTTPError as error:
            if error.code == 304:
                logger.debug(f"{log_prefix} NOT modified since {last_collected_str}")
                return True
            else:
                logger.exception(f"{log_prefix} HTTP error occurred: {error}")
                return False
        except socket.timeout:
            logger.debug(f"{log_prefix} Request timed out for {request.full_url}")
            return False
        except Exception as error:
            logger.exception(f"{log_prefix} An error occurred: {error}")
            return False

    def run_collector(self, source) -> None:
        """Run the collector on the given source.

        Parameters:
            source: The source to collect data from.
        """
        runner = self.__class__()  # get right type of collector
        source.logger.info("Start")
        self.update_last_attempt(source)
        runner.collect(source)
        source.logger.info("End")
        self.update_last_error_message(source)

    def initialize(self):
        """Initialize the collector."""
        self.refresh()
