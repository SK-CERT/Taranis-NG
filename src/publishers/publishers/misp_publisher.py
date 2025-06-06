"""Publisher for MISP."""

import json
from base64 import b64decode
import urllib3
from pymisp import PyMISP, MISPEvent

from .base_publisher import BasePublisher
from shared.log_manager import logger
from shared.config_publisher import ConfigPublisher


class MISPPublisher(BasePublisher):
    """MISP Publisher class.

    Attributes:
        type (str): Type of publisher.
        config (ConfigPublisher): Configuration for publisher.
        name (str): Name of publisher.
        description (str): Description of publisher.
        parameters (List[Parameter]): Parameters for publisher.
    """

    type = "MISP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input):
        """Publish data to MISP.

        Args:
            publisher_input (PublisherInput): Publisher input.
        Raises:
            Exception: If an error occurs while publishing data.
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            misp_url = publisher_input.param_key_values["MISP_URL"]
            misp_key = publisher_input.param_key_values["MISP_API_KEY"]
            misp_verifycert = False

            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)

            event_json = json.loads(bytes_data)

            urllib3.disable_warnings()

            misp = PyMISP(misp_url, misp_key, misp_verifycert)

            event = MISPEvent()
            event.load(event_json)
            misp.add_event(event)
        except Exception as error:
            self.logger.exception(f"Publishing fail: {error}")
