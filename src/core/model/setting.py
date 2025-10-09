"""Settings model."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.setting import Setting, SettingUser
    from model.user import User
    from sqlalchemy.orm import Query

from datetime import datetime

from managers.db_manager import db
from sqlalchemy import case, func, or_

from shared.common import TZ
from shared.schema.setting import SettingSchema, SettingValueSchema


class SettingUser(db.Model):
    """Model class for user settings.

    Attributes:
        id (int): Primary key.
        settings_id (int): Foreign key to the settings table.
        user_id (int): Foreign key to the users table.
        value (str): Value of the setting.
        updated_at (datetime): Timestamp of the last update.
    """

    __tablename__ = "settings_user"
    id = db.Column(db.Integer, primary_key=True)
    settings_id = db.Column(db.Integer, db.ForeignKey("settings.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    value = db.Column(db.String(), nullable=False)
    updated_at = db.Column(db.DateTime)

    def __init__(self, settings_id: int, user_id: int, value: str) -> None:
        """Initialize a new SettingUser instance.

        Args:
            settings_id (int): Foreign key to the settings table.
            user_id (int): Foreign key to the users table.
            value (str): Value of the setting.
        """
        self.settings_id = settings_id
        self.user_id = user_id
        self.value = value
        self.updated_at = None

    @classmethod
    def add_new(cls, setting_id: int, user_id: int, value: str) -> SettingUser:
        """Add a new user setting to the database.

        Args:
            setting_id (int): ID of the setting to associate with the user.
            user_id (int): ID of the user who owns the setting.
            value (str): Value for the new setting.
        """
        record = SettingUser(setting_id, user_id, value)
        record.updated_at = datetime.now(TZ)
        db.session.add(record)
        db.session.commit()

    @classmethod
    def update_value(cls, setting_id: int, user_id: int, data: dict) -> bool:
        """Update the value of an existing user setting.

        Args:
            setting_id (int): ID of the setting to update.
            user_id (int): ID of the user who owns the setting.
            data (dict): Data to update the user setting with.
        """
        schema = SettingValueSchema()
        updated_record = schema.load(data)
        if updated_record.is_global:
            return False

        record = db.session.get(cls, updated_record.user_setting_id)
        if record:
            record.value = updated_record.value
            record.updated_at = datetime.now(TZ)
            db.session.commit()
            return True
        # If the setting is global or record does not exist, add a new user setting
        cls.add_new(setting_id, user_id, updated_record.value)
        return True

    @classmethod
    def find(cls, user_setting_id: int) -> SettingUser:
        """Find a user setting by its ID.

        Args:
            user_setting_id (int): ID of the user setting to find.

        Returns:
            SettingUser: The found user setting.
        """
        return db.session.get(cls, user_setting_id)


class Setting(db.Model):
    """Model class for settings.

    Attributes:
        id (int): Primary key.
        key (str): Unique key for the setting.
        type (str): Type of the setting.
        value (str): Value of the setting.
        default_val (str): Default value of the setting.
        description (str): Description of the setting.
        is_global (bool): Indicates if the setting is global.
        updated_at (datetime): Timestamp of the last update.
        updated_by (str): User who last updated the setting.
    """

    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(40), unique=True, nullable=False)
    type = db.Column(db.String(1), unique=True, nullable=False)
    value = db.Column(db.String(), nullable=False)
    default_val = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)
    is_global = db.Column(db.Boolean(), nullable=False, default=True)
    options = db.Column(db.String())
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.String())
    user_settings = db.relationship(SettingUser, lazy="joined")

    @property
    def user_setting_id(self) -> int:
        """Return id from user setting table."""
        return self.user_settings.id if self.user_settings else None

    def __init__(
        self,
        key: str,
        type: str,  # noqa: A002
        value: str,
        default_val: str,
        description: str,
    ) -> None:
        """Initialize a new Setting instance.

        Args:
            key (str): Unique key for the setting.
            type (str): Type of the setting.
            value (str): Value of the setting.
            default_val (str): Default value of the setting.
            description (str): Description of the setting.
        """
        self.id = None
        self.key = key
        self.type = type
        self.value = value
        self.default_val = default_val
        self.description = description
        self.updated_at = None
        self.updated_by = None

    @classmethod
    def add_new(cls, data: dict) -> None:
        """Add a new setting to the database.

        Args:
            data (dict): Data for the new setting.
        """
        schema = SettingSchema()
        record = schema.load(data)
        record.is_global = True
        record.updated_at = datetime.now(TZ)
        db.session.add(record)
        db.session.commit()

    @classmethod
    def update_value(cls, setting_id: int, user_name: str, data: dict) -> None:
        """Update the value of an existing setting.

        Args:
            setting_id (int): ID of the setting to update.
            data (dict): Data to update the setting with.
            user_name (str): User who is updating the setting.
        """
        schema = SettingValueSchema()
        updated_record = schema.load(data)
        record = db.session.get(cls, setting_id)
        record.value = updated_record.value
        record.updated_by = user_name
        record.updated_at = datetime.now(TZ)
        db.session.commit()

    @classmethod
    def _get_main_query(
        cls,
        user: User,
        search_str: str | None,
        search_id: int | None,
        search_user_settings_id: int | None,
        search_key: str | None,
    ) -> Query:
        """Get main settings query.

        Args:
            query: Base query to build upon.
            user (User): The user making the request.
            search_str (str): Search query.
            search_id (int): ID of the setting to find.
            search_user_settings_id (int): ID of the user setting to find.
            search_key (str): Key of the user setting to find.

        Returns:
            query: The constructed query.
        """
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = None
            user_id = 0

        query = cls.query.with_entities(
            Setting.id,
            SettingUser.id.label("user_setting_id"),
            Setting.key,
            Setting.type,
            func.coalesce(SettingUser.value, Setting.value).label("value"),
            Setting.default_val,
            Setting.description,
            Setting.is_global,
            Setting.options,
            func.coalesce(SettingUser.updated_at, Setting.updated_at).label("updated_at"),
            case((SettingUser.id == None, Setting.updated_by), else_=user_name).label("updated_by"),  # noqa: E711
        )
        query = query.outerjoin(SettingUser, (SettingUser.settings_id == Setting.id) & (SettingUser.user_id == user_id))

        if search_str:
            search_string = f"%{search_str}%"
            query = query.filter(
                or_(
                    func.coalesce(SettingUser.value, Setting.default_val).ilike(search_string),
                    Setting.description.ilike(search_string),
                ),
            )
        if search_id:
            query = query.filter(Setting.id == search_id)
        if search_user_settings_id:
            query = query.filter(SettingUser.id == search_user_settings_id)
        if search_key:
            query = query.filter(Setting.key == search_key)

        return query.order_by(db.asc(Setting.description))

    @classmethod
    def delete(cls, setting_id: int) -> None:
        """Delete a setting from the database.

        Args:
            setting_id (int): ID of the setting to delete.
        """
        record = db.session.get(cls, setting_id)
        db.session.delete(record)
        db.session.commit()

    @classmethod
    def find(cls, user: User, setting_id: int) -> Setting:
        """Find a setting by its ID.

        Args:
            user (User): The user making the request.
            setting_id (int): ID of the setting to find.

        Returns:
            Setting: The found setting.
        """
        query = cls._get_main_query(user, None, setting_id, None, None)
        return query.first()

    @classmethod
    def get_all(cls, user: User, search: str) -> list[Setting]:
        """Get all settings ordered by description.

        Returns:
            list: List of all settings.
        """
        query = cls._get_main_query(user, search, None, None, None)
        return query.all()

    @classmethod
    def get_json(cls, user: User, setting_id: int) -> dict:
        """Get setting detail in JSON format.

        Args:
            user (User): The user making the request.
            setting_id (int): ID of the setting to get.

        Returns:
            dict: Setting detail in JSON format.
        """
        record = cls.find(user, setting_id)
        schema = SettingSchema()
        return schema.dump(record)

    @classmethod
    def get_all_json(cls, user: User, search: str) -> dict:
        """Get all settings in JSON format based on a search query.

        Args:
            user (User): The user making the request.
            search (str): Search query.

        Returns:
            dict: Dictionary containing list of settings in JSON format.
        """
        records = cls.get_all(user, search)
        schema = SettingSchema(many=True)
        return schema.dump(records)

    @classmethod
    def get_setting(cls, user: User, key: str, default_value: str = "") -> str:
        """Get setting value by key.

        Args:
            user (User): The user making the request.
            key (str): Key of the setting to get.
            default_value (str): Default value if setting is not found.

        Returns:
            str: Value of the setting or default value if not found.
        """
        query = cls._get_main_query(user, None, None, key)
        record = query.first()
        if not record:
            return default_value
        return record.value

    @classmethod
    def get_setting_bool(cls, user: User, key: str, default_value: bool = False) -> bool:
        """Get boolean setting value by key.

        Args:
            user (User): The user making the request.
            key (str): Key of the setting to get.
            default_value (bool): Default value if setting is not found.

        Returns:
            bool: Value of the setting or default value if not found.
        """
        val = cls.get_setting(user, key, "true" if default_value else "false")
        return val is not None and val.lower().strip() == "true"
