"""RSS collector module."""

import datetime
import hashlib
import uuid
import re
import socks
import feedparser
import urllib.request
from sockshandler import SocksiPyHandler
from bs4 import BeautifulSoup

from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.schema.news_item import NewsItemData
from shared.schema.parameter import Parameter, ParameterType


class RSSCollector(BaseCollector):
    """RSS collector class.

    Arguments:
        BaseCollector -- Base collector class.
    """

    type = "RSS_COLLECTOR"
    name = "RSS Collector"
    description = "Collector for gathering data from RSS and Atom feeds"

    parameters = [
        Parameter(0, "FEED_URL", "Feed URL", "Full URL for RSS or Atom feed", ParameterType.STRING),
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
        """Collect data from RSS or Atom feed.

        Arguments:
            source -- Source object.
        """
        self.collector_source = f"{self.name} '{source.name}':"

        def strip_html_tags(html_string):
            soup = BeautifulSoup(html_string, "html.parser")
            return soup.get_text(separator=" ", strip=True)

        BaseCollector.update_last_attempt(source)
        feed_url = source.parameter_values["FEED_URL"]
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)

        logger.info(f"{self.collector_source} Starting collector for URL: {feed_url}")

        user_agent = source.parameter_values["USER_AGENT"]
        if user_agent:
            logger.debug(f"{self.collector_source} Using user agent: {user_agent}")
            feedparser.USER_AGENT = user_agent

        # use system proxy
        proxy_handler = None
        opener = urllib.request.urlopen

        if "PROXY_SERVER" in source.parameter_values:
            proxy_server = source.parameter_values["PROXY_SERVER"]

            # disable proxy - do not use system proxy
            if proxy_server == "none":  # WTF?
                proxy_handler = urllib.request.ProxyHandler({})
            else:
                proxy = re.search(r"^(http|https|socks4|socks5|ftp)://([a-zA-Z0-9\-\.\_]+):(\d+)/?$", proxy_server)
                if proxy:
                    scheme, host, port = proxy.groups()
                    if scheme in ["http", "https", "ftp"]:
                        logger.debug(f"{self.collector_source} Using {scheme} proxy: {host}:{port}")
                        proxy_handler = urllib.request.ProxyHandler(
                            {
                                "http": f"{scheme}://{host}:{port}",
                                "https": f"{scheme}://{host}:{port}",
                                "ftp": f"{scheme}://{host}:{port}",
                            }
                        )
                    elif scheme == "socks4":
                        logger.debug(f"{self.collector_source} Using socks4 proxy: {host}:{port}")
                        proxy_handler = SocksiPyHandler(socks.SOCKS4, host, int(port))
                    elif scheme == "socks5":
                        logger.debug(f"{self.collector_source} Using socks5 proxy: {host}:{port}")
                        proxy_handler = SocksiPyHandler(socks.SOCKS5, host, int(port))

        # use proxy in urllib
        if proxy_handler:
            opener = urllib.request.build_opener(proxy_handler).open

        try:
            if proxy_handler:
                logger.debug(f"{self.collector_source} Using proxy for feed collection: {proxy_server}")
                feed = feedparser.parse(feed_url, handlers=[proxy_handler])
            else:
                feed = feedparser.parse(feed_url)

            logger.debug(f"{self.collector_source} Feed returned {len(feed['entries'])} entries.")

            news_items = []

            count = 0
            for feed_entry in feed["entries"]:
                count += 1
                author = feed_entry.get("author", "")
                title = feed_entry.get("title", "")
                published = feed_entry.get("published", "")
                published_parsed = feed_entry.get("published_parsed", "")
                updated = feed_entry.get("updated", "")
                updated_parsed = feed_entry.get("updated_parsed", "")
                summary = feed_entry.get("summary", "")
                content = feed_entry.get("content", "")
                date = ""
                review = ""
                article = ""
                link_for_article = feed_entry.get("link", "")
                if summary:
                    review = strip_html_tags(summary[:500])
                if content:
                    article = strip_html_tags(content[0].get("value", ""))

                if not link_for_article:
                    logger.debug(f"{self.collector_source} Skipping an empty link in feed entry '{title}'.")
                    continue
                elif not article:
                    logger.debug(f"{self.collector_source} Visiting an article {count}/{len(feed['entries'])}: {link_for_article}")
                    html_article = ""
                    try:
                        request = urllib.request.Request(link_for_article)
                        request.add_header("User-Agent", user_agent)

                        with opener(request) as response:
                            html_article = response.read()

                        soup = BeautifulSoup(html_article, features="html.parser")

                        if html_article:
                            article_text = [p.text.strip() for p in soup.findAll("p")]
                            replaced_str = "\xa0"
                            article_sanit = [w.replace(replaced_str, " ") for w in article_text]
                            article_sanit = " ".join(article_sanit)
                            # use HTML article if it is longer than summary
                            if len(article_sanit) > len(summary):
                                article = article_sanit
                            logger.debug(f"{self.collector_source} Got an article: {link_for_article}")
                    except Exception as error:
                        logger.exception(f"{self.collector_source} Failed to fetch article: {error}")

                # use summary if article is empty
                if summary and not article:
                    article = strip_html_tags(summary)
                    logger.debug(f"{self.collector_source} Using summary for article: {article}")
                # use first 500 characters of article if summary is empty
                elif not summary and article:
                    review = article[:500]
                    logger.debug(f"{self.collector_source} Using first 500 characters of article for summary: {review}")

                # use published date if available, otherwise use updated date
                if published_parsed:
                    date = datetime.datetime(*published_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                    logger.debug(f"{self.collector_source} Using parsed 'published' date: {date}")
                elif updated_parsed:
                    date = datetime.datetime(*updated_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                    logger.debug(f"{self.collector_source} Using parsed 'updated' date: {date}")
                elif published:
                    date = published
                    logger.debug(f"{self.collector_source} Using 'published' date: {date}")
                elif updated:
                    date = updated
                    logger.debug(f"{self.collector_source} Using 'updated' date: {date}")

                for_hash = author + title + link_for_article

                news_item = NewsItemData(
                    uuid.uuid4(),
                    hashlib.sha256(for_hash.encode()).hexdigest(),
                    title,
                    review,
                    feed_url,
                    link_for_article,
                    date,
                    author,
                    datetime.datetime.now(),
                    article,
                    source.id,
                    [],
                )

                news_items.append(news_item)

                if count >= links_limit & links_limit > 0:
                    logger.info(f"{self.collector_source} Limit for article links ({links_limit}) has been reached.")
                    break

            BaseCollector.publish(news_items, source)

        except Exception as error:
            logger.exception(f"{self.collector_source} RSS collection exceptionally failed: {error}")

        logger.info(f"{self.collector_source} Collection finished.")
