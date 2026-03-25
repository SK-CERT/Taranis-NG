"""Module for Manual collector."""

from shared.common import ignore_exceptions
from shared.config_collector import ConfigCollector

from .base_collector import BaseCollector


class ManualCollector(BaseCollector):
    """Manual collector class."""

    collector_type = "MANUAL_COLLECTOR"
    config = ConfigCollector().get_config_by_type(collector_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @ignore_exceptions
    def collect(self) -> None:
        """Collect data from source."""
