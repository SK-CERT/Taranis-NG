"""RSS collector module."""

import datetime
import hashlib
import uuid
import traceback
import re
import socks
import feedparser
import urllib.request
from sockshandler import SocksiPyHandler
from bs4 import BeautifulSoup

from .base_collector import BaseCollector
from managers import log_manager
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

        def strip_html_tags(html_string):
            soup = BeautifulSoup(html_string, "html.parser")
            return soup.get_text(separator=" ", strip=True)

        BaseCollector.update_last_attempt(source)
        feed_url = source.parameter_values["FEED_URL"]
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)

        log_manager.log_collector_activity("rss", source.name, f"Starting collector for URL: {feed_url}")

        user_agent = source.parameter_values["USER_AGENT"]
        if user_agent:
            feedparser.USER_AGENT = user_agent
            log_manager.log_collector_activity("rss", source.name, f"Using user agent: {user_agent}")

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
                        proxy_handler = urllib.request.ProxyHandler(
                            {
                                "http": f"{scheme}://{host}:{port}",
                                "https": f"{scheme}://{host}:{port}",
                                "ftp": f"{scheme}://{host}:{port}",
                            }
                        )
                    elif scheme == "socks4":
                        proxy_handler = SocksiPyHandler(socks.SOCKS4, host, int(port))
                    elif scheme == "socks5":
                        proxy_handler = SocksiPyHandler(socks.SOCKS5, host, int(port))

        # use proxy in urllib
        if proxy_handler:
            opener = urllib.request.build_opener(proxy_handler).open

        try:
            if proxy_handler:
                feed = feedparser.parse(feed_url, handlers=[proxy_handler])
                log_manager.log_collector_activity("rss", source.name, f"Using proxy {proxy_server} for RSS feed")
            else:
                feed = feedparser.parse(feed_url)

            log_manager.log_collector_activity("rss", source.name, f"RSS returned feed with {len(feed['entries'])} entries")

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
                log_manager.log_collector_activity("rss", source.name, f"Title: {title}")
                if summary:
                    review = strip_html_tags(summary[:500])
                if content:
                    article = strip_html_tags(content[0].get("value", ""))

                if not link_for_article:
                    log_manager.log_collector_activity("rss", source.name, "Skipping (empty link)")
                    continue
                elif not article:
                    log_manager.log_collector_activity(
                        "rss", source.name, f"Visiting article {count}/{len(feed['entries'])}: {link_for_article}"
                    )
                    html_article = ""
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

                # use summary if article is empty
                if summary and not article:
                    article = strip_html_tags(summary)
                # use first 500 characters of article if summary is empty
                elif not summary and article:
                    review = article[:500]

                # use published date if available, otherwise use updated date
                if published_parsed:
                    date = datetime.datetime(*published_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                elif updated_parsed:
                    date = datetime.datetime(*updated_parsed[:6]).strftime("%d.%m.%Y - %H:%M")
                elif published:
                    date = published
                elif updated:
                    date = updated

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
                    log_manager.log_collector_activity("rss", source.name, f"Limit for article links reached ({links_limit})")
                    break

            BaseCollector.publish(news_items, source)

        except Exception as error:
            log_manager.log_collector_activity("rss", source.name, "RSS collection exceptionally failed")
            BaseCollector.print_exception(source, error)
            log_manager.log_debug(traceback.format_exc())

        log_manager.log_debug("{} collection finished.".format(self.type))
