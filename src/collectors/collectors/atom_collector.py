"""Module for Atom collector."""

import datetime
import hashlib
import uuid
import traceback
import feedparser
import requests
from bs4 import BeautifulSoup

from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.schema.news_item import NewsItemData
from shared.schema.parameter import Parameter, ParameterType


class AtomCollector(BaseCollector):
    """Collector for gathering data from Atom.

    Attributes:
        type (str): Type of the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (list): List of parameters required for the collector.
    Methods:
        collect(source): Collect data from an Atom feed.

    Raises:
        Exception: If an error occurs during the collection process.
    """

    type = "ATOM_COLLECTOR"
    name = "Atom Collector"
    description = "Collector for gathering data from Atom feeds"

    parameters = [
        Parameter(0, "ATOM_FEED_URL", "Atom feed URL", "Full url for Atom feed", ParameterType.STRING),
        Parameter(0, "USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING),
        Parameter(
            0,
            "LINKS_LIMIT",
            "Limit for article links",
            "OPTIONAL: Maximum number of article links to process. Default: all",
            ParameterType.NUMBER,
        ),
    ]

    parameters.extend(BaseCollector.parameters)

    news_items = []

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from Atom feed.

        Parameters:
            source -- Source object.
        """
        BaseCollector.update_last_attempt(source)
        feed_url = source.parameter_values["ATOM_FEED_URL"]
        user_agent = source.parameter_values["USER_AGENT"]
        interval = source.parameter_values["REFRESH_INTERVAL"]  # noqa: F841
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)

        logger.log_collector_activity_info("atom", source.name, f"Starting collector for URL: {feed_url}")

        proxies = {}
        if "PROXY_SERVER" in source.parameter_values:
            proxy_server = source.parameter_values["PROXY_SERVER"]
            if proxy_server.startswith("https://"):
                proxies["https"] = proxy_server
            elif proxy_server.startswith("http://"):
                proxies["http"] = proxy_server
            else:
                proxies["http"] = "http://" + proxy_server

        try:
            if proxies:
                atom_xml = requests.get(feed_url, headers={"User-Agent": user_agent}, proxies=proxies)
                feed = feedparser.parse(atom_xml.text)
            else:
                feed = feedparser.parse(feed_url)

            logger.log_collector_activity_info("atom", source.name, f"Atom returned feed with {len(feed['entries'])} entries")

            news_items = []

            count = 0
            for feed_entry in feed["entries"]:
                count += 1
                link_for_article = feed_entry["link"]
                logger.log_collector_activity_info(
                    "atom", source.name, f"Visiting article {count}/{len(feed['entries'])}: {link_for_article}"
                )
                if proxies:
                    page = requests.get(link_for_article, headers={"User-Agent": user_agent}, proxies=proxies)
                else:
                    page = requests.get(link_for_article, headers={"User-Agent": user_agent})

                html_content = page.text

                if html_content:
                    content = BeautifulSoup(html_content, features="html.parser").text
                else:
                    content = ""

                description = feed_entry["summary"][:500].replace("<p>", " ")

                # author can exist/miss in header/entry
                author = feed_entry["author"] if "author" in feed_entry else ""
                for_hash = author + feed_entry["title"] + feed_entry["link"]

                news_item = NewsItemData(
                    uuid.uuid4(),
                    hashlib.sha256(for_hash.encode()).hexdigest(),
                    feed_entry["title"],
                    description,
                    feed_url,
                    feed_entry["link"],
                    feed_entry["updated"],
                    author,
                    datetime.datetime.now(),
                    content,
                    source.id,
                    [],
                )

                news_items.append(news_item)

                if count >= links_limit & links_limit > 0:
                    logger.log_collector_activity_info("atom", source.name, f"Limit for article links reached ({links_limit})")
                    break

            BaseCollector.publish(news_items, source)

        except Exception as error:
            logger.log_collector_activity_info("atom", source.name, "Atom collection exceptionally failed")
            BaseCollector.print_exception(source, error)
            logger.log_debug(traceback.format_exc())

        logger.log_debug(f"{self.type} collection finished.")
