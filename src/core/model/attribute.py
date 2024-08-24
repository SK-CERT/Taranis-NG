"""This module contains the model for the attribute and attribute_enum tables.

Returns:
    _description_
"""

import os
from xml.etree.ElementTree import iterparse
from marshmallow import fields, post_load
from sqlalchemy import orm, func, or_, and_

from managers.log_manager import logger
from managers.db_manager import db
from shared.schema.attribute import AttributeBaseSchema, AttributeEnumSchema, AttributeType, AttributeValidator, AttributePresentationSchema


class NewAttributeEnumSchema(AttributeEnumSchema):
    """Class for NewAttributeEnumSchema.

    Arguments:
        AttributeEnumSchema -- Schema for attribute enums.
    """

    @post_load
    def make_attribute_enum(self, data, **kwargs):
        """Create a new attribute enum.

        Arguments:
            data (dict): The data for the attribute enum.

        Returns:
            AttributeEnum: The created attribute enum.
        """
        return AttributeEnum(**data)


class AttributeEnum(db.Model):
    """Class for AttributeEnum.

    Arguments:
        db -- The database object.
    """

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)
    value = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    imported = db.Column(db.Boolean, default=False)

    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute = db.relationship("Attribute", back_populates="attribute_enums")

    def __init__(self, id, index, value, description):
        """Initialize the attribute enum.

        Arguments:
            id (int): ID of the attribute enum.
            index (int): Index of the attribute enum.
            value (str): Value of the attribute enum.
            description (str): Description of the attribute enum.
        """
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.index = index
        self.value = value
        self.description = description

    @classmethod
    def count_for_attribute(cls, attribute_id):
        """
        Count the number of attribute enums for an attribute.

        Arguments:
            attribute_id (int): ID of the attribute.

        Returns:
            int: Number of attribute enums.
        """
        return cls.query.filter_by(attribute_id=attribute_id).count()

    @classmethod
    def get_all_for_attribute(cls, attribute_id):
        """Get all attribute enums for an attribute.

        Arguments:
            attribute_id (int): The ID of the attribute.

        Returns:
            list: A list of attribute enums for the specified attribute, ordered by index.
        """
        return cls.query.filter_by(attribute_id=attribute_id).order_by(db.asc(AttributeEnum.index)).all()

    @classmethod
    def get_for_attribute(cls, attribute_id, search, offset, limit):
        """
        Get attribute enums for an attribute.

        This method retrieves attribute enums for a given attribute ID, with optional search, offset, and limit parameters.

        Arguments:
            attribute_id (int): ID of the attribute.
            search (str): Search string.
            offset (int): Offset for pagination.
            limit (int): Limit for pagination.

        Returns:
            tuple: A tuple containing two elements:
                - A list of attribute enums matching the criteria.
                - The total count of attribute enums matching the criteria.
        """
        query = cls.query.filter_by(attribute_id=attribute_id)
        if search:
            search_string = "%" + search + "%"
            query = query.filter(or_(AttributeEnum.value.ilike(search_string), AttributeEnum.description.ilike(search_string)))

        query = query.order_by(db.asc(AttributeEnum.index))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def find_by_value(cls, attribute_id, value):
        """
        Find an attribute enum by value.

        Arguments:
            attribute_id (int): ID of the attribute.
            value (str): Value of the attribute enum.

        Returns:
            AttributeEnum: The attribute enum matching the given value, or None if not found.
        """
        return cls.query.filter_by(attribute_id=attribute_id).filter(func.lower(AttributeEnum.value) == value.lower()).first()

    @classmethod
    def get_for_attribute_json(cls, attribute_id, search, offset, limit):
        """
        Retrieve attribute enums in JSON format for a given attribute ID.

        Args:
            attribute_id (int): The ID of the attribute.
            search (str): The search query.
            offset (int): The offset for pagination.
            limit (int): The limit for pagination.

        Returns:
            dict: A dictionary containing the total count and a list of attribute enums in JSON format.
        """
        attribute_enums, total_count = cls.get_for_attribute(attribute_id, search, offset, limit)
        attribute_enums_schema = AttributeEnumSchema(many=True)
        return {"total_count": total_count, "items": attribute_enums_schema.dump(attribute_enums)}

    @classmethod
    def delete_for_attribute(cls, attribute_id):
        """
        Delete all records associated with the given attribute ID.

        Args:
            attribute_id (int): The ID of the attribute.

        Returns:
            None
        """
        cls.query.filter_by(attribute_id=attribute_id).delete()
        db.session.commit()

    @classmethod
    def delete_imported_for_attribute(cls, attribute_id):
        """
        Delete imported attributes for a given attribute ID.

        Args:
            attribute_id (int): The ID of the attribute.

        Returns:
            None
        """
        cls.query.filter_by(attribute_id=attribute_id, imported=True).delete()
        db.session.commit()

    @classmethod
    def add(cls, attribute_id, data):
        """
        Add attribute enums to the database.

        Args:
            attribute_id (int): The ID of the attribute.
            data (dict): The data containing the attribute enums.

        Returns:
            None
        """
        count = 0
        if data["delete_existing"] is True:
            cls.delete_for_attribute(attribute_id)
        else:
            count = cls.count_for_attribute(attribute_id)

        attribute_enums_schema = NewAttributeEnumSchema(many=True)
        attribute_enums = attribute_enums_schema.load(data["items"])

        for attribute_enum in attribute_enums:
            original_attribute_enum = cls.find_by_value(attribute_id, attribute_enum.value)
            if original_attribute_enum is None:
                attribute_enum.attribute_id = attribute_id
                attribute_enum.index = count
                count += 1
                db.session.add(attribute_enum)
            else:
                original_attribute_enum.value = attribute_enum.value
                original_attribute_enum.description = attribute_enum.description

        db.session.commit()

    @classmethod
    def update(cls, enum_id, data):
        """
        Update the attribute enum with the given enum_id using the provided data.

        Args:
            enum_id (int): The ID of the attribute enum to update.
            data (dict): The data containing the updated attribute enum values.

        Returns:
            None
        """
        attribute_enums_schema = NewAttributeEnumSchema(many=True)
        attribute_enums = attribute_enums_schema.load(data)
        for attribute_enum in attribute_enums:
            original_attribute_enum = cls.query.get(enum_id)
            original_attribute_enum.value = attribute_enum.value
            original_attribute_enum.description = attribute_enum.description
            original_attribute_enum.imported = False

        db.session.commit()

    @classmethod
    def delete(cls, attribute_enum_id):
        """
        Delete an attribute by its enum ID.

        Args:
            attribute_enum_id (int): The enum ID of the attribute to be deleted.
        """
        db.session.delete(cls.query.get(attribute_enum_id))
        db.session.commit()


