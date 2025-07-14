"""RSS collector module."""

import datetime
import feedparser
import hashlib
import urllib.request
import uuid
from bs4 import BeautifulSoup
from .base_collector import BaseCollector, not_modified
from shared.common import ignore_exceptions, read_int_parameter
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData


class RSSCollector(BaseCollector):
    """RSS collector class.

    Arguments:
        BaseCollector: Base collector class.
    """

    type = "RSS_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    news_items = []

    def __get_opener(self):
        """Get the opener function for URL requests.

        Arguments:
            proxy_handler (SocksiPyHandler): The proxy handler to use for the request (default: None).
        Returns:
            function: The opener function to use for URL requests.
        """
        if self.source.proxy_handler:
            return urllib.request.build_opener(self.source.proxy_handler).open
        return urllib.request.urlopen

    def __fetch_feed(self):
        """Fetch the feed using feedparser with optional handler."""
        if self.source.user_agent:
            feedparser.USER_AGENT = self.source.user_agent
        try:
            if self.source.proxy_handler:
                return feedparser.parse(self.source.url, handlers=[self.source.proxy_handler])
            return feedparser.parse(self.source.url)
        except Exception as error:
            self.source.logger.exception(f"Fetch feed failed: {error}")
            return None

    def __get_feed(self):
        """Fetch the feed data, using proxy if provided, and check modification status.

        Returns:
            dict: The parsed feed data or an empty dictionary if not modified.
        """
        # Check if the feed has been modified since the last collection
        if self.source.last_collected:
            if not_modified(self.source):
                return None

        self.source.logger.debug(f"Fetching feed from URL: {self.source.url}")
        return self.__fetch_feed()

    @ignore_exceptions
    def collect(self):
        """Collect data from RSS or Atom feed."""
        self.source.url = self.source.param_key_values["FEED_URL"]
        if not self.source.url:
            self.source.logger.error("Feed URL is not set. Skipping collection.")

            return
        links_limit = read_int_parameter("LINKS_LIMIT", 0, self.source)
        self.source.user_agent = self.source.param_key_values["USER_AGENT"]
        self.source.proxy = self.source.param_key_values["PROXY_SERVER"]
        self.source.parsed_proxy = self.get_parsed_proxy()
        if self.source.parsed_proxy:
            self.source.proxy_handler = self.get_proxy_handler()
        else:
            self.source.proxy_handler = None
        self.source.opener = self.__get_opener()
        if self.source.user_agent:
            self.source.logger.info(f"Requesting feed URL: {self.source.url} (User-Agent: {self.source.user_agent})")
        else:
            self.source.logger.info(f"Requesting feed URL: {self.source.url}")
        feed = self.__get_feed()
        if feed:
            try:
                self.source.logger.debug(f"Feed returned {len(feed['entries'])} entries.")

                news_items = []

                for count, feed_entry in enumerate(feed["entries"], 1):
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
                        review = summary
                    if content_rss:
                        content = content_rss[0].get("value", "")

                    if not link_for_article:
                        self.source.logger.debug(f"Skipping an empty link in feed entry '{title}'.")
                        continue
                    elif not content:
                        self.source.logger.info(f"Visiting an article {count}/{len(feed['entries'])}: {link_for_article}")
                        content_with_newlines = ""
                        try:
                            request = urllib.request.Request(link_for_article)
                            request.add_header("User-Agent", self.source.user_agent)

                            with self.source.opener(request) as response:
                                content_html = response.read()
                            if content_html:
                                soup = BeautifulSoup(content_html, features="html.parser")
                                # get all <p> tags text in body
                                content_html_text = [p.get_text(strip=True) for p in soup.find_all("p")]
                                content_with_newlines = "\n".join(content_html_text)
                            if len(content_with_newlines) > len(summary):
                                content = content_with_newlines
                                self.source.logger.debug("Using web text for content")
                        except urllib.error.HTTPError as http_err:
                            if http_err.code in [401, 429, 403]:
                                self.source.logger.warning(
                                    f"HTTP {http_err.code} {http_err.reason} for {link_for_article}. Skipping getting article content."
                                )
                            else:
                                self.source.logger.exception(f"{http_err}")
                        except Exception as error:
                            self.source.logger.exception(f"Fetch web content failed: {error}")

                    # use summary if content is empty
                    if summary and not content:
                        content = summary
                        self.source.logger.debug("Using review for content")
                    # use content for review if summary is empty
                    elif not summary and content:
                        review = content
                        self.source.logger.debug("Using content for review")

                    # use published date if available, otherwise use updated date
                    if published_parsed:
                        date = datetime.datetime(*published_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                        self.source.logger.debug("Using parsed 'published' date")
                    elif updated_parsed:
                        date = datetime.datetime(*updated_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                        self.source.logger.debug("Using parsed 'updated' date")
                    elif published:
                        date = published
                        self.source.logger.debug("Using 'published' date")
                    elif updated:
                        date = updated
                        self.source.logger.debug("Using 'updated' date")

                    for_hash = author + title + link_for_article

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        title,
                        review,
                        self.source.url,
                        link_for_article,
                        date,
                        author,
                        datetime.datetime.now(),
                        content,
                        self.source.id,
                        [],
                    )
                    news_item = self.sanitize_news_item(news_item, self.source)
                    news_item.print_news_item(self.source.logger)
                    news_items.append(news_item)

                    if links_limit > 0 and count >= links_limit:
                        self.source.logger.debug(f"Limit for article links ({links_limit}) has been reached.")
                        break

                self.publish(news_items)

            except Exception as error:
                self.source.logger.exception(f"Collection failed: {error}")
