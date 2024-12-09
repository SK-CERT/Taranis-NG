"""Module for Atom collector."""

import datetime
import hashlib
import uuid
import feedparser
import requests
from bs4 import BeautifulSoup

from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData


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
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters
    news_items = []

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from Atom feed.

        Parameters:
            source -- Source object.
        """
        feed_url = source.parameter_values["ATOM_FEED_URL"]
        user_agent = source.parameter_values["USER_AGENT"]
        interval = source.parameter_values["REFRESH_INTERVAL"]  # noqa: F841
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)

        logger.info(f"{self.collector_source} Requesting feed URL {feed_url}")

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

            logger.debug(f"{self.collector_source} Atom returned feed with {len(feed['entries'])} entries")

            news_items = []

            count = 0
            for feed_entry in feed["entries"]:
                count += 1
                link_for_article = feed_entry["link"]
                logger.info(f"{self.collector_source} Visiting article {count}/{len(feed['entries'])}: {link_for_article}")
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
                    logger.debug(f"{self.collector_source} Limit for article links reached ({links_limit})")
                    break

            BaseCollector.publish(news_items, source, self.collector_source)

        except Exception as error:
            logger.exception(f"{self.collector_source} Collection failed: {error}")
