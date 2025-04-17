"""Publisher for Twiter."""

from base64 import b64decode
import tweepy

from .base_publisher import BasePublisher
from managers.log_manager import logger

from shared.config_publisher import ConfigPublisher


class TWITTERPublisher(BasePublisher):
    """Publisher for Twitter.

    Attributes:
        type (str): Publisher type.
        config (ConfigPublisher): Publisher configuration.
        name (str): Publisher name.
        description (str): Publisher description.
        parameters (list): Publisher parameters.
    """

    type = "TWITTER_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input):
        """Publish data.

        Args:
            publisher_input (PublisherInput): Publisher input.
        Raises:
            Exception: If an error occurs.
        """
        self.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            api_key = publisher_input.parameter_values_map["TWITTER_API_KEY"]
            api_key_secret = publisher_input.parameter_values_map["TWITTER_API_KEY_SECRET"]
            access_token = publisher_input.parameter_values_map["TWITTER_ACCESS_TOKEN"]
            access_token_secret = publisher_input.parameter_values_map["TWITTER_ACCESS_TOKEN_SECRET"]

            auth = tweepy.OAuthHandler(api_key, api_key_secret)
            auth.set_access_token(access_token, access_token_secret)

            api = tweepy.API(auth)

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True)

            if len(bytes_data) <= 240:
                api.update_status(bytes_data)
        except Exception as error:
            logger.exception(f"Publishing fail: {error}")
