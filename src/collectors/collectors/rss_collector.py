"""RSS collector module."""

import datetime
import hashlib
import urllib.request
import uuid
from typing import ClassVar

import feedparser
from bs4 import BeautifulSoup

from shared.common import TZ, ignore_exceptions, read_bool_parameter, read_int_parameter, text_to_simple_html
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData

from .base_collector import BaseCollector, not_modified


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

    news_items: ClassVar[list[NewsItemData]] = []

    def _scrape_content(self, url: str, title: str, count: int, feed: dict | None) -> str:
        """Scrape content from the given URL.

        Arguments:
            url (str): The URL to scrape content from.
            title (str): The title of the feed entry (for logging purposes).
            count (int): The current count of the feed entry (for logging purposes).
            feed (dict | None): The feed dictionary (for logging purposes).

        Returns:
            str: The scraped content as a string.
        """
        if not url:
            self.source.logger.debug(f"Skipping an empty link in feed entry '{title}'.")
        elif not url.startswith(("http://", "https://")):
            self.source.logger.debug(f"Skipping unsupported URL scheme in link: {url}")
        else:
            message = f"Visiting an article {count}/{len(feed['entries'])}: {url}"
            self.source.logger.info(message)
            try:
                request = urllib.request.Request(url)  # noqa: S310
                request.add_header("User-Agent", self.source.user_agent)

                with self.source.opener(request) as response:
                    html = response.read()
                if html:
                    soup = BeautifulSoup(html, features="html.parser")
                    # get all <p> tags text in body
                    content_html = [str(p) for p in soup.find_all("p")]
                    if not content_html:
                        # try to get all <pre> tags text in body
                        content_html = [str(pre) for pre in soup.find_all("pre")]
                    if not content_html:
                        # No tags found, treat as plaintext and wrap in <pre> tags
                        # decode bytes to string if needed
                        plaintext = html.decode(errors="replace") if isinstance(html, bytes) else str(html)
                        return text_to_simple_html(plaintext, preformatted_text=True)
                    return "".join(content_html)

            except urllib.error.HTTPError as http_err:
                if http_err.code in [401, 429, 403]:
                    message = f"HTTP {http_err.code} {http_err.reason} for {url}. Skipping getting article content."
                    self.source.logger.warning(message)
                else:
                    self.source.logger.exception()

            except Exception:
                self.source.logger.exception("Fetch web content failed")
        return ""

    def __get_opener(self) -> urllib.request.OpenerDirector:
        """Get the opener function for URL requests.

        Arguments:
            proxy_handler (SocksiPyHandler): The proxy handler to use for the request (default: None).

        Returns:
            function: The opener function to use for URL requests.
        """
        if self.source.proxy_handler:
            return urllib.request.build_opener(self.source.proxy_handler).open
        return urllib.request.urlopen

    def __fetch_feed(self) -> dict | None:
        """Fetch the feed using feedparser with optional handler."""
        if self.source.user_agent:
            feedparser.USER_AGENT = self.source.user_agent
        try:
            if self.source.proxy_handler:
                return feedparser.parse(self.source.url, handlers=[self.source.proxy_handler])
            return feedparser.parse(self.source.url)
        except Exception:
            self.source.logger.exception("Fetch feed failed")
            return None

    def __get_feed(self) -> dict | None:
        """Fetch the feed data, using proxy if provided, and check modification status.

        Returns:
            dict: The parsed feed data or an empty dictionary if not modified.
        """
        # Check if the feed has been modified since the last collection
        if self.source.last_collected and not_modified(self.source):
            return None

        self.source.logger.debug(f"Fetching feed from URL: {self.source.url}")
        return self.__fetch_feed()

    @ignore_exceptions
    def collect(self) -> None:
        """Collect data from RSS or Atom feed."""
        self._initialize_source(self.source)
        feed = self.__get_feed()
        if not feed:
            return
        try:
            self.source.logger.debug(f"Feed returned {len(feed['entries'])} entries.")
            links_limit = read_int_parameter("LINKS_LIMIT", 0, self.source)
            news_items = self._process_feed_entries(feed, links_limit)
            self.publish(news_items)
        except Exception:
            self.source.logger.exception("Collection failed")

    def _initialize_source(self, source: object) -> None:
        self.source = source
        super()._initialize_source(source)
        source.url = source.param_key_values["FEED_URL"]
        if not source.url:
            source.logger.error("Feed URL is not set. Skipping collection.")
            return
        source.user_agent = source.param_key_values["USER_AGENT"]
        source.proxy = source.param_key_values["PROXY_SERVER"]
        source.parsed_proxy = self.get_parsed_proxy()
        source.proxy_handler = self.get_proxy_handler() if source.parsed_proxy else None
        source.opener = self.__get_opener()
        if source.user_agent:
            source.logger.info(f"Requesting feed URL: {source.url} (User-Agent: {source.user_agent})")
        else:
            source.logger.info(f"Requesting feed URL: {source.url}")

    def _process_feed_entries(self, feed: dict, links_limit: int) -> list[NewsItemData]:
        news_items = []
        for count, feed_entry in enumerate(feed["entries"], 1):
            news_item = self._create_news_item(feed_entry, count, feed)
            news_item = self.sanitize_news_item(news_item, self.source)
            news_item.print_news_item(self.source.logger)
            news_items.append(news_item)
            if links_limit > 0 and count >= links_limit:
                self.source.logger.debug(f"Limit for article links ({links_limit}) has been reached.")
                break
        return news_items

    def _create_news_item(self, feed_entry: dict, count: int, feed: dict) -> NewsItemData:
        author = feed_entry.get("author", "")
        title = feed_entry.get("title", "")
        published = feed_entry.get("published", "")
        published_parsed = feed_entry.get("published_parsed", "")
        updated = feed_entry.get("updated", "")
        updated_parsed = feed_entry.get("updated_parsed", "")
        summary = feed_entry.get("summary", "")
        content_rss = feed_entry.get("content", "")
        link_for_article = feed_entry.get("link", "")
        review, content = self._get_review_and_content(summary, content_rss)
        if read_bool_parameter("PREFER_SCRAPING", default_value=False, object_dict=self.source) or (
            content in ["", None] and summary in ["", None]
        ):
            html_content = self._scrape_content(link_for_article, title, count, feed)
            if len(html_content) > len(summary):
                self.source.logger.debug("Using web text for content")
                content = html_content
        review, content = self._resolve_review_content(summary, content)
        date = self._resolve_date(published_parsed, updated_parsed, published, updated)
        for_hash = author + title + link_for_article
        return NewsItemData(
            uuid.uuid4(),
            hashlib.sha256(for_hash.encode()).hexdigest(),
            title,
            review,
            self.source.url,
            link_for_article,
            date,
            author,
            datetime.datetime.now(tz=TZ),
            content,
            self.source.id,
            [],
        )

    def _get_review_and_content(self, summary: str, content_rss: list[dict]) -> tuple[str, str]:
        review = summary if summary else ""
        content = ""
        if content_rss:
            content = content_rss[0].get("value", "")
        return review, content

    def _resolve_review_content(self, summary: str, content: str) -> tuple[str, str]:
        if summary and not content:
            self.source.logger.debug("Using review for content")
            return summary, summary
        if not summary and content:
            self.source.logger.debug("Using content for review")
            return content, content
        return summary, content

    def _resolve_date(self, published_parsed: tuple, updated_parsed: tuple, published: str, updated: str) -> str:
        if published_parsed:
            self.source.logger.debug("Using parsed 'published' date")
            return datetime.datetime(*published_parsed[:6], tzinfo=TZ).strftime("%d.%m.%Y - %H:%M")
        if updated_parsed:
            self.source.logger.debug("Using parsed 'updated' date")
            return datetime.datetime(*updated_parsed[:6], tzinfo=TZ).strftime("%d.%m.%Y - %H:%M")
        if published:
            self.source.logger.debug("Using 'published' date")
            return published
        if updated:
            self.source.logger.debug("Using 'updated' date")
            return updated
        return ""
