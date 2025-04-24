"""RSS collector module."""

import datetime
import feedparser
import hashlib
import urllib.request
import uuid
from bs4 import BeautifulSoup
from .base_collector import BaseCollector
from managers.log_manager import logger
from shared import common
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
        self.log_prefix = f"{self.name} '{source.name}'"

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
                if BaseCollector.not_modified(feed_url, last_collected, opener, user_agent):
                    return None

            logger.debug(f"Fetching feed from URL: {feed_url}")
            return fetch_feed(feed_url, proxy_handler)

        feed_url = source.parameter_values["FEED_URL"]
        if not feed_url:
            logger.error("Feed URL is not set. Skipping collection.")
            BaseCollector.publish([], source)
            return
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)
        last_collected = source.last_collected
        user_agent = source.parameter_values["USER_AGENT"]
        parsed_proxy = BaseCollector.get_parsed_proxy(source.parameter_values["PROXY_SERVER"])
        if parsed_proxy:
            proxy_handler = BaseCollector.get_proxy_handler(parsed_proxy)
        else:
            proxy_handler = None
        opener = urllib.request.build_opener(proxy_handler).open if proxy_handler else urllib.request.urlopen
        if user_agent:
            logger.info(f"Requesting feed URL: {feed_url} (User-Agent: {user_agent})")
        else:
            logger.info(f"Requesting feed URL: {feed_url}")
        feed = get_feed(feed_url, last_collected, user_agent, proxy_handler)
        if feed:
            try:
                logger.debug(f"Feed returned {len(feed['entries'])} entries.")

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
                    content_rss = feed_entry.get("content", "")
                    date = ""
                    review = ""
                    content = ""
                    link_for_article = feed_entry.get("link", "")
                    if summary:
                        review = common.strip_html(summary)
                    if content_rss:
                        content = common.strip_html(content_rss[0].get("value", ""))

                    if not link_for_article:
                        logger.debug(f"Skipping an empty link in feed entry '{title}'.")
                        continue
                    elif not content:
                        logger.info(f"Visiting an article {count}/{len(feed['entries'])}: {link_for_article}")
                        content_html = ""
                        try:
                            request = urllib.request.Request(link_for_article)
                            request.add_header("User-Agent", user_agent)

                            with opener(request) as response:
                                content_html = response.read()

                            if content_html:
                                soup = BeautifulSoup(content_html, features="html.parser")
                                content_html_text = [p.text.strip() for p in soup.findAll("p")]
                                content_sanit = [w.replace("\xa0", " ") for w in content_html_text]
                                content_sanit = " ".join(content_sanit)
                                # use web content if it's longer than summary, if not we use summary in next step
                                if len(content_sanit) > len(summary):
                                    content = content_sanit
                                    logger.debug("Using web text for content")

                        except Exception as error:
                            logger.exception(f"Fetch web content failed: {error}")

                    # use summary if content is empty
                    if summary and not content:
                        content = common.strip_html(summary)
                        logger.debug("Using review for content")
                    # use first 500 characters of content if summary is empty
                    elif not summary and content:
                        review = content
                        logger.debug("Using first 500 characters of content for review")

                    title = common.smart_truncate(title, 200)
                    review = common.smart_truncate(review)

                    # use published date if available, otherwise use updated date
                    if published_parsed:
                        date = datetime.datetime(*published_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                        logger.debug("Using parsed 'published' date")
                    elif updated_parsed:
                        date = datetime.datetime(*updated_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                        logger.debug("Using parsed 'updated' date")
                    elif published:
                        date = published
                        logger.debug("Using 'published' date")
                    elif updated:
                        date = updated
                        logger.debug("Using 'updated' date")

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
                        content,
                        source.id,
                        [],
                    )

                    BaseCollector.print_news_item(news_item)
                    news_items.append(news_item)

                    if count >= links_limit & links_limit > 0:
                        logger.debug(f"Limit for article links ({links_limit}) has been reached.")
                        break

                BaseCollector.publish(news_items, source)

            except Exception as error:
                logger.exception(f"Collection failed: {error}")

        else:
            logger.info("Will not collect the feed because nothing has changed.")
            BaseCollector.publish([], source)
