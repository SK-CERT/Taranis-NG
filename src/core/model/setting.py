"""Settings model."""

from datetime import datetime
from managers.db_manager import db
from sqlalchemy import or_
from shared.schema.setting import SettingSchema, SettingValueSchema


class Setting(db.Model):
    """
    Model class for settings.

    Attributes:
        id (int): Primary key.
        key (str): Unique key for the setting.
        type (str): Type of the setting.
        value (str): Value of the setting.
        default_val (str): Default value of the setting.
        description (str): Description of the setting.
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
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.String())

    def __init__(self, key, type, value, default_val, description):
        """
        Initialize a new Setting instance.

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
    def add_new(cls, data):
        """
        Add a new setting to the database.

        Args:
            data (dict): Data for the new setting.
        """
        schema = SettingSchema()
        setting = schema.load(data)
        db.session.add(setting)
        db.session.commit()

    @classmethod
    def update_value(cls, setting_id, data, user_name):
        """
        Update the value of an existing setting.

        Args:
            setting_id (int): ID of the setting to update.
            data (dict): Data to update the setting with.
            user_mame (str): User who is updating the setting.
        """
        schema = SettingValueSchema()
        updated_setting = schema.load(data)
        setting = db.session.get(cls, setting_id)
        setting.value = updated_setting.value
        setting.updated_by = user_name
        setting.updated_at = datetime.now()
        db.session.commit()

    @classmethod
    def update(cls, setting_id, data, user_name):
        """
        Update an existing setting.

        Args:
            setting_id (int): ID of the setting to update.
            data (dict): Data to update the setting with.
            user_mame (str): User who is updating the setting.
        """
        schema = SettingSchema()
        updated_setting = schema.load(data)
        setting = db.session.get(cls, setting_id)
        setting.key = updated_setting.key
        setting.type = updated_setting.type
        setting.value = updated_setting.value
        setting.default_val = updated_setting.default_val
        setting.description = updated_setting.description
        setting.updated_by = user_name
        setting.updated_at = datetime.now()
        db.session.commit()

    @classmethod
    def delete(cls, setting_id):
        """
        Delete a setting from the database.

        Args:
            setting_id (int): ID of the setting to delete.
        """
        setting = db.session.get(cls, setting_id)
        db.session.delete(setting)
        db.session.commit()

    @classmethod
    def find(cls, setting_id):
        """
        Find a setting by its ID.

        Args:
            setting_id (int): ID of the setting to find.

        Returns:
            Setting: The found setting.
        """
        setting = db.session.get(cls, setting_id)
        return setting

    @classmethod
    def find_by_key(cls, key):
        """
        Find a setting by its key.

        Args:
            key (str): Key of the setting to find.

        Returns:
            Setting: The found setting.
        """
        setting = cls.query.filter_by(key=key).first()
        return setting

    @classmethod
    def get_all(cls):
        """
        Get all settings ordered by description.

        Returns:
            list: List of all settings.
        """
        return cls.query.order_by(db.asc(Setting.description)).all()

    @classmethod
    def get(cls, search):
        """
        Get settings based on a search query.

        Args:
            search (str): Search query.

        Returns:
            tuple: List of settings and the count of settings.
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search + "%"
            query = query.filter(or_(Setting.value.ilike(search_string), Setting.description.ilike(search_string)))

        return query.order_by(db.asc(Setting.description)).all(), query.count()

    @classmethod
    def get_json(cls, setting_id):
        """
        Get setting detail in JSON format.

        Args:
            setting_id (int): ID of the setting to get.

        Returns:
            dict: Setting detail in JSON format.
        """
        setting = cls.find(setting_id)
        schema = SettingSchema()
        return schema.dump(setting)

    @classmethod
    def get_all_json(cls, search):
        """
        Get all settings in JSON format based on a search query.

        Args:
            search (str): Search query.

        Returns:
            dict: Dictionary containing total count and list of settings in JSON format.
        """
        settings, count = cls.get(search)
        schema = SettingSchema(many=True)
        return {"total_count": count, "items": schema.dump(settings)}
