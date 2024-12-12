"""Module for Manual collector."""

from .base_collector import BaseCollector
from shared.config_collector import ConfigCollector


class ManualCollector(BaseCollector):
    """Manual collector class."""

    type = "MANUAL_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from source."""
        pass
