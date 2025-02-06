"""RSS collector module."""

import datetime
import feedparser
import hashlib
import pytz
import urllib.request
import uuid
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse

from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData


class RSSCollector(BaseCollector):
    """RSS collector class.

    Arguments:
        BaseCollector -- Base collector class.
    """

    type = "RSS_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    news_items = []

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from RSS or Atom feed.

        Arguments:
            source: Source object.
        """

        def strip_html_tags(html_string):
            """Strip HTML tags from the given string.

            Arguments:
                html_string (string): The HTML string.

            Returns:
                string: The string without HTML tags.
            """
            soup = BeautifulSoup(html_string, "html.parser")
            return soup.get_text(separator=" ", strip=True)

        def not_modified(url, last_collected, opener, user_agent=None):
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

            try:
                with opener(request) as response:
                    last_modified = response.headers.get("Last-Modified")
                    if response.status == 304:
                        logger.debug(f"{self.collector_source} Content has not been modified since {last_collected}")
                        return True
                    elif last_modified:
                        last_modified = date_parse(last_modified)
                        if last_collected >= last_modified:
                            logger.debug(
                                f"{self.collector_source} Content has not been modified since {last_collected} "
                                f"(Last-Modified: {last_modified})"
                            )
                            return True
                        else:
                            logger.debug(
                                f"{self.collector_source} Content has been modified since {last_collected} (Last-Modified: {last_modified})"
                            )
                            return False
                    else:
                        logger.debug(
                            f"{self.collector_source} Content has been modified since {last_collected} (Last-Modified header not received)"
                        )
                        return False
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    logger.debug(f"{self.collector_source} Content has not been modified since {last_collected}")
                    return True
                else:
                    logger.exception(f"{self.collector_source} HTTP error occurred: {e}")
                    return False
            except Exception as e:
                logger.exception(f"{self.collector_source} An error occurred: {e}")
                return False

        def get_feed(feed_url, last_collected=None, user_agent=None, proxy_handler=None):
            """Fetch the feed data, using proxy if provided, and check modification status.

            Arguments:
                feed_url (string): The URL of the feed.
                last_collected (string): The datetime of the last collection.
                proxy_handler (SocksiPyHandler): The proxy handler to use for the request (default: None).

            Returns:
                dict: The parsed feed data or an empty dictionary if not modified.
            """

            def fetch_feed(url, handler=None):
                """Fetch the feed using feedparser with optional handler."""
                if user_agent:
                    feedparser.USER_AGENT = user_agent
                if handler:
                    return feedparser.parse(url, handlers=[handler])
                return feedparser.parse(url)

            # Determine the opener function based on the proxy handler
            opener = urllib.request.build_opener(proxy_handler).open if proxy_handler else urllib.request.urlopen

            # Check if the feed has been modified since the last collection
            if last_collected:
                if not_modified(feed_url, last_collected, opener, user_agent):
                    return None

            logger.debug(f"{self.collector_source} Fetching feed from URL: {feed_url}")
            return fetch_feed(feed_url, proxy_handler)

        feed_url = source.parameter_values["FEED_URL"]
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)
        last_collected = source.last_collected
        user_agent = source.parameter_values["USER_AGENT"]
        proxy_handler = BaseCollector.get_proxy_handler(source, self.collector_source)
        opener = urllib.request.build_opener(proxy_handler).open if proxy_handler else urllib.request.urlopen
        if user_agent:
            logger.info(f"{self.collector_source} Requesting feed URL: {feed_url} (User-Agent: {user_agent})")
        else:
            logger.info(f"{self.collector_source} Requesting feed URL: {feed_url}")
        feed = get_feed(feed_url, last_collected, user_agent, proxy_handler)
        if feed:
            try:
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
                        logger.info(f"{self.collector_source} Visiting an article {count}/{len(feed['entries'])}: {link_for_article}")
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
                            logger.exception(f"{self.collector_source} Fetch article failed: {error}")

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
                        logger.debug(f"{self.collector_source} Using parsed 'published' date")
                    elif updated_parsed:
                        date = datetime.datetime(*updated_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                        logger.debug(f"{self.collector_source} Using parsed 'updated' date")
                    elif published:
                        date = published
                        logger.debug(f"{self.collector_source} Using 'published' date")
                    elif updated:
                        date = updated
                        logger.debug(f"{self.collector_source} Using 'updated' date")

                    logger.debug(f"{self.collector_source} ... Title    : {title}")
                    logger.debug(f"{self.collector_source} ... Review   : {review.replace('\r', '').replace('\n', ' ').strip()[:100]}")
                    logger.debug(f"{self.collector_source} ... Content  : {article.replace('\r', '').replace('\n', ' ').strip()[:100]}")
                    logger.debug(f"{self.collector_source} ... Published: {date}")

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
                        logger.debug(f"{self.collector_source} Limit for article links ({links_limit}) has been reached.")
                        break

                BaseCollector.publish(news_items, source, self.collector_source)

            except Exception as error:
                logger.exception(f"{self.collector_source} Collection failed: {error}")

        else:
            logger.info(f"{self.collector_source} Will not collect the feed because nothing has changed.")
            BaseCollector.publish([], source, self.collector_source)