class NewAttributeSchema(AttributeBaseSchema):
    """Schema for a new attribute.

    This schema extends the AttributeBaseSchema and defines the structure
    and validation rules for a new attribute.

    Arguments:
        AttributeBaseSchema -- The base schema for attributes.

    Returns:
        An instance of the NewAttributeSchema class.
    """

    attribute_enums = fields.Nested(NewAttributeEnumSchema, many=True)

    @post_load
    def make_attribute(self, data, **kwargs):
        """Create an Attribute instance from the provided data.

        This method is called after the data has been loaded and performs
        any additional processing or validation before creating the
        Attribute instance.

        Arguments:
            data (dict): The loaded data.

        Returns:
            Attribute: An instance of the Attribute class.
        """
        return Attribute(**data)


class Attribute(db.Model):
    """Represents an attribute in the system.

    Args:
        db (object): The database object.

    Attributes:
        id (int): The ID of the attribute.
        name (str): The name of the attribute.
        description (str): The description of the attribute.
        type (AttributeType): The type of the attribute.
        default_value (str): The default value of the attribute.
        validator (AttributeValidator): The validator for the attribute.
        validator_parameter (str): The parameter for the validator.
        attribute_enums (list): The list of attribute enums.
        title (str): The title of the attribute.
        subtitle (str): The subtitle of the attribute.
        tag (str): The tag of the attribute.

    Methods:
        __init__: Initializes an Attribute object.
        reconstruct: Reconstructs the attribute object.
        get_all: Retrieves all attributes.
        find_by_type: Finds an attribute by type.
        get: Retrieves attributes based on search criteria.
        get_all_json: Retrieves all attributes in JSON format.
        create_attribute: Creates a new attribute.
        add_attribute: Adds a new attribute.
        update: Updates an attribute.
        delete_attribute: Deletes an attribute.
        load_cve_from_file: Loads CVE attributes from a file.
        load_cpe_from_file: Loads CPE attributes from a file.
        load_cwe_from_file: Loads CWE attributes from a file.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(AttributeType))
    default_value = db.Column(db.String())

    validator = db.Column(db.Enum(AttributeValidator))
    validator_parameter = db.Column(db.String())

    attribute_enums = db.relationship(
        "AttributeEnum",
        primaryjoin=and_(id == AttributeEnum.attribute_id, or_(type == AttributeType.RADIO, type == AttributeType.ENUM)),
        back_populates="attribute",
        lazy="subquery",
    )

    def __init__(self, id, name, description, type, default_value, validator, validator_parameter, attribute_enums):
        """Initialize an Attribute object.

        Args:
            id (int): The ID of the attribute.
            name (str): The name of the attribute.
            description (str): The description of the attribute.
            type (str): The type of the attribute.
            default_value (str): The default value of the attribute.
            validator (str): The validator for the attribute.
            validator_parameter (str): The parameter for the validator.
            attribute_enums (list): The list of attribute enums.

        Returns:
            None
        """
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter
        self.attribute_enums = attribute_enums
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        """
        Reconstructs the attribute object.

        This method is called when the attribute object is loaded from the database.
        It sets the title and subtitle attributes based on the name and description attributes.
        It also sets the tag attribute based on the type of the attribute.

        Returns:
            None
        """
        self.title = self.name
        self.subtitle = self.description

        switcher = {
            AttributeType.STRING: "mdi-form-textbox",
            AttributeType.NUMBER: "mdi-numeric",
            AttributeType.BOOLEAN: "mdi-checkbox-marked-outline",
            AttributeType.RADIO: "mdi-radiobox-marked",
            AttributeType.ENUM: "mdi-format-list-bulleted-type",
            AttributeType.TEXT: "mdi-form-textarea",
            AttributeType.RICH_TEXT: "mdi-format-font",
            AttributeType.DATE: "mdi-calendar-blank-outline",
            AttributeType.TIME: "clock-outline",
            AttributeType.DATE_TIME: "calendar-clock",
            AttributeType.LINK: "mdi-link",
            AttributeType.ATTACHMENT: "mdi-paperclip",
            AttributeType.TLP: "mdi-traffic-light",
            AttributeType.CPE: "mdi-laptop",
            AttributeType.CVE: "mdi-hazard-lights",
            AttributeType.CWE: "mdi-shield-alert",
            AttributeType.CVSS: "mdi-counter",
        }
        self.tag = switcher.get(self.type, "mdi-textbox")

    @classmethod
    def get_all(cls):
        """Retrieve all attributes.

        Returns:
            list: A list of all attributes.
        """
        return cls.query.order_by(Attribute.name).all()

    @classmethod
    def find_by_type(cls, attribute_type):
        """Find an attribute by type.

        Args:
            attribute_type (AttributeType): The type of the attribute.

        Returns:
            Attribute: The attribute object.
        """
        return cls.query.filter_by(type=attribute_type).first()

    @classmethod
    def get(cls, search):
        """Retrieve attributes based on search criteria.

        Args:
            search (str): The search criteria.

        Returns:
            tuple: A tuple containing the list of attributes and the total count.
        """
        query = cls.query

        if search is not None:
            search_string = "%" + search.lower() + "%"
            query = query.filter(or_(func.lower(Attribute.name).like(search_string), func.lower(Attribute.description).like(search_string)))

        return query.order_by(db.asc(Attribute.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        """Retrieve all attributes in JSON format.

        Args:
            search (str): The search criteria.

        Returns:
            dict: A dictionary containing the total count and the items in JSON format.
        """
        attributes, total_count = cls.get(search)
        for attribute in attributes:
            if attribute.type == AttributeType.CPE or attribute.type == AttributeType.CVE:
                attribute.attribute_enums = []
            else:
                attribute.attribute_enums = AttributeEnum.get_all_for_attribute(attribute.id)

        attribute_schema = AttributePresentationSchema(many=True)
        return {"total_count": total_count, "items": attribute_schema.dump(attributes)}

    @classmethod
    def create_attribute(cls, attribute):
        """Create a new attribute.

        Args:
            attribute (Attribute): The attribute object.

        Returns:
            None
        """
        db.session.add(attribute)
        db.session.commit()

        for attribute_enum in attribute.attribute_enums:
            attribute_enum.attribute_id = attribute.id
            db.session.add(attribute_enum)

        attribute.attribute_enums = []

        db.session.commit()

    @classmethod
    def add_attribute(cls, attribute_data):
        """Add a new attribute.

        Args:
            attribute_data (dict): The attribute data.

        Returns:
            None
        """
        attribute_schema = NewAttributeSchema()
        attribute = attribute_schema.load(attribute_data)
        db.session.add(attribute)
        db.session.commit()

        count = 0
        for attribute_enum in attribute.attribute_enums:
            attribute_enum.attribute_id = attribute.id
            attribute_enum.index = count
            count += 1
            db.session.add(attribute_enum)

        attribute.attribute_enums = []

        db.session.commit()

    @classmethod
    def update(cls, attribute_id, data):
        """Update an attribute.

        Args:
            attribute_id (int): The ID of the attribute.
            data (dict): The updated attribute data.

        Returns:
            None
        """
        schema = NewAttributeSchema()
        updated_attribute = schema.load(data)
        attribute = cls.query.get(attribute_id)
        attribute.name = updated_attribute.name
        attribute.description = updated_attribute.description
        attribute.type = updated_attribute.type
        attribute.default_value = updated_attribute.default_value
        attribute.validator = updated_attribute.validator
        attribute.validator_parameter = updated_attribute.validator_parameter
        db.session.commit()

    @classmethod
    def delete_attribute(cls, id):
        """Delete an attribute.

        Args:
            id (int): The ID of the attribute.

        Returns:
            None
        """
        attribute = cls.query.get(id)
        AttributeEnum.delete_for_attribute(id)
        db.session.delete(attribute)
        db.session.commit()

    @classmethod
    def load_cve_from_file(cls, file_path):
        """Load CVE attributes from a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            None
        """
        attribute = cls.query.filter_by(type=AttributeType.CVE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)

        item_count = 0
        block_item_count = 0
        desc = ""
        for event, element in iterparse(file_path, events=("start", "end")):
            if event == "end":
                if element.tag == "{http://cve.mitre.org/cve/downloads/1.0}desc":
                    desc = element.text
                elif element.tag == "{http://cve.mitre.org/cve/downloads/1.0}item":
                    attribute_enum = AttributeEnum(None, item_count, element.attrib["name"], desc)
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    desc = ""
                    if block_item_count == 1000:
                        logger.log_critical("Processed CVE items: " + str(item_count))
                        block_item_count = 0
                        db.session.commit()

        logger.log_critical("Processed CVE items: " + str(item_count))
        db.session.commit()

    @classmethod
    def load_cpe_from_file(cls, file_path):
        """Load CPE attributes from a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            None
        """
        attribute = cls.query.filter_by(type=AttributeType.CPE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)

        item_count = 0
        block_item_count = 0
        desc = ""
        for event, element in iterparse(file_path, events=("start", "end")):
            if event == "end":
                if element.tag == "{http://cpe.mitre.org/dictionary/2.0}title":
                    desc = element.text
                elif element.tag == "{http://cpe.mitre.org/dictionary/2.0}cpe-item":
                    attribute_enum = AttributeEnum(None, item_count, element.attrib["name"], desc)
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    desc = ""
                    if block_item_count == 1000:
                        logger.log_critical("Processed CPE items: " + str(item_count))
                        block_item_count = 0
                        db.session.commit()

        logger.log_critical("Processed CPE items: " + str(item_count))
        db.session.commit()

    @classmethod
    def load_cwe_from_file(cls, file_path):
        """Load CWE attributes from a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            None
        """
        attribute = cls.query.filter_by(type=AttributeType.CWE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)

        item_count = 0
        block_item_count = 0
        for event, element in iterparse(file_path, events=("start", "end")):
            if event == "end":
                if element.tag == "{http://cwe.mitre.org/cwe-7}Weakness":
                    attribute_enum = AttributeEnum(None, item_count, element.attrib["ID"], element.attrib["Name"])
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    # desc = ""
                    if block_item_count == 1000:
                        logger.log_critical("Processed CWE items: " + str(item_count))
                        block_item_count = 0
                        db.session.commit()

        logger.log_critical("Processed CWE items: " + str(item_count))
        db.session.commit()

    @classmethod
    def load_dictionaries(cls, dict_type):
        """
        Load dictionaries based on the specified dict_type.

        Args:
            dict_type (str): The type of dictionary to load.

        Returns:
            None
        """
        if dict_type == "cve":
            cve_update_file = os.getenv("CVE_UPDATE_FILE")
            if cve_update_file is not None and os.path.exists(cve_update_file):
                Attribute.load_cve_from_file(cve_update_file)

        if dict_type == "cpe":
            cpe_update_file = os.getenv("CPE_UPDATE_FILE")
            if cpe_update_file is not None and os.path.exists(cpe_update_file):
                Attribute.load_cpe_from_file(cpe_update_file)

        if dict_type == "cwe":
            cwe_update_file = os.getenv("CWE_UPDATE_FILE")
            if cwe_update_file is not None and os.path.exists(cwe_update_file):
                Attribute.load_cwe_from_file(cwe_update_file)
