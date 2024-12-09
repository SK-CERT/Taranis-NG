"""Module for Manual collector."""

from .base_collector import BaseCollector
from shared.config_collector import ConfigCollector


class ManualCollector(BaseCollector):
    """XXX_2069."""

    type = "MANUAL_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """XXX_2069."""
        pass
