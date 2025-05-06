"""Module for X collector."""

import datetime
import hashlib
import uuid
import tweepy

from .base_collector import BaseCollector
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData


class TwitterCollector(BaseCollector):
    """Collector for gathering data from Twitter.

    Attributes:
        type (str): Type of the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (list): List of parameters required for the collector.
    Methods:
        collect(source): Collect data from a Twitter source.
    Raises:
        Exception: If an error occurs during the collection process.
    """

    type = "TWITTER_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from X source.

        Parameters:
            source -- Source object.
        """
        self.source = source

        try:
            news_items = []
            attributes = []

            search_keywords = self.source.parameter_values["SEARCH_KEYWORDS"].replace(" ", "")
            keywords_list = search_keywords.split(",")

            search_hashtags = self.source.parameter_values["SEARCH_HASHTAGS"].replace(" ", "")
            hashtags_list = search_hashtags.split(",")

            number_of_tweets = self.source.parameter_values["NUMBER_OF_TWEETS"]

            twitter_api_key = self.source.parameter_values["TWITTER_API_KEY"]
            twitter_api_key_secret = self.source.parameter_values["TWITTER_API_KEY_SECRET"]
            twitter_access_token = self.source.parameter_values["TWITTER_ACCESS_TOKEN"]
            twitter_access_token_secret = self.source.parameter_values["TWITTER_ACCESS_TOKEN_SECRET"]

            proxy_server = self.source.parameter_values["PROXY_SERVER"]

            auth = tweepy.OAuthHandler(twitter_api_key, twitter_api_key_secret)
            auth.set_access_token(twitter_access_token, twitter_access_token_secret)

            if proxy_server:
                proxy = "socks5://" + proxy_server
                api = tweepy.API(auth, proxy=str(proxy), wait_on_rate_limit=True)
            else:
                api = tweepy.API(auth, wait_on_rate_limit=True)

            if number_of_tweets == "":
                number_of_tweets = 100

            if search_keywords:
                public_tweets = tweepy.Cursor(api.search, q=keywords_list).items(int(number_of_tweets))
            elif search_hashtags:
                public_tweets = tweepy.Cursor(api.search, q=hashtags_list).items(int(number_of_tweets))
            else:
                public_tweets = api.home_timeline(count=number_of_tweets)

            interval = source.parameter_values["REFRESH_INTERVAL"]

            limit = BaseCollector.history(interval)

            for tweet in public_tweets:

                time_to_collect = tweet.created_at

                if time_to_collect > limit:
                    tweet_id = tweet.id_str
                    link = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
                    author = tweet.author.name
                    content = tweet.text.encode("utf-8")
                    review = content  # max 280 chars - it's ok
                    published = tweet.created_at
                    title = "Twitter post from " + "@" + author
                    url = ""

                    for_hash = author + tweet_id + str(review)

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        title,
                        review,
                        url,
                        link,
                        published,
                        author,
                        datetime.datetime.now(),
                        content,
                        self.source.id,
                        attributes,
                    )

                    news_items.append(news_item)

            BaseCollector.publish(news_items, source)

        except Exception as error:
            self.source.logger.exception(f"Collection failed: {error}")
