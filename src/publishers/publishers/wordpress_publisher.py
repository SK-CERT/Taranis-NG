"""Publisher for Wordpress."""

import base64
from base64 import b64decode
from datetime import datetime
import requests

from .base_publisher import BasePublisher
from shared.log_manager import logger
from shared.config_publisher import ConfigPublisher


class WORDPRESSPublisher(BasePublisher):
    """Publisher for Wordpress.

    Attributes:
        type (str): Publisher type.
        config (ConfigPublisher): Publisher configuration.
        name (str): Publisher name.
        description (str): Publisher description.
        parameters (list): Publisher parameters.
    """

    type = "WORDPRESS_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input):
        """Publish data.

        Args:
            publisher_input (PublisherInput): Publisher input.
        Raises:
            Exception: If an error occurs
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            user = publisher_input.parameter_values_map["WP_USER"]
            python_app_secret = publisher_input.parameter_values_map["WP_PYTHON_APP_SECRET"]
            main_wp_url = publisher_input.parameter_values_map["WP_URL"]

            data_string = user + ":" + python_app_secret

            token = base64.b64encode(data_string.encode())

            headers = {"Authorization": "Basic " + token.decode("utf-8")}

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True).decode("utf-8")

            now = datetime.now()
            title = "Report from TaranisNG on " + now.strftime("%d.%m.%Y") + " at " + now.strftime("%H:%M")

            post = {"title": title, "status": "publish", "content": bytes_data}

            requests.post(main_wp_url + "/index.php/wp-json/wp/v2/posts", headers=headers, json=post)
        except Exception as error:
            self.logger.exception(f"Publishing fail: {error}")
