"""Module for Base collector."""

import datetime
import hashlib
import time
import urllib.request
import uuid
from http import HTTPStatus
from typing import ClassVar
from urllib.parse import urlparse

import pytz
import socks
from dateutil.parser import parse as date_parse
from remote.core_api import CoreApi
from sockshandler import SocksiPyHandler

from shared import common, time_manager
from shared.log_manager import create_logger, logger
from shared.schema import collector, news_item, osint_source

TZ = common.TZ


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
    parameters: ClassVar[list] = []

    def __init__(self) -> None:
        """Initialize the BaseCollector object."""
        self.osint_sources = []

    def get_info(self) -> dict:
        """Get information about the collector.

        Returns:
            (dict): A dictionary containing information about the collector.
        """
        info_schema = collector.CollectorSchema()
        return info_schema.dump(self)

    @staticmethod
    def update_last_attempt(source: object) -> None:
        """Update the last attempt for a collector.

        Args:
            source: The source object representing the collector.
        """
        response, status_code = CoreApi.update_collector_last_attempt(source.id)
        if status_code != HTTPStatus.OK:
            source.logger.error(
                f"Update last attempt failed, Code: {status_code}{', response: ' + str(response) if response is not None else ''}",
            )

    @staticmethod
    def update_last_error_message(source: object) -> None:
        """Update the last error message for a collector.

        Args:
            source: The source object representing the collector.
        """
        response, status_code = CoreApi.update_collector_last_error_message(source.id, source.logger.stored_message)
        if status_code != HTTPStatus.OK:
            source.logger.error(
                f"Update last error message failed, Code: {status_code}{', response: ' + str(response) if response is not None else ''}",
            )

    @staticmethod
    def history(interval: str | int) -> datetime.datetime:
        """Calculate the limit for retrieving historical data based on the given interval.

        Args:
            interval (str or int): The interval for retrieving historical data. It can be a string representing a time unit
              (e.g., '1d' for 1 day, '1w' for 1 week) or an integer representing the number of minutes.

        Returns:
            limit (datetime.datetime): The limit for retrieving historical data.
        """
        minute = 60
        if interval[0].isdigit() and ":" in interval:
            limit = datetime.datetime.now(tz=TZ) - datetime.timedelta(days=1)
        elif interval[0].isalpha():
            limit = datetime.datetime.now(tz=TZ) - datetime.timedelta(weeks=1)
        elif int(interval) > minute:
            hours = int(interval) // minute
            minutes = int(interval) - hours * minute
            limit = datetime.datetime.now(tz=TZ) - datetime.timedelta(days=0, hours=hours, minutes=minutes)
        else:
            limit = datetime.datetime.now(tz=TZ) - datetime.timedelta(days=0, hours=0, minutes=int(interval))

        return limit

    @staticmethod
    def filter_by_word_list(news_items: list, source: object) -> list:
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
            return news_items
        return news_items

    @classmethod
    def sanitize_news_item(cls, news_item: object, source: object) -> object:
        """Sanitize the given news_item by setting default values for any missing attributes.

        Args:
            news_item (object): The news item to be sanitized.
            source: The source of the news item.

        Returns:
            news_item (object): A sanitized news item with default values for missing attributes.
        """
        # Set default values for missing attributes
        defaults = {
            "id": uuid.uuid4(),
            "title": "",
            "review": "",
            "source": "",
            "link": "",
            "author": "",
            "content": "",
            "published": datetime.datetime.now(tz=TZ),
            "collected": datetime.datetime.now(tz=TZ),
            "osint_source_id": source.id,
            "attributes": [],
        }
        for attr, default in defaults.items():
            if getattr(news_item, attr, None) is None:
                setattr(news_item, attr, default)

        if getattr(news_item, "hash", None) is None:
            for_hash = news_item.author + news_item.title + news_item.link
            news_item.hash = hashlib.sha256(for_hash.encode()).hexdigest()

        news_item.title = common.smart_truncate(common.strip_html(news_item.title), 200)
        news_item.review = common.smart_truncate(common.strip_html(news_item.review))
        news_item.content = common.remove_empty_html_tags(common.simplify_html_text(news_item.content))
        news_item.author = common.strip_html(news_item.author)
        return news_item

    def publish(self, news_items: list) -> None:
        """Publish the collected news items to the CoreApi.

        Args:
            news_items (list): A list of news items to be published.
        """
        self.source.logger.debug(f"Collected {len(news_items)} news items")
        filtered_news_items = self.filter_by_word_list(news_items, self.source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        CoreApi.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self) -> None:
        """Refresh the OSINT sources for the collector."""
        logger.debug(f"{self.name}: Awaiting initialization of CORE (timeout: 20s)")
        time.sleep(20)  # wait for the CORE
        logger.info(f"Core API requested a refresh of OSINT sources for {self.name}...")

        time_manager.cancel_all_jobs()
        self.osint_sources = []

        response, code = CoreApi.get_osint_sources(self.type)
        try:
            if code != HTTPStatus.OK or response is None:
                logger.error(f"OSINT sources not received, Code: {code}{', response: ' + str(response) if response is not None else ''}")
                return

            source_schema = osint_source.OSINTSourceSchema(many=True)
            self.osint_sources = source_schema.load(response)
            logger.debug(f"{self.name}: {len(self.osint_sources)} sources loaded")

            for source in self.osint_sources:
                interval = source.param_key_values["REFRESH_INTERVAL"]
                if interval in ["", "0"]:
                    logger.info(f"{self.name} '{getattr(source, 'name', '')}': Disabled")
                    continue
                self._initialize_source(source)
                self.run_collector(source)
                self._schedule_source(source, interval)
        except Exception as error:
            logger.exception(f"Refreshing of sources failed: {error}")

    def _initialize_source(self, source: object) -> None:
        source.last_error_message = None
        source.log_prefix = f"{self.name} '{source.name}'"
        source.logger = create_logger(log_prefix=source.log_prefix)
        source.logger.stored_message_levels = ["error", "exception", "warning", "critical"]

    def _schedule_source(self, source: object, interval: str) -> None:
        # run task every day at XY
        if interval[0].isdigit() and ":" in interval:
            source.logger.debug(f"Scheduling for {interval} daily")
            source.scheduler_job = time_manager.schedule_job_every_day(interval, self.run_collector, source)
            return

        # run task at a specific day (XY, ZZ:ZZ:ZZ)
        if interval[0].isalpha():
            try:
                day, at = [x.strip() for x in interval.split(",", 1)]
            except ValueError:
                source.logger.warning(f"Invalid interval format: {interval}")
                return
            day_map = {
                "Monday": time_manager.schedule_job_on_monday,
                "Tuesday": time_manager.schedule_job_on_tuesday,
                "Wednesday": time_manager.schedule_job_on_wednesday,
                "Thursday": time_manager.schedule_job_on_thursday,
                "Friday": time_manager.schedule_job_on_friday,
                "Saturday": time_manager.schedule_job_on_saturday,
                "Sunday": time_manager.schedule_job_on_sunday,
            }
            schedule_func = day_map.get(day)
            if schedule_func:
                source.logger.debug(f"Scheduling for {day} {at}")
                source.scheduler_job = schedule_func(at, self.run_collector, source)
            else:
                source.logger.warning(f"Unknown day for scheduling: {day}")
            return

        # run task every XY minutes
        try:
            minutes = int(interval)
            source.scheduler_job = time_manager.schedule_job_minutes(minutes, self.run_collector, source)
            source.logger.debug(f"Scheduling for {source.scheduler_job.next_run} (in {interval} minutes)")
        except Exception:
            source.logger.warning(f"Invalid interval value: {interval}")

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
                },
            )
        if self.source.parsed_proxy.scheme in ["socks4", "socks5"]:
            socks_type = socks.SOCKS5 if self.source.parsed_proxy.scheme == "socks5" else socks.SOCKS4
            return SocksiPyHandler(socks_type, self.source.parsed_proxy.hostname, int(self.source.parsed_proxy.port))
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
        self.source.logger.warning(f"Invalid proxy server: {self.source.proxy}. Not using proxy.")
        return None

    def run_collector(self, source: object) -> None:
        """Run the collector on the given source.

        Args:
            source: The source to collect data from.
        """
        runner = self.__class__()  # get right type of collector
        source.logger.info("Start")
        self.update_last_attempt(source)
        runner.source = source
        runner.collect()
        source.logger.info("End")
        self.update_last_error_message(source)

    def initialize(self) -> None:
        """Initialize the collector."""
        self.refresh()


