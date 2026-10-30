"""Base definition for module types."""

from dataclasses import dataclass

from shared.schema.parameter import ParameterType


@dataclass
class ParamType:
    """Parameter type definition.

    Attributes:
        key (str): Parameter key.
        name (str): Parameter name.
        description (str): Parameter description.
        type (ParameterType): Parameter type
        translate (bool): Whether the parameter is translatable.
    """

    key: str
    name: str
    description: str
    type: ParameterType
    default_value: str = ""
    translate: bool = False


@dataclass
class ModuleType:
    """Module type definition.

    Attributes:
        type (str): Module type.
        name (str): Module name.
        description (str): Module description.
        parameters (List[ParamType]): Module parameters.
    """

    type: str
    name: str
    description: str
    parameters: list[ParamType]

    def __init__(
        self,
        type: str,  # noqa: A002
        name: str,
        description: str,
    ) -> None:
        """Initialize module type."""
        self.type = type
        self.name = name
        self.description = description


class ConfigBase:
    """Base definition for module types."""

    def get_config_by_type(
        self,
        module_type: str,
    ) -> ModuleType | None:
        """Get module configuration by type.

        Args:
            module_type (str): Module type.

        Returns:
            ModuleType | None: Module configuration or None if not found.
        """
        for mod in self.modules:
            if mod.type == module_type:
                return mod
        return None
