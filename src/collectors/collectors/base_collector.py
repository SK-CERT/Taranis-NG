"""Module for Base collector."""

import datetime
import hashlib
import uuid
import bleach
import re
import time
from functools import wraps

from managers import time_manager
from managers.log_manager import logger
from remote.core_api import CoreApi
from shared.schema import collector, osint_source, news_item
from shared.schema.parameter import Parameter, ParameterType


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
        presanitize_html(html): Clean and sanitize the given HTML by removing certain tags and entities.
        sanitize_news_items(news_items, source): Sanitize news items by setting default values for any missing attributes.
        publish(news_items, source): Publish the collected news items to the CoreApi.
        refresh(): Refresh the OSINT sources for the collector.
    """

    type = "BASE_COLLECTOR"
    name = "Base Collector"
    description = "Base abstract type for all collectors"

    parameters = [
        Parameter(
            0, "PROXY_SERVER", "Proxy server", "Type SOCKS5 proxy server as username:password@ip:port or ip:port", ParameterType.STRING
        ),
        Parameter(
            0,
            "REFRESH_INTERVAL",
            "Refresh interval in minutes (0 to disable)",
            "How often is this collector queried for new data",
            ParameterType.NUMBER,
        ),
    ]

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
        response, status_code = CoreApi.update_collector_last_attepmt(source.id)
        if status_code != 200:
            logger.critical(f"Update last attempt: HTTP {status_code}, response: {response}")

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
    def presanitize_html(html):
        """Clean and sanitize the given HTML by removing certain tags and entities.

        Parameters:
            html (str): The HTML string to be sanitized.
        Returns:
           clean (str): The sanitized HTML string.
        """
        # these re.sub are not security sensitive ; bleach is supposed to fix the remaining stuff
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        html = re.sub(r"(?i)<head[^>/]*>.*?</head[^>/]*>", "", html, re.DOTALL)
        html = re.sub(r"(?i)<script[^>/]*>.*?</script[^>/]*>", "", html, re.DOTALL)
        html = re.sub(r"(?i)<style[^>/]*>.*?</style[^>/]*>", "", html, re.DOTALL)

        clean = bleach.clean(html, tags=["p", "b", "i", "b", "u", "pre"], strip=True)
        return clean

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
            item.title = BaseCollector.presanitize_html(item.title)
            item.review = BaseCollector.presanitize_html(item.review)
            item.content = BaseCollector.presanitize_html(item.content)
            item.author = BaseCollector.presanitize_html(item.author)
            item.source = BaseCollector.presanitize_html(item.source)  # TODO: replace with link sanitizer
            item.link = BaseCollector.presanitize_html(item.link)  # TODO: replace with link sanitizer

    @staticmethod
    def publish(news_items, source, collector_source):
        """Publish the collected news items to the CoreApi.

        Parameters:
            news_items (list): A list of news items to be published.
            source (object): The source object from which the news items were collected.
            collector_source (string): Collector readbale name
        """
        logger.debug(f"{collector_source} Collected {len(news_items)} news items")
        BaseCollector.sanitize_news_items(news_items, source)
        filtered_news_items = BaseCollector.filter_by_word_list(news_items, source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        CoreApi.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self):
        """Refresh the OSINT sources for the collector."""
        time.sleep(30)
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
        # logger.debug(f"HTTP {code}: Got the following reply: {response}")

        try:
            # if configuration was successfully received
            if code == 200 and response is not None:
                source_schema = osint_source.OSINTSourceSchemaBase(many=True)
                self.osint_sources = source_schema.load(response)

                logger.debug(f"{self.name}: {len(self.osint_sources)} sources loaded")

                # start collection
                for source in self.osint_sources:
                    interval = source.parameter_values["REFRESH_INTERVAL"]
                    # do not schedule if no interval is set
                    if interval == "" or interval == "0":
                        logger.info(f"{self.name} '{source.name}': Disabled")
                        continue

                    self.run_collector(source)

                    # run task every day at XY
                    if interval[0].isdigit() and ":" in interval:
                        logger.debug(f"{self.name} '{source.name}': Scheduling at: {interval}")
                        source.scheduler_job = time_manager.schedule_job_every_day(interval, self.run_collector, source)
                    # run task at a specific day (XY, ZZ:ZZ:ZZ)
                    elif interval[0].isalpha():
                        interval = interval.split(",")
                        day = interval[0].strip()
                        at = interval[1].strip()
                        logger.debug(f"{self.name} '{source.name}': Scheduling at: {day} {at}")
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
                        logger.debug(f"{self.name} '{source.name}': Scheduling for {interval}")
                        source.scheduler_job = time_manager.schedule_job_minutes(int(interval), self.run_collector, source)
            else:
                # TODO: send update to core with the error message
                logger.warning(f"configuration not received, code: {code}, response: {response}")
                pass
        except Exception as error:
            logger.exception(f"Refreshing of sources failed: {error}")
            pass

    def run_collector(self, source):
        """Run the collector on the given source.

        Parameters:
            source: The source to collect data from.
        """
        runner = self.__class__()  # get right type of collector
        runner.collector_source = f"{self.name} '{source.name}':"
        logger.info(f"{runner.collector_source} Starting collector")
        BaseCollector.update_last_attempt(source)
        runner.collect(source)
        logger.info(f"{runner.collector_source} Collection finished")

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