def not_modified(source: object) -> bool:
    """Check if the content has been modified since the given date using the If-Modified-Since and Last-Modified headers."""
    if source.last_collected.tzinfo is None:
        source.last_collected = source.last_collected.replace(tzinfo=pytz.UTC)
    last_collected_str = source.last_collected.strftime("%a, %d %b %Y %H:%M:%S GMT")
    headers = {"If-Modified-Since": last_collected_str}
    if source.user_agent:
        headers["User-Agent"] = source.user_agent
    request = urllib.request.Request(source.url, method="HEAD", headers=headers)  # noqa: S310
    log_prefix = "Check-if-modified:"
    last_collected_str_fmt = source.last_collected.strftime("%Y-%m-%d %H:%M")
    try:
        with source.opener(request, timeout=5) as response:
            return _not_modified_response(source, response, log_prefix, last_collected_str_fmt)
    except urllib.error.HTTPError as http_error:
        return _not_modified_http_error(source, http_error, log_prefix, last_collected_str_fmt)
    except TimeoutError:
        source.logger.debug(f"{log_prefix} Request timed out for {request.full_url}")
        return False
    except Exception:
        source.logger.exception(f"{log_prefix} An error occurred")
        return False


def _not_modified_response(source: object, response: object, log_prefix: str, last_collected_str_fmt: str) -> bool:
    last_modified = response.headers.get("Last-Modified")
    if response.status == HTTPStatus.NOT_MODIFIED:
        source.logger.debug(f"{log_prefix} NOT modified since {last_collected_str_fmt}")
        return True
    if last_modified:
        last_modified_dt = date_parse(last_modified)
        last_modified_str = last_modified_dt.strftime("%Y-%m-%d %H:%M")
        if source.last_collected >= last_modified_dt:
            source.logger.debug(f"{log_prefix} NOT modified since {last_collected_str_fmt} (Last-Modified: {last_modified_str})")
            return True
        source.logger.debug(f"{log_prefix} YES, modified since {last_collected_str_fmt} (Last-Modified: {last_modified_str})")
        return False
    source.logger.debug(f"{log_prefix} Unable to determine modification since {last_collected_str_fmt} (Last-Modified: not received)")
    return False


def _not_modified_http_error(source: object, http_error: object, log_prefix: str, last_collected_str_fmt: str) -> bool:
    if http_error.code == HTTPStatus.NOT_MODIFIED:
        source.logger.debug(f"{log_prefix} NOT modified since {last_collected_str_fmt}")
        return True
    if http_error.code in [401, 429, 403]:
        source.logger.info(f"{log_prefix} HTTP {http_error.code} {http_error.reason} for {source.url}. Continuing...")
        return False
    source.logger.exception(f"{log_prefix} HTTP error occurred")
    return False
