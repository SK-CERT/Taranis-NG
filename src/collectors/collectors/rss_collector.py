"""RSS collector module."""

import datetime
import feedparser
import hashlib
import uuid
from bs4 import BeautifulSoup
import aiohttp
import aiohttp_socks
import asyncio

from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData


class RSSCollector(BaseCollector):
    """RSS collector class."""

    type = "RSS_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    news_items = []

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from RSS or Atom feed."""

        def strip_html_tags(html_string):
            """Strip HTML tags from the given string."""
            soup = BeautifulSoup(html_string, "html.parser")
            return soup.get_text(separator=" ", strip=True)

        async def fetch_feed(session, url):
            """Fetch the feed using feedparser."""
            async with session.get(url) as response:
                content = await response.text()
                return feedparser.parse(content)

        async def get_feed(feed_url, last_collected=None, user_agent=None):
            """Fetch the feed data, using proxy if provided, and check modification status."""
            headers = {}
            if user_agent:
                headers["User-Agent"] = user_agent

            connector = aiohttp_socks.ProxyConnector.from_url(proxy) if proxy else None

            async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                # Check if the feed has been modified since the last collection
                if last_collected:
                    if await BaseCollector.not_modified(self.collector_source, feed_url, last_collected, session, user_agent):
                        return None

                logger.debug(f"{self.collector_source} Fetching feed from URL: {feed_url}")
                return await fetch_feed(session, feed_url)

        async def process_feed_entry(feed_entry, user_agent, proxy):
            """Process a single feed entry asynchronously."""
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
                return None
            elif not article:
                logger.info(f"{self.collector_source} Visiting an article: {link_for_article}")
                html_article = ""
                try:
                    headers = {"User-Agent": user_agent} if user_agent else {}
                    connector = aiohttp_socks.ProxyConnector.from_url(proxy) if proxy else None
                    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                        async with session.get(link_for_article) as response:
                            html_article = await response.text()

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

            return news_item

        feed_url = source.parameter_values["FEED_URL"]
        links_limit = BaseCollector.read_int_parameter("LINKS_LIMIT", 0, source)
        last_collected = source.last_collected
        user_agent = source.parameter_values["USER_AGENT"]
        parsed_proxy = BaseCollector.get_parsed_proxy(source.parameter_values["PROXY_SERVER"], self.collector_source)
        proxy = parsed_proxy.geturl() if parsed_proxy else None

        if user_agent:
            logger.info(f"{self.collector_source} Requesting feed URL: {feed_url} (User-Agent: {user_agent})")
        else:
            logger.info(f"{self.collector_source} Requesting feed URL: {feed_url}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        feed = loop.run_until_complete(get_feed(feed_url, last_collected, user_agent))
        if feed:
            try:
                logger.debug(f"{self.collector_source} Feed returned {len(feed['entries'])} entries.")

                tasks = []
                for feed_entry in feed["entries"]:
                    tasks.append(process_feed_entry(feed_entry, user_agent, proxy))

                news_items = loop.run_until_complete(asyncio.gather(*tasks))

                # Filter out None values
                news_items = [item for item in news_items if item is not None]

                if links_limit > 0:
                    news_items = news_items[:links_limit]

                BaseCollector.publish(news_items, source, self.collector_source)

            except Exception as error:
                logger.exception(f"{self.collector_source} Collection failed: {error}")

        else:
            logger.info(f"{self.collector_source} Will not collect the feed because nothing has changed.")
            BaseCollector.publish([], source, self.collector_source)
