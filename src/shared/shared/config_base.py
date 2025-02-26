"""Base definition for module types."""

from dataclasses import dataclass
from typing import List
from shared.schema.parameter import ParameterType


@dataclass
class param_type:
    """Parameter type definition.

    Attributes:
        key (str): Parameter key.
        name (str): Parameter name.
        description (str): Parameter description.
        type (ParameterType): Parameter type
    """

    key: str
    name: str
    description: str
    type: ParameterType
    default_value: str = ""


@dataclass
class module_type:
    """Module type definition.

    Attributes:
        type (str): Module type.
        name (str): Module name.
        description (str): Module description.
        parameters (List[param_type]): Module parameters.
    """

    type: str
    name: str
    description: str
    parameters: List[param_type]

    def __init__(self, type, name, description):
        """Initialize module type."""
        self.type = type
        self.name = name
        self.description = description


class ConfigBase:
    """Base definition for module types."""

    def get_config_by_type(self, type: str) -> module_type | None:
        """Get module configuration by type.

        Args:
            type (str): Module type.
        Returns:
            module_type | None: Module configuration or None if not found.
        """
        for mod in self.modules:
            if mod.type == type:
                return mod
        return None
