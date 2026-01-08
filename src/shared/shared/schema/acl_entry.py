"""Module for ACL entry schema."""

from enum import Enum, auto

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.presentation import PresentationSchema
from shared.schema.role import RoleSchema
from shared.schema.user import UserSchemaBase


class ItemType(Enum):
    """An enumeration class that represents different types of items.

    Attributes:
        COLLECTOR (auto): Represents a collector item type.
        OSINT_SOURCE (auto): Represents an OSINT source item type.
        OSINT_SOURCE_GROUP (auto): Represents a group of OSINT sources.
        WORD_LIST (auto): Represents a word list item type.
        REPORT_ITEM_TYPE (auto): Represents a type of report item.
        PRODUCT_TYPE (auto): Represents a product type item.
    """

    COLLECTOR = auto()
    OSINT_SOURCE = auto()
    OSINT_SOURCE_GROUP = auto()
    WORD_LIST = auto()
    REPORT_ITEM_TYPE = auto()
    PRODUCT_TYPE = auto()


class ACLEntryStatusSchema(Schema):
    """Defines the schema for an ACL (Access Control List) entry status.

    Attributes:
        see (fields.Bool): Indicates if the entry has permission to see the resource.
        access (fields.Bool): Indicates if the entry has permission to access the resource.
        modify (fields.Bool): Indicates if the entry has permission to modify the resource.
    """

    see = fields.Bool()
    access = fields.Bool()
    modify = fields.Bool()


class ACLEntrySchema(ACLEntryStatusSchema):
    """A schema class that inherits from ACLEntryStatusSchema.

    Attributes:
        Meta (class): A nested class that contains metadata for the schema.
            unknown (str): Specifies the behavior for unknown fields. Set to EXCLUDE.
        id (fields.Integer): An integer field representing the ID of the ACL entry.
        name (fields.Str): A string field representing the name of the ACL entry.
        description (fields.Str): A string field representing the description of the ACL entry.
        item_type (fields.Enum): An enum field representing the type of the item.
        item_id (fields.Str): A string field representing the ID of the item.
        everyone (fields.Bool): A boolean field indicating if the ACL entry applies to everyone.
    """

    class Meta:
        """Meta class for configuring schema behavior.

        Attributes:
            unknown (marshmallow.fields.Field): Specifies the behavior for unknown fields in the input data.
                Set to `EXCLUDE` to ignore unknown fields.
        """

        unknown = EXCLUDE

    id = fields.Integer()
    name = fields.Str()
    description = fields.Str()

    item_type = fields.Enum(ItemType)
    item_id = fields.Str()

    everyone = fields.Bool()


class ACLEntryPresentationSchema(ACLEntrySchema, PresentationSchema):
    """A schema that combines the ACLEntrySchema and PresentationSchema.

    It includes nested fields for roles and users.

    Attributes:
        roles (list): A list of roles associated with the ACL entry, represented by RoleSchema.
        users (list): A list of users associated with the ACL entry, represented by UserSchemaBase.
    """

    roles = fields.Nested(RoleSchema, many=True)
    users = fields.Nested(UserSchemaBase, many=True)
