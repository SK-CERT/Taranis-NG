"""Publisher for MISP."""

import json
from base64 import b64decode
import urllib3
from pymisp import ExpandedPyMISP, MISPEvent

from .base_publisher import BasePublisher
from shared.config_publisher import ConfigPublisher


class MISPPublisher(BasePublisher):
    """XXX_2069."""

    type = "MISP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input):
        """XXX_2069."""
        try:
            misp_url = publisher_input.parameter_values_map["MISP_URL"]
            misp_key = publisher_input.parameter_values_map["MISP_API_KEY"]
            misp_verifycert = False

            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)

            event_json = json.loads(bytes_data)

            urllib3.disable_warnings()

            misp = ExpandedPyMISP(misp_url, misp_key, misp_verifycert)

            event = MISPEvent()
            event.load(event_json)
            misp.add_event(event)
        except Exception as error:
            BasePublisher.print_exception(self, error)
