"""RSS collector module."""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import urllib.request
import uuid
from typing import TYPE_CHECKING, ClassVar

import feedparser
from bs4 import BeautifulSoup
from shared.common import TZ, ignore_exceptions, read_bool_parameter, read_int_parameter, text_to_simple_html
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData
from shared.url_guard import BlockedUrlError, assert_collector_url, build_guarded_opener

from .base_collector import BaseCollector, allowed_targets, not_modified

if TYPE_CHECKING:
    from collections.abc import Callable
    from http.client import HTTPResponse

# Seconds to wait for a feed; the request used to have no limit at all.
FEED_TIMEOUT = 60


class RSSCollector(BaseCollector):
    """RSS collector class.

    Arguments:
        BaseCollector: Base collector class.
    """

    collector_type = "RSS_COLLECTOR"
    config = ConfigCollector().get_config_by_type(collector_type)
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
                        # No tags we can quote, so take the page's text and wrap it in <pre>.
                        # Read it off the soup rather than the raw bytes: a page built from
                        # tags we do not quote is not plaintext, and its markup would now be
                        # escaped into the item instead of being swallowed by the parser.
                        plaintext = soup.get_text(separator="\n", strip=True)
                        return text_to_simple_html(plaintext, preformatted_text=True)
                    return "".join(content_html)

            except urllib.error.HTTPError as http_err:
                if http_err.code in [401, 429, 403]:
                    message = f"HTTP {http_err.code} {http_err.reason} for {url}. Skipping getting article content."
                    self.source.logger.warning(message)
                else:
                    self.source.logger.exception()

            except BlockedUrlError as blocked:
                self.source.logger.warning(f"{blocked}. Skipping getting article content.")

            except Exception:
                self.source.logger.exception("Fetch web content failed")
        return ""

    def __get_opener(self) -> Callable[..., HTTPResponse]:
        """Get the function this source fetches URLs with.

        Every URL it is given, and every redirect it follows, is checked by ``shared.url_guard``
        first: http(s) only, and no internal address unless the collectors node allows it.

        Returns:
            Callable: Used like ``urllib.request.urlopen``.
        """
        allowed = allowed_targets(self.source)
        if self.source.proxy_handler:
            return build_guarded_opener(self.source.proxy_handler, via_proxy=True, allowed=allowed)
        return build_guarded_opener(allowed=allowed)

    def __fetch_feed(self) -> dict | None:
        """Download the feed through the guarded opener and parse what came back.

        feedparser is handed the body, never the URL: given a string it would also open a local
        file of that name, and it follows redirects on its own.
        """
        try:
            # Asked here too, so that something that is not a URL at all is refused the same way.
            assert_collector_url(self.source.url, via_proxy=bool(self.source.proxy_handler), allowed=allowed_targets(self.source))
            request = urllib.request.Request(self.source.url)  # noqa: S310 - http(s) only, checked above
            # The header feedparser itself would send, so servers keep answering with a feed.
            request.add_header("Accept", feedparser.http.ACCEPT_HEADER)
            # Without one configured, feedparser's own, as before (some sites refuse urllib's).
            request.add_header("User-Agent", self.source.user_agent or feedparser.USER_AGENT)
            with self.source.opener(request, timeout=FEED_TIMEOUT) as response:
                body = response.read()
                headers = {name.lower(): value for name, value in response.headers.items()}
            # Not asked for, but some servers compress anyway.
            if headers.pop("content-encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
            # The URL after redirects is what relative links in the feed are resolved against.
            headers.setdefault("content-location", response.geturl())
            return feedparser.parse(body, response_headers=headers)
        except BlockedUrlError as blocked:
            self.source.logger.error(f"{blocked}. Skipping collection.")  # noqa: TRY400 - the reason is the message
            return None
        except Exception:
            self.source.logger.exception("Fetch feed failed")
            return None

    def __get_feed(self) -> dict | None:
        """Fetch the feed data, using proxy if provided, and check modification status.

        Returns:
            dict: The parsed feed data or an empty dictionary if not modified.
        """
        # Check if the feed has been modified since the last collection
        check_if_modified = read_bool_parameter("CHECK_IF_MODIFIED", default_value=True, object_dict=self.source)
        if check_if_modified and self.source.last_collected and not_modified(self.source):
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
        if not read_bool_parameter("PREFER_SCRAPING", default_value=False, object_dict=self.source) and content:
            content = text_to_simple_html(content, preformatted_text=False)
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
            dt.datetime.now(TZ),
            content,
            self.source.id,
            [],
        )

    def _get_review_and_content(self, summary: str, content_rss: list[dict]) -> tuple[str, str]:
        review = summary or ""
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
            return dt.datetime(*published_parsed[:6], tzinfo=TZ).strftime("%d.%m.%Y - %H:%M")
        if updated_parsed:
            self.source.logger.debug("Using parsed 'updated' date")
            return dt.datetime(*updated_parsed[:6], tzinfo=TZ).strftime("%d.%m.%Y - %H:%M")
        if published:
            self.source.logger.debug("Using 'published' date")
            return published
        if updated:
            self.source.logger.debug("Using 'updated' date")
            return updated
        return ""
