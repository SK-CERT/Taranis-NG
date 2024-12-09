"""Base definition for module types."""

from dataclasses import dataclass
from typing import List
from shared.schema.parameter import ParameterType


@dataclass
class param_type:
    """XXX_2069."""

    key: str
    name: str
    description: str
    type: ParameterType


@dataclass
class module_type:
    """XXX_2069."""

    type: str
    name: str
    description: str
    parameters: List[param_type]

    def __init__(self, type, name, description):
        """XXX_2069."""
        self.type = type
        self.name = name
        self.description = description


class ConfigBase:
    """XXX_2069."""

    def get_config_by_type(self, type: str) -> module_type | None:
        """XXX_2069."""
        for mod in self.modules:
            if mod.type == type:
                return mod
        return None
