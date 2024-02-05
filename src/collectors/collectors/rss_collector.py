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
import dateparser

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
    description = "Collector for gathering data from RSS feeds"

    parameters = [
        Parameter(0, "FEED_URL", "Feed URL", "Full url for RSS feed", ParameterType.STRING),
        Parameter(0, "USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING),
    ]

    parameters.extend(BaseCollector.parameters)

    news_items = []

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from RSS feed.

        Arguments:
            source -- Source object.
        """
        feed_url = source.parameter_values["FEED_URL"]
        interval = source.parameter_values["REFRESH_INTERVAL"]

        log_manager.log_collector_activity("rss", source.name, "Starting collector for url: {}".format(feed_url))

        user_agent = source.parameter_values["USER_AGENT"]
        if user_agent:
            feedparser.USER_AGENT = user_agent
            # user_agent_headers = {"User-Agent": user_agent}
        else:
            # user_agent_headers = {}
            pass

        # use system proxy
        proxy_handler = None
        opener = urllib.request.urlopen

        if "PROXY_SERVER" in source.parameter_values:
            proxy_server = source.parameter_values["PROXY_SERVER"]

            # disable proxy - do not use system proxy
            if proxy_server == "none":
                proxy_handler = urllib.request.ProxyHandler({})
            else:
                proxy = re.search(r"^(http|https|socks4|socks5|ftp)://([a-zA-Z0-9\-\.\_]+):(\d+)/?$", proxy_server)
                if proxy:
                    scheme, host, port = proxy.groups()
                    # classic HTTP/HTTPS proxy
                    if scheme in ["http", "https", "ftp"]:
                        proxy_handler = urllib.request.ProxyHandler(
                            {
                                "http": "{}://{}:{}".format(scheme, host, port),
                                "https": "{}://{}:{}".format(scheme, host, port),
                                "ftp": "{}://{}:{}".format(scheme, host, port),
                            }
                        )
                    # socks4 proxy
                    elif scheme == "socks4":
                        proxy_handler = SocksiPyHandler(socks.SOCKS4, host, int(port))
                    # socks5 proxy
                    elif scheme == "socks5":
                        proxy_handler = SocksiPyHandler(socks.SOCKS5, host, int(port))

        # use proxy in urllib
        if proxy_handler:
            opener = urllib.request.build_opener(proxy_handler).open

        try:
            if proxy_handler:
                feed = feedparser.parse(feed_url, handlers=[proxy_handler])
            else:
                feed = feedparser.parse(feed_url)

            log_manager.log_collector_activity("rss", source.name, "RSS returned feed with {} entries".format(len(feed["entries"])))

            news_items = []

            limit = BaseCollector.history(interval)
            for feed_entry in feed["entries"]:
                for key in ["author", "published", "title", "description", "link"]:
                    if key not in feed_entry.keys():
                        feed_entry[key] = ""

                published = feed_entry["published"]
                published = dateparser.parse(published, settings={"DATE_ORDER": "DMY"})
                # comment this at the beginning of the testing to get some initial data
                if str(published) > str(limit):
                    link_for_article = feed_entry["link"]
                    if not link_for_article:
                        log_manager.log_collector_activity("rss", source.name, "Skipping (empty link)")
                        continue

                    log_manager.log_collector_activity("rss", source.name, "Processing entry [{}]".format(link_for_article))

                    html_content = ""
                    request = urllib.request.Request(link_for_article)
                    request.add_header("User-Agent", user_agent)

                    with opener(request) as response:
                        html_content = response.read()

                    soup = BeautifulSoup(html_content, features="html.parser")

                    content = ""

                    if html_content:
                        content_text = [p.text.strip() for p in soup.findAll("p")]
                        replaced_str = "\xa0"
                        if replaced_str:
                            content = [w.replace(replaced_str, " ") for w in content_text]
                            content = " ".join(content)

                    for_hash = feed_entry["author"] + feed_entry["title"] + feed_entry["link"]

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        feed_entry["title"],
                        feed_entry["description"],
                        feed_url,
                        feed_entry["link"],
                        feed_entry["published"],
                        feed_entry["author"],
                        datetime.datetime.now(),
                        content,
                        source.id,
                        [],
                    )

                    news_items.append(news_item)

            BaseCollector.publish(news_items, source)

        except Exception as error:
            log_manager.log_collector_activity("rss", source.name, "RSS collection exceptionally failed")
            BaseCollector.print_exception(source, error)
            log_manager.log_debug(traceback.format_exc())

        log_manager.log_debug("{} collection finished.".format(self.type))
