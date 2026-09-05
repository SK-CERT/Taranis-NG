"""This module contains the model for the attribute and attribute_enum tables.

Returns:
    _description_
"""

import os
from pathlib import Path

# The dictionary files are large third-party XML downloads, so parse them with the
# hardened iterparse: entity expansion and external references stay refused.
from defusedxml.ElementTree import iterparse
from managers.db_manager import db
from managers.log_manager import logger
from marshmallow import fields, post_load
from shared.schema.attribute import AttributeBaseSchema, AttributeEnumSchema, AttributePresentationSchema, AttributeType, AttributeValidator
from sqlalchemy import and_, func, or_, orm
from sqlalchemy.orm import noload
from tqdm import tqdm

# Dictionary imports run to hundreds of thousands of rows, so they are committed in
# batches rather than in one transaction.
IMPORT_COMMIT_BATCH = 1000


class AttributeInUseError(Exception):
    """Raised when an attribute cannot be deleted because report types still use it."""

    def __init__(self, report_types: list[str]) -> None:
        """Record the report types that block the deletion.

        Args:
            report_types (list[str]): Titles of the report types using the attribute.
        """
        self.report_types = report_types
        super().__init__(f"Attribute is used by report types: {', '.join(report_types)}")


class NewAttributeEnumSchema(AttributeEnumSchema):
    """Class for NewAttributeEnumSchema.

    Args:
        AttributeEnumSchema -- Schema for attribute enums.
    """

    @post_load
    def make_attribute_enum(self, data: dict, **kwargs) -> "AttributeEnum":  # noqa: ANN003, ARG002
        """Create a new attribute enum.

        Args:
            data (dict): The data for the attribute enum.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            AttributeEnum: The created attribute enum.
        """
        return AttributeEnum(**data)


