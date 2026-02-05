"""Publisher for Twiter."""

from base64 import b64decode
from http import HTTPStatus

import tweepy

from shared.config_publisher import ConfigPublisher
from shared.log_manager import logger

from .base_publisher import BasePublisher


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

    def publish(self, publisher_input: dict) -> tuple[dict, HTTPStatus]:
        """Publish data.

        Args:
            publisher_input (PublisherInput): Publisher input.

        Raises:
            Exception: If an error occurs.
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            api_key = publisher_input.param_key_values["TWITTER_API_KEY"]
            api_key_secret = publisher_input.param_key_values["TWITTER_API_KEY_SECRET"]
            access_token = publisher_input.param_key_values["TWITTER_ACCESS_TOKEN"]
            access_token_secret = publisher_input.param_key_values["TWITTER_ACCESS_TOKEN_SECRET"]

            auth = tweepy.OAuthHandler(api_key, api_key_secret)
            auth.set_access_token(access_token, access_token_secret)

            api = tweepy.API(auth)

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True)

            max_size = 240
            if len(bytes_data) <= max_size:
                api.update_status(bytes_data)
                return {}, HTTPStatus.OK
            msg = f"Data size exceeds Twitter's character limit ({len(bytes_data)} > {max_size})."
            self.logger.error(msg)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

        except Exception as error:
            self.logger.exception(f"Error: {error}")
            return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR
