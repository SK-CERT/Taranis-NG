"""This module defines the schema and data model for States using Marshmallow for serialization and deserialization."""

from marshmallow import EXCLUDE, Schema, fields, post_load


class StateDefinition:
    """Data model for States."""

    def __init__(
        self,
        id: int,  # noqa: A002
        display_name: str,
        description: str,
        color: str,
        icon: str,
        editable: bool,
    ) -> None:
        """Initialize a State instance.

        Args:
            id (int): Unique identifier for the state.
            display_name (str): Display name of the state.
            description (str): Description of the state.
            color (str): Color code of the state.
            icon (str): Icon of the state.
            editable (bool): Whether the state is editable.
        """
        self.id = id
        self.display_name = display_name
        self.description = description
        self.color = color
        self.icon = icon
        self.editable = editable
        # updated_by and updated_at are set on the server


class StateDefinitionSchema(Schema):
    """Marshmallow schema for serializing and deserializing State objects."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    display_name = fields.Str()
    description = fields.Str()
    color = fields.Str()
    icon = fields.Str()
    editable = fields.Bool()
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @post_load
    def make(self, data: dict, **kwargs) -> StateDefinition:  # noqa: ARG002, ANN003
        """Create a AiProvider instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing local AI modelr attributes.
            **kwargs: Additional keyword arguments.

        Returns:
            AiProvider: An instance of AiProvider initialized with the provided data.
        """
        return StateDefinition(**data)


class StateTypeDefinition:
    """Data model for State Type Definitions."""

    def __init__(
        self,
        id: int,  # noqa: A002
        entity_type: str,
        state_id: int,
        state_type: str,
        is_active: bool,
        editable: bool,
        sort_order: int,
    ) -> None:
        """Initialize a StateTypeDefinition instance.

        Args:
            id (int): Unique identifier for the state type.
            entity_type (str): Entity type of the state.
            state_id (int): State ID.
            state_type (str): State type.
            is_active (bool): Whether the state is active.
            editable (bool): Whether the state is editable.
            sort_order (int): Sort order of the state.
        """
        self.id = id
        self.entity_type = entity_type
        self.state_id = state_id
        self.state_type = state_type
        self.is_active = is_active
        self.editable = editable
        self.sort_order = sort_order
        # updated_by and updated_at are set on the server


class StateTypeDefinitionSchema(Schema):
    """Marshmallow schema for serializing and deserializing State Type objects."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    entity_type = fields.Str()
    state_id = fields.Int()
    state_type = fields.Str(load_default="normal")
    is_active = fields.Bool(load_default=True)
    editable = fields.Bool(load_default=True)
    sort_order = fields.Int(load_default=0)
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    state = fields.Nested(StateDefinitionSchema)

    @post_load
    def make(self, data: dict, **kwargs) -> StateTypeDefinition:  # noqa: ARG002, ANN003
        """Create a StateTypeDefinition instance from the deserialized data.

        Args:
            data (dict): The deserialized data containing StateTypeDefinition.
            **kwargs: Additional keyword arguments.

        Returns:
            StateTypeDefinition: An instance of StateTypeDefinition initialized with the provided data.
        """
        return StateTypeDefinition(**data)