class AttributeEnum(db.Model):
    """Class for AttributeEnum.

    Attributes:
        id (int): The ID of the attribute enum.
        index (int): The index of the attribute enum.
        value (str): The value of the attribute enum.
        description (str): The description of the attribute enum.
        imported (bool): Indicates whether the attribute enum was imported.
        attribute_id (int): The ID of the attribute.
        attribute (Attribute): The attribute object
    """

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)
    value = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    imported = db.Column(db.Boolean, default=False)

    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id"))
    attribute = db.relationship("Attribute", back_populates="attribute_enums")

    # `id` shadows the builtin, but it is the schema field marshmallow unpacks into
    # this constructor, so renaming it would break deserialization.
    def __init__(self, id: int | None, index: int, value: str, description: str) -> None:  # noqa: A002
        """Initialize the attribute enum."""
        if id is not None and id != -1:
            self.id = id
        else:
            self.id = None

        self.index = index
        self.value = value
        self.description = description

    @classmethod
    def count_for_attribute(cls, attribute_id: int) -> int:
        """Count the number of attribute enums for an attribute.

        Args:
            attribute_id (int): ID of the attribute.

        Returns:
            int: Number of attribute enums.
        """
        return cls.query.filter_by(attribute_id=attribute_id).count()

    @classmethod
    def get_for_attribute(cls, attribute_id: int, search: str | None, offset: int, limit: int) -> tuple[list["AttributeEnum"], int]:
        """Get attribute enums for an attribute.

        This method retrieves attribute enums for a given attribute ID, with optional search, offset, and limit parameters.

        Args:
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
            search_string = f"%{search}%"
            query = query.filter(or_(AttributeEnum.value.ilike(search_string), AttributeEnum.description.ilike(search_string)))

        query = query.order_by(db.asc(AttributeEnum.index))

        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def find_by_value(cls, attribute_id: int, value: str) -> "AttributeEnum | None":
        """Find an attribute enum by value.

        Args:
            attribute_id (int): ID of the attribute.
            value (str): Value of the attribute enum.

        Returns:
            AttributeEnum: The attribute enum matching the given value, or None if not found.
        """
        return cls.query.filter_by(attribute_id=attribute_id).filter(func.lower(AttributeEnum.value) == value.lower()).first()

    @classmethod
    def get_for_attribute_json(cls, attribute_id: int, search: str | None, offset: int, limit: int) -> dict:
        """Retrieve attribute enums in JSON format for a given attribute ID.

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
    def delete_for_attribute(cls, attribute_id: int) -> None:
        """Delete all records associated with the given attribute ID.

        Args:
            attribute_id (int): The ID of the attribute.

        Returns:
            None
        """
        cls.query.filter_by(attribute_id=attribute_id).delete()
        db.session.commit()

    @classmethod
    def delete_imported_for_attribute(cls, attribute_id: int) -> None:
        """Delete imported attributes for a given attribute ID.

        Args:
            attribute_id (int): The ID of the attribute.

        Returns:
            None
        """
        cls.query.filter_by(attribute_id=attribute_id, imported=True).delete()
        db.session.commit()

    @classmethod
    def add(cls, attribute_id: int, data: dict) -> None:
        """Add attribute enums to the database.

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
    def update(cls, enum_id: int, data: list) -> None:
        """Update the attribute enum with the given enum_id using the provided data.

        Args:
            enum_id (int): The ID of the attribute enum to update.
            data (dict): The data containing the updated attribute enum values.

        Returns:
            None
        """
        attribute_enums_schema = NewAttributeEnumSchema(many=True)
        attribute_enums = attribute_enums_schema.load(data)
        for attribute_enum in attribute_enums:
            original_attribute_enum = db.session.get(cls, enum_id)
            original_attribute_enum.value = attribute_enum.value
            original_attribute_enum.description = attribute_enum.description
            original_attribute_enum.imported = False

        db.session.commit()

    @classmethod
    def delete(cls, attribute_enum_id: int) -> None:
        """Delete an attribute by its enum ID.

        Args:
            attribute_enum_id (int): The enum ID of the attribute to be deleted.
        """
        db.session.delete(db.session.get(cls, attribute_enum_id))
        db.session.commit()


class NewAttributeSchema(AttributeBaseSchema):
    """Schema for a new attribute.

    This schema extends the AttributeBaseSchema and defines the structure
    and validation rules for a new attribute.

    Args:
        AttributeBaseSchema -- The base schema for attributes.

    Returns:
        An instance of the NewAttributeSchema class.
    """

    # load_default: an update round-tripped from a configuration list row arrives without the
    # constants, which that list no longer ships. Attribute.update ignores them; they are created
    # and edited through /config/attributes/<id>/enums.
    attribute_enums = fields.Nested(NewAttributeEnumSchema, many=True, load_default=list)

    @post_load
    def make_attribute(self, data: dict, **kwargs) -> "Attribute":  # noqa: ANN003, ARG002
        """Create an Attribute instance from the provided data.

        This method is called after the data has been loaded and performs
        any additional processing or validation before creating the
        Attribute instance.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

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
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(AttributeType))
    default_value = db.Column(db.String())

    validator = db.Column(db.Enum(AttributeValidator))
    validator_parameter = db.Column(db.String())

    # `id` and `type` below are the mapped columns declared above, not the builtins;
    # they are named for their database columns and cannot be renamed.
    attribute_enums = db.relationship(
        "AttributeEnum",
        primaryjoin=and_(
            id == AttributeEnum.attribute_id,  # noqa: A003
            or_(type == AttributeType.RADIO, type == AttributeType.ENUM, type == AttributeType.MULTI_CHOICE),  # noqa: A003
        ),
        back_populates="attribute",
        lazy="subquery",
    )

    # `id` and `type` shadow builtins, but both are schema field names that marshmallow
    # unpacks into this constructor, so renaming them would break deserialization.
    # `id` is accepted and ignored on purpose: a new attribute always takes a fresh key.
    def __init__(
        self,
        id: int | None,  # noqa: A002, ARG002
        name: str,
        description: str | None,
        type: AttributeType,  # noqa: A002
        default_value: str | None,
        validator: AttributeValidator | None,
        validator_parameter: str | None,
        attribute_enums: list[AttributeEnum],
    ) -> None:
        """Initialize an Attribute object."""
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
    def reconstruct(self) -> None:
        """Reconstruct the attribute object."""
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
            AttributeType.MULTI_CHOICE: "mdi-checkbox-multiple-marked-outline",
        }
        self.tag = switcher.get(self.type, "mdi-textbox")

    @classmethod
    def get_all(cls) -> list["Attribute"]:
        """Retrieve all attributes.

        Returns:
            list: A list of all attributes.
        """
        return cls.query.order_by(Attribute.name).all()

    @classmethod
    def find_by_type(cls, attribute_type: AttributeType) -> "Attribute | None":
        """Find an attribute by type.

        Args:
            attribute_type (AttributeType): The type of the attribute.

        Returns:
            Attribute: The attribute object.
        """
        return cls.query.filter_by(type=attribute_type).first()

    @classmethod
    def get(cls, search: str | None) -> tuple[list["Attribute"], int]:
        """Retrieve attributes based on search criteria.

        Args:
            search (str): The search criteria.

        Returns:
            tuple: A tuple containing the list of attributes and the total count.
        """
        # noload overrides the relationship's lazy="subquery": get_all_json is the only caller and
        # it does not serialise the constants, so loading them would be work for nothing.
        query = cls.query.options(noload(cls.attribute_enums))

        if search is not None:
            search_string = f"%{search}%"
            query = query.filter(or_(Attribute.name.ilike(search_string), Attribute.description.ilike(search_string)))

        return query.order_by(db.asc(Attribute.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict:
        """Retrieve all attributes in JSON format.

        Args:
            search (str): The search criteria.

        Returns:
            dict: A dictionary containing the total count and the items in JSON format.
        """
        attributes, total_count = cls.get(search)

        # Without the constants: the list shows name, type and description, and both GUIs load an
        # attribute's constants from the paginated /enums endpoint when the edit dialog opens.
        # Nesting them here shipped every constant of every attribute on every page load - CPE and
        # CVE were already skipped for that reason, but a loaded CWE dictionary is just as large,
        # and this also loaded each attribute's rows a second time on top of the relationship.
        attribute_schema = AttributePresentationSchema(many=True, exclude=("attribute_enums",))
        return {"total_count": total_count, "items": attribute_schema.dump(attributes)}

    @classmethod
    def add_attribute(cls, attribute_data: dict) -> None:
        """Add a new attribute.

        Args:
            attribute_data (dict): The attribute data.

        Returns:
            None
        """
        attribute_schema = NewAttributeSchema()
        attribute = attribute_schema.load(attribute_data)

        # The relationship cascade inserts the constants along with the attribute and fills in
        # their attribute_id. Clearing the collection afterwards (as this used to do) would
        # de-associate the rows it had just written and null that foreign key back out, so the
        # constants of a freshly created RADIO/ENUM/MULTI_CHOICE attribute were lost.
        for count, attribute_enum in enumerate(attribute.attribute_enums):
            attribute_enum.index = count

        db.session.add(attribute)
        db.session.commit()

    @classmethod
    def update(cls, attribute_id: int, data: dict) -> None:
        """Update an attribute.

        Args:
            attribute_id (int): The ID of the attribute.
            data (dict): The updated attribute data.

        Returns:
            None
        """
        schema = NewAttributeSchema()
        updated_attribute = schema.load(data)
        attribute = db.session.get(cls, attribute_id)
        attribute.name = updated_attribute.name
        attribute.description = updated_attribute.description
        attribute.type = updated_attribute.type
        attribute.default_value = updated_attribute.default_value
        attribute.validator = updated_attribute.validator
        attribute.validator_parameter = updated_attribute.validator_parameter
        db.session.commit()

    @classmethod
    # `id` shadows the builtin; it is part of this classmethod's existing call signature.
    def report_types_using(cls, id: int) -> list[str]:  # noqa: A002
        """Titles of the report types whose fields are built on this attribute.

        Args:
            id (int): The ID of the attribute.

        Returns:
            list[str]: Report type titles, sorted, without duplicates.
        """
        # Imported here: report_item_type imports this module, so a module-level import
        # of it would be circular.
        from model.report_item_type import AttributeGroup, AttributeGroupItem, ReportItemType  # noqa: PLC0415

        titles = (
            db.session.query(ReportItemType.title)
            .join(AttributeGroup, AttributeGroup.report_item_type_id == ReportItemType.id)
            .join(AttributeGroupItem, AttributeGroupItem.attribute_group_id == AttributeGroup.id)
            .filter(AttributeGroupItem.attribute_id == id)
            .distinct()
            .all()
        )
        return sorted(title for (title,) in titles)

    @classmethod
    # `id` shadows the builtin; it is part of this classmethod's existing call signature.
    def delete_attribute(cls, id: int) -> None:  # noqa: A002
        """Delete an attribute.

        Args:
            id (int): The ID of the attribute.

        Raises:
            AttributeInUseError: If a report type still builds a field on this attribute.
        """
        # attribute_group_item.attribute_id cascades on delete, so removing an attribute that
        # a report type uses would strip those fields from the report type - and fail outright
        # with a foreign key violation once report items hold values for them. Refuse instead,
        # and name the report types that have to be edited first.
        report_types = cls.report_types_using(id)
        if report_types:
            raise AttributeInUseError(report_types)

        attribute = db.session.get(cls, id)
        AttributeEnum.delete_for_attribute(id)
        db.session.delete(attribute)
        db.session.commit()

    @staticmethod
    def count_elements(file_path: str, tag: str) -> int:
        """Count the number of elements with a specific tag in an XML file.

        Args:
            file_path (str): The path to the XML file.
            tag (str): The tag name of the elements to count.

        Returns:
            int: The number of elements with the specified tag.
        """
        return sum(1 for event, elem in iterparse(file_path, events=("end",)) if elem.tag == tag)

    @classmethod
    def load_cve_from_file(cls, file_path: str) -> None:
        """Load CVE attributes from a file.

        Args:
            file_path (str): The path to the file.
        """
        attribute = cls.query.filter_by(type=AttributeType.CVE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)
        tag_desc = "{http://cve.mitre.org/cve/downloads/1.0}desc"
        tag_item = "{http://cve.mitre.org/cve/downloads/1.0}item"

        item_count = 0
        block_item_count = 0
        desc = ""

        total_elements = cls.count_elements(file_path, tag_item)

        with tqdm(total=total_elements, desc="Processing CVE items", unit="\u2009CVEs") as pbar:
            for event, element in iterparse(file_path, events=("start", "end")):
                if event == "end":
                    if element.tag == tag_desc:
                        desc = element.text
                    elif element.tag == tag_item:
                        attribute_enum = AttributeEnum(None, item_count, element.attrib["name"], desc)
                        attribute_enum.attribute_id = attribute.id
                        attribute_enum.imported = True
                        db.session.add(attribute_enum)
                        item_count += 1
                        block_item_count += 1
                        element.clear()
                        desc = ""
                        if block_item_count == IMPORT_COMMIT_BATCH:
                            block_item_count = 0
                            db.session.commit()
                        pbar.update(1)

        db.session.commit()
        logger.info(f"Processed CVE items: {item_count}")

    @classmethod
    def load_cpe_from_file(cls, file_path: str) -> None:
        """Load CPE attributes from a file.

        Args:
            file_path (str): The path to the file.
        """
        attribute = cls.query.filter_by(type=AttributeType.CPE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)
        tag_item = "{http://cpe.mitre.org/dictionary/2.0}cpe-item"
        tag_title = "{http://cpe.mitre.org/dictionary/2.0}title"

        total_elements = cls.count_elements(file_path, tag_item)

        item_count = 0
        block_item_count = 0
        desc = ""
        with tqdm(total=total_elements, desc="Processing CPE items", unit="\u2009CPEs") as pbar:
            for event, element in iterparse(file_path, events=("start", "end")):
                if event == "end":
                    if element.tag == tag_title:
                        desc = element.text
                    elif element.tag == tag_item:
                        attribute_enum = AttributeEnum(None, item_count, element.attrib["name"], desc)
                        attribute_enum.attribute_id = attribute.id
                        attribute_enum.imported = True
                        db.session.add(attribute_enum)
                        item_count += 1
                        block_item_count += 1
                        element.clear()
                        desc = ""
                        if block_item_count == IMPORT_COMMIT_BATCH:
                            block_item_count = 0
                            db.session.commit()
                        pbar.update(1)

        db.session.commit()
        logger.info(f"Processed CPE items: {item_count}")

    @classmethod
    def load_cwe_from_file(cls, file_path: str) -> None:
        """Load CWE attributes from a file.

        Args:
            file_path (str): The path to the file.
        """
        attribute = cls.query.filter_by(type=AttributeType.CWE).first()
        AttributeEnum.delete_imported_for_attribute(attribute.id)
        tag = "{http://cwe.mitre.org/cwe-7}Weakness"

        total_elements = cls.count_elements(file_path, tag)

        item_count = 0
        block_item_count = 0
        with tqdm(total=total_elements, desc="Processing CWE items", unit="\u2009CWEs") as pbar:
            for event, element in iterparse(file_path, events=("start", "end")):
                if event == "end" and element.tag == tag:
                    attribute_enum = AttributeEnum(None, item_count, element.attrib["ID"], element.attrib["Name"])
                    attribute_enum.attribute_id = attribute.id
                    attribute_enum.imported = True
                    db.session.add(attribute_enum)
                    item_count += 1
                    block_item_count += 1
                    element.clear()
                    if block_item_count == IMPORT_COMMIT_BATCH:
                        block_item_count = 0
                        db.session.commit()
                    pbar.update(1)

        db.session.commit()
        logger.info(f"Processed CWE items: {item_count}")

    @classmethod
    def load_dictionaries(cls, dict_type: str) -> None:
        """Load dictionaries based on the specified dict_type.

        Args:
            dict_type (str): The type of dictionary to load.
        """
        if dict_type == "cve":
            cve_update_file = os.getenv("CVE_UPDATE_FILE")
            if cve_update_file is not None and Path(cve_update_file).exists():
                Attribute.load_cve_from_file(cve_update_file)

        if dict_type == "cpe":
            cpe_update_file = os.getenv("CPE_UPDATE_FILE")
            if cpe_update_file is not None and Path(cpe_update_file).exists():
                Attribute.load_cpe_from_file(cpe_update_file)

        if dict_type == "cwe":
            cwe_update_file = os.getenv("CWE_UPDATE_FILE")
            if cwe_update_file is not None and Path(cwe_update_file).exists():
                Attribute.load_cwe_from_file(cwe_update_file)
