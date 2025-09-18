"""Publisher for Mastodon."""

from base64 import b64decode

from mastodon import Mastodon

from shared.common import read_bool_parameter
from shared.config_publisher import ConfigPublisher
from shared.log_manager import logger

from .base_publisher import BasePublisher


class MASTODONPublisher(BasePublisher):
    """Publisher for Mastodon.

    Attributes:
        type (str): Publisher type.
        config (ConfigPublisher): Publisher configuration.
        name (str): Publisher name.
        description (str): Publisher description.
        parameters (list): Publisher parameters.
    """

    type = "MASTODON_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input: dict) -> None:
        """Publish data.

        Args:
            publisher_input (PublisherInput): Publisher input.

        Raises:
            Exception: If an error occurs.
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            access_token = publisher_input.param_key_values["MASTODON_ACCESS_TOKEN"]
            api_base_url = publisher_input.param_key_values["MASTODON_API_BASE_URL"]
            visibility = publisher_input.param_key_values["VISIBILITY"]
            sensitive = read_bool_parameter("SENSITIVE", default_value=False, object_dict=publisher_input)

            spoiler_text = None
            status = None

            if publisher_input.message_title:
                spoiler_text = b64decode(publisher_input.message_title, validate=True).decode("UTF-8")
            if publisher_input.message_body:
                status = b64decode(publisher_input.message_body, validate=True).decode("UTF-8")

            if not status:
                self.logger.warning("Status is empty, publication skipped.")
                return

            if spoiler_text in ["", "None"]:
                spoiler_text = None

            if not api_base_url:
                api_base_url = "https://mastodon.social"

            if visibility.casefold() not in ["public", "direct", "unlisted", "private"]:
                visibility = None

            mastodon = Mastodon(access_token=access_token, api_base_url=api_base_url)
            mastodon.status_post(status=status, sensitive=sensitive, visibility=visibility, spoiler_text=spoiler_text)

        except Exception as error:
            self.logger.exception(f"Publishing fail: {error}")
