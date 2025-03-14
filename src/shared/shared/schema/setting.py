"""Module for Settings schema."""

from marshmallow import Schema, fields, post_load, EXCLUDE


class SettingValueSchema(Schema):
    """
    Schema for validating and deserializing SettingValue objects.

    Attributes:
        id (str): The ID of the setting value.
        value (str): The value of the setting.
    """

    class Meta:
        """Meta class for the schema.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Setting it to EXCLUDE will ignore any unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Str()
    value = fields.Str()

    @post_load
    def make_setting(self, data, **kwargs):
        """
        Create a SettingValue instance from deserialized data.

        Args:
            data (dict): Deserialized data.

        Returns:
            SettingValue: The created SettingValue instance.
        """
        return SettingValue(**data)


class SettingValue:
    """
    Class representing a setting value.

    Attributes:
        id (str): The ID of the setting value.
        value (str): The value of the setting.
    """

    def __init__(self, id, value):
        """
        Initialize a SettingValue instance.

        Args:
            id (str): The ID of the setting value.
            value (str): The value of the setting.
        """
        self.id = id
        self.value = value


class SettingSchema(Schema):
    """
    Schema for validating and deserializing Setting objects.

    Attributes:
        id (str): The ID of the setting.
        key (str): The key of the setting.
        type (str): The type of the setting.
        value (str): The value of the setting.
        default_val (str): The default value of the setting.
        description (str): The description of the setting.
        updated_at (str): The timestamp of the last update.
        updated_by (str): The user who last updated the setting.
    """

    class Meta:
        """Meta class for the schema.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Setting it to EXCLUDE will ignore any unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Str()
    key = fields.Str()
    type = fields.Str()
    value = fields.Str()
    default_val = fields.Str()
    description = fields.Str()
    updated_at = fields.Str()
    updated_by = fields.Str()

    @post_load
    def make_setting(self, data, **kwargs):
        """
        Create a Setting instance from deserialized data.

        Args:
            data (dict): Deserialized data.

        Returns:
            Setting: The created Setting instance.
        """
        return Setting(**data)


class Setting:
    """
    Class representing a setting.

    Attributes:
        id (str): The ID of the setting.
        key (str): The key of the setting.
        type (str): The type of the setting.
        value (str): The value of the setting.
        default_val (str): The default value of the setting.
        description (str): The description of the setting.
        updated_at (str): The timestamp of the last update.
        updated_by (str): The user who last updated the setting.
    """

    def __init__(self, id, key, type, value, default_val, description, updated_at, updated_by):
        """
        Initialize a Setting instance.

        Args:
            id (str): The ID of the setting.
            key (str): The key of the setting.
            type (str): The type of the setting.
            value (str): The value of the setting.
            default_val (str): The default value of the setting.
            description (str): The description of the setting.
            updated_at (str): The timestamp of the last update.
            updated_by (str): The user who last updated the setting.
        """
        self.id = id
        self.key = key
        self.type = type
        self.value = value
        self.default_val = default_val
        self.description = description
        self.updated_at = updated_at
        self.updated_by = updated_by
