"""Module for Base collector."""

import datetime
import hashlib
import pytz
import socks
import time
import urllib.request
import uuid
from functools import wraps
from sockshandler import SocksiPyHandler
from urllib.parse import urlparse
from dateutil.parser import parse as date_parse
from managers import time_manager
from managers.log_manager import logger
from remote.core_api import CoreApi
from shared import common
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
        publish(news_items, source, collector_source): Publish the collected news items to the CoreApi.
        refresh(): Refresh the OSINT sources for the collector.
        get_proxy_handler(source, collector_source): Get the proxy handler for the collector.
        run_collector(source): Run the collector on the given source.
        initialize(): Initialize the collector.
        read_int_parameter(name, default_value, source): Read an integer parameter from a source dictionary
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
            logger.error(
                f"Update last attempt failed, Code: {status_code}" f"{', response: ' + str(response) if response is not None else ''}"
            )

    @staticmethod
    def update_last_error_message(source):
        """Update the last attempt for a collector.

        Parameters:
            source: The source object representing the collector.
        """
        response, status_code = CoreApi.update_collector_last_error_message(source.id, source.last_error_message)
        if status_code != 200:
            logger.error(
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
        logger.debug(f"Collected {len(news_items)} news items")
        BaseCollector.sanitize_news_items(news_items, source)
        filtered_news_items = BaseCollector.filter_by_word_list(news_items, source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        CoreApi.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self):
        """Refresh the OSINT sources for the collector."""
        time.sleep(20)  # wait for the CORE
        logger.info(f"Core API requested a refresh of OSINT sources for {self.name}...")

        # cancel all existing jobs
        # TODO: cannot cancel jobs that are running and are scheduled for further in time than 60 seconds
        # updating of the configuration needs to be done more gracefully
        for source in self.osint_sources:
            try:
                time_manager.cancel_job(source.scheduler_job)
            except Exception:
                pass
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
                    logger.set_dynamic_target(source)
                    logger.set_module_name(f"{self.name} '{source.name}'")
                    source.last_error_message = None
                    interval = source.parameter_values["REFRESH_INTERVAL"]
                    # do not schedule if no interval is set
                    if interval == "" or interval == "0":
                        logger.info("Disabled")
                        continue

                    self.run_collector(source)

                    # run task every day at XY
                    if interval[0].isdigit() and ":" in interval:
                        logger.debug(f"Scheduling at: {interval}")
                        source.scheduler_job = time_manager.schedule_job_every_day(interval, self.run_collector, source)
                    # run task at a specific day (XY, ZZ:ZZ:ZZ)
                    elif interval[0].isalpha():
                        interval = interval.split(",")
                        day = interval[0].strip()
                        at = interval[1].strip()
                        logger.debug(f"Scheduling at: {day} {at}")
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
                        logger.debug(f"Scheduling for {interval}")
                        source.scheduler_job = time_manager.schedule_job_minutes(int(interval), self.run_collector, source)
            else:
                logger.error(f"OSINT sources not received, Code: {code}" f"{', response: ' + str(response) if response is not None else ''}")
                pass
        except Exception as error:
            logger.exception(f"Refreshing of sources failed: {error}")
            pass

    @staticmethod
    def get_proxy_handler(parsed_proxy) -> object:
        """Get the proxy handler for the collector.

        Parameters:
            parsed_proxy (urlparse object): The parsed proxy URL.
            collector_source (string): Collector readable name
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
    def get_parsed_proxy(proxy_string, collector_source) -> object:
        """Get the parsed proxy URL for the collector.

        Parameters:
            proxy_string (str): The proxy URL string.
            collector_source (string): Collector readable name
        Returns:
            (urlparse object): The parsed proxy URL for the collector.
        """
        if proxy_string in [None, ""] or proxy_string.lower() == "none":
            return None
        parsed_proxy = urlparse(proxy_string)
        if parsed_proxy.scheme in ["http", "https", "socks4", "socks5"]:
            logger.debug(f"Using {parsed_proxy.scheme} proxy: {parsed_proxy.hostname}:{parsed_proxy.port}")
            return parsed_proxy
        else:
            logger.warning(f"Invalid proxy server: {proxy_string}. Not using proxy.")
            return None

    @staticmethod
    def not_modified(collector_source, url, last_collected, opener, user_agent=None) -> bool:
        """Check if the content has been modified since the given date using the If-Modified-Since and Last-Modified headers.

        Arguments:
            url (string): The URL of the content.
            last_collected (datetime): The datetime of the last collection.
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

        last_collected_str = last_collected.strftime("%Y-%m-%d %H:%M")
        try:
            with opener(request) as response:
                last_modified = response.headers.get("Last-Modified")
                if response.status == 304:
                    logger.debug(f"Content has not been modified since {last_collected_str}")
                    return True
                elif last_modified:
                    last_modified = date_parse(last_modified)
                    last_modified_str = last_modified.strftime("%Y-%m-%d %H:%M")
                    if last_collected >= last_modified:
                        logger.debug(f"Content has not been modified since {last_collected_str} " f"(Last-Modified: {last_modified_str})")
                        return True
                    else:
                        logger.debug(f"Content has been modified since {last_collected_str} " f"(Last-Modified: {last_modified_str})")
                        return False
                else:
                    logger.debug(f"Content has been modified since {last_collected_str} " f"(Last-Modified: header not received)")
                    return False
        except urllib.error.HTTPError as e:
            if e.code == 304:
                logger.debug(f"Content has not been modified since {last_collected_str}")
                return True
            else:
                logger.exception(f"HTTP error occurred: {e}")
                return False
        except Exception as e:
            logger.exception(f"An error occurred: {e}")
            return False

    def run_collector(self, source) -> None:
        """Run the collector on the given source.

        Parameters:
            source: The source to collect data from.
        """
        runner = self.__class__()  # get right type of collector
        runner.collector_source = f"{self.name} '{source.name}'"
        logger.set_module_name(runner.collector_source)
        logger.info("Starting collector")
        self.update_last_attempt(source)
        runner.collect(source)
        self.update_last_error_message(source)
        logger.info("Collection finished")

    def initialize(self):
        """Initialize the collector."""
        self.refresh()

    @staticmethod
    def read_int_parameter(name, default_value, source):
        """Read an integer parameter from a source dictionary.

        Parameters:
            name (str): The name of the parameter to read.
            default_value (int): The default value to return if the parameter is not found or is not a valid integer.
            source (dict): The dictionary containing the parameter values.
        Returns:
           val (int): The value of the parameter, or the default value if the parameter is not found or is not a valid integer.
        """
        val = default_value
        try:
            par_val = source.parameter_values[name]
            if par_val != "":
                val = int(par_val)
                if val <= 0:
                    val = default_value
        except Exception as error:
            logger.exception(f"Reading of int parameter failed: {error}")
        return val

    @staticmethod
    def print_news_item(itm):
        """Print news item detials.

        Parameters:
            itm (NewsItemData): News Item object.
        """
        if itm.title:
            logger.debug(f"__ Title    : {itm.title[:100]}")
        if itm.review:
            logger.debug(f"__ Review   : {itm.review[:100]}")
        if itm.content:
            logger.debug(f"__ Content  : {common.clean_whitespace(itm.content)[:100]}")
        if itm.published:
            logger.debug(f"__ Published: {itm.published}")
