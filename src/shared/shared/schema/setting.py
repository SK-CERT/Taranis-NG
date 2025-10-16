"""Module for Settings schema."""

import datetime

from marshmallow import EXCLUDE, Schema, fields, post_load


class SettingValue:
    """Class representing a setting value.

    Attributes:
        id (str): The ID of the setting value.
        user_setting_id (int): The ID of the associated user setting.
        value (str): The value of the setting.
        is_global (bool): Indicates if the setting is global.
    """

    def __init__(
        self,
        id: int,  # noqa: A002
        user_setting_id: int,
        value: str,
        is_global: bool,
    ) -> None:
        """Initialize a SettingValue instance.

        Args:
            id (str): The ID of the setting value.
            user_setting_id (int): The ID of the associated user setting.
            value (str): The value of the setting.
            is_global (bool): Indicates if the setting is global.
        """
        self.id = id
        self.user_setting_id = user_setting_id
        self.value = value
        self.is_global = is_global


class SettingValueSchema(Schema):
    """Schema for validating and deserializing SettingValue objects.

    Attributes:
        id (int): The ID of the setting value.
        user_setting_id (int): The ID of the associated user setting.
        value (str): The value of the setting.
        is_global (bool): Indicates if the setting is global.
    """

    class Meta:
        """Meta class for the schema.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Setting it to EXCLUDE will ignore any unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Int()
    user_setting_id = fields.Int(load_default=None, allow_none=True)
    value = fields.Str()
    is_global = fields.Bool()

    @post_load
    def make_setting(self, data: dict, **kwargs) -> SettingValue:  # noqa: ANN003, ARG002
        """Create a SettingValue instance from deserialized data.

        Args:
            data (dict): Deserialized data.
            **kwargs: Additional arguments.

        Returns:
            SettingValue: The created SettingValue instance.
        """
        return SettingValue(**data)


class Setting:
    """Class representing a setting."""

    def __init__(
        self,
        id: int,  # noqa: A002
        user_setting_id: int,
        key: str,
        type: str,  # noqa: A002
        value: str,
        default_val: str,
        description: str,
        is_global: bool,
        options: str,
        updated_at: datetime,
        updated_by: str,
    ) -> None:
        """Initialize a global Setting instance.

        Args:
            id (int): The ID of the setting.
            user_setting_id (int): The ID of the associated user setting.
            key (str): The key of the setting.
            type (str): The type of the setting.
            value (str): The value of the setting.
            default_val (str): The default value of the setting.
            description (str): The description of the setting.
            is_global (bool): Indicates if the setting is global.
            options (str): The options for the setting.
            updated_at (datetime): The timestamp of the last update.
            updated_by (str): The user who last updated the setting.
        """
        self.id = id
        self.user_setting_id = user_setting_id
        self.key = key
        self.type = type
        self.value = value
        self.default_val = default_val
        self.description = description
        self.is_global = is_global
        self.options = options
        self.updated_at = updated_at
        self.updated_by = updated_by


class SettingSchema(Schema):
    """Schema for validating and deserializing Setting objects.

    Attributes:
        id (str): The ID of the setting.
        user_setting_id (int): The ID of the associated user setting.
        key (str): The key of the setting.
        type (str): The type of the setting.
        value (str): The value of the setting.
        default_val (str): The default value of the setting.
        description (str): The description of the setting.
        is_global (bool): Indicates if the setting is global.
        options (str): The options for the setting.
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

    id = fields.Int()
    user_setting_id = fields.Int(load_default=None, allow_none=True)
    key = fields.Str()
    type = fields.Str()
    value = fields.Str()
    default_val = fields.Str()
    description = fields.Str()
    is_global = fields.Bool()
    options = fields.Str()
    updated_at = fields.Str(load_default=None, allow_none=True)
    updated_by = fields.Str()

    @post_load
    def make_setting(self, data: dict, **kwargs) -> Setting:  # noqa: ANN003, ARG002
        """Create a Setting instance from deserialized data.

        Args:
            data (dict): Deserialized data.
            **kwargs: Additional arguments.

        Returns:
            Setting: The created Setting instance.
        """
        return Setting(**data)
