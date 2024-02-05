import datetime
import hashlib
import uuid
import traceback
import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse

from .base_collector import BaseCollector
from managers import log_manager
from shared.schema.news_item import NewsItemData
from shared.schema.parameter import Parameter, ParameterType


class AtomCollector(BaseCollector):
    type = "ATOM_COLLECTOR"
    name = "Atom Collector"
    description = "Collector for gathering data from Atom feeds"

    parameters = [Parameter(0, "ATOM_FEED_URL", "Atom feed URL", "Full url for Atom feed", ParameterType.STRING),
                  Parameter(0, "USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING)
                  ]

    parameters.extend(BaseCollector.parameters)

    news_items = []

    @BaseCollector.ignore_exceptions
    def collect(self, source):

        feed_url = source.parameter_values['ATOM_FEED_URL']
        user_agent = source.parameter_values['USER_AGENT']
        interval = source.parameter_values['REFRESH_INTERVAL']
        log_manager.log_collector_activity("atom", source.name, "Starting collector for url: {}".format(feed_url))

        proxies = {}
        if 'PROXY_SERVER' in source.parameter_values:
            proxy_server = source.parameter_values['PROXY_SERVER']
            if proxy_server.startswith('https://'):
                proxies['https'] = proxy_server
            elif proxy_server.startswith('http://'):
                proxies['http'] = proxy_server
            else:
                proxies['http'] = 'http://' + proxy_server

        try:
            if proxies:
                atom_xml = requests.get(feed_url, headers={'User-Agent': user_agent}, proxies=proxies)
                feed = feedparser.parse(atom_xml.text)
            else:
                feed = feedparser.parse(feed_url)

            log_manager.log_collector_activity("atom", source.name, "ATOM returned feed with {} entries".format(len(feed["entries"])))

            news_items = []

            limit = BaseCollector.history(interval)
            for feed_entry in feed['entries']:
                published = feed_entry['updated']
                published = parse(published, tzinfos=BaseCollector.timezone_info())
                # comment this at the beginning of the testing to get some initial data
                if str(published) > str(limit):
                    link_for_article = feed_entry['link']
                    log_manager.log_collector_activity("atom", source.name, "Processing entry [{}]".format(link_for_article))
                    if proxies:
                        page = requests.get(link_for_article, headers={'User-Agent': user_agent}, proxies=proxies)
                    else:
                        page = requests.get(link_for_article, headers={'User-Agent': user_agent})

                    html_content = page.text

                    if html_content:
                        content = BeautifulSoup(html_content, features='html.parser').text
                    else:
                        content = ''

                    description = feed_entry['summary'][:500].replace('<p>', ' ')

                    for_hash = feed_entry['author'] + feed_entry['title'] + feed_entry['link']

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        feed_entry['title'],
                        description,
                        feed_url,
                        feed_entry['link'],
                        feed_entry['updated'],
                        feed_entry['author'],
                        datetime.datetime.now(),
                        content,
                        source.id,
                        []
                    )

                    news_items.append(news_item)

            BaseCollector.publish(news_items, source)
        except Exception as error:
            log_manager.log_collector_activity("atom", source.name, "ATOM collection exceptionally failed")
            BaseCollector.print_exception(source, error)
            log_manager.log_debug(traceback.format_exc())

        log_manager.log_debug("{} collection finished.".format(self.type))
