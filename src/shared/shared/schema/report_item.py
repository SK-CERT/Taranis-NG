"""This module contains schemas and classes for representing report items and their attributes.

The module includes the following classes:
- ReportItemAttributeBaseSchema: Schema for representing a report item attribute.
- ReportItemAttributeSchema: Schema for representing a report item attribute with additional fields.
- ReportItemAttribute: Class representing an attribute of a report item.
- ReportItemBaseSchema: Schema for the base report item.
- RemoteReportItemSchema: Schema for remote report items.
- ReportItemSchema: Schema for serializing and deserializing ReportItem objects.
- ReportItemAttributeRemoteSchema: Schema for representing a remote attribute of a report item.
- ReportItemRemoteSchema: Schema for representing a remote report item.
- ReportItemPresentationSchema: Schema for presenting a report item.
- ReportItem: Class representing a report item.

The module also imports schemas from other modules:
- PresentationSchema: Schema for presentation.
- NewsItemAggregateSchema: Schema for representing news item aggregates.
- ACLEntryStatusSchema: Schema for the ACL entry status.
- UserSchemaBase: Schema for representing user data.
"""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.acl_entry import ACLEntryStatusSchema
from shared.schema.news_item import NewsItemAggregateSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.state import StateDefinitionSchema
from shared.schema.user import UserSchemaBase


class ReportItemAttributeBaseSchema(Schema):
    """Schema for representing a report item attribute.

    Attributes:
        id (int): The ID of the attribute.
        value (str): The value of the attribute.
        value_description (str): The description of the attribute value.
        binary_mime_type (str): The MIME type of the binary attribute.
        binary_size (int): The size of the binary attribute.
        binary_description (str): The description of the binary attribute.
        attribute_group_item_title (str): The title of the attribute group item.
        attribute_group_item_id (int): The ID of the attribute group item.
    """

    class Meta:
        """Meta class for configuring the behavior of the ReportItemAttributeBase schema."""

        unknown = EXCLUDE

    id = fields.Int(load_default=None, allow_none=True)
    value = fields.Str()
    value_description = fields.Str(load_default=None, allow_none=True)
    binary_mime_type = fields.Str(load_default=None, allow_none=True)
    binary_size = fields.Int(load_default=0)
    binary_description = fields.Str(load_default=None, allow_none=True)
    attribute_group_item_title = fields.Str(load_default=None, allow_none=True)
    attribute_group_item_id = fields.Integer(load_default=None, allow_none=True)


class ReportItemAttribute:
    """Represents an attribute of a report item.

    Attributes:
        id (int): The ID of the attribute.
        value (str): The value of the attribute.
        value_description (str): The description of the attribute value.
        binary_mime_type (str): The MIME type of the binary data associated with the attribute.
        binary_size (int): The size of the binary data associated with the attribute.
        binary_description (str): The description of the binary data associated with the attribute.
        attribute_group_item_id (int): The ID of the attribute group item.
        attribute_group_item_title (str): The title of the attribute group item.
        created (datetime): The date and time when the attribute was created.
        last_updated (datetime): The date and time when the attribute was last updated.
        version (int): The version of the attribute.
        current (bool): Indicates whether the attribute is the current version.
        user (str): The user who created or last updated the attribute.
    """

    def __init__(
        self,
        id: int,  # noqa: A002
        value: str,
        value_description: str,
        binary_mime_type: str,
        binary_size: int,
        binary_description: str,
        attribute_group_item_id: int,
        attribute_group_item_title: str,
        created: str,
        last_updated: str,
        version: int,
        current: bool,
        user: str,
    ) -> None:
        """Initialize a new instance of the ReportItem class."""
        self.id = id
        self.value = value
        self.value_description = value_description
        self.created = created
        self.last_updated = last_updated
        self.version = version
        self.current = current
        self.binary_mime_type = binary_mime_type
        self.binary_size = binary_size
        self.binary_description = binary_description
        self.attribute_group_item_id = attribute_group_item_id
        self.attribute_group_item_title = attribute_group_item_title
        self.user = user


class ReportItemAttributeSchema(ReportItemAttributeBaseSchema):
    """Schema for representing a report item attribute.

    This schema defines the structure and validation rules for a report item attribute.

    Arguments:
        ReportItemAttributeBaseSchema -- The base schema for a report item attribute.

    Returns:
        An instance of the ReportItemAttributeSchema class.
    """

    created = fields.DateTime("%d.%m.%Y - %H:%M")
    last_updated = fields.DateTime("%d.%m.%Y - %H:%M")
    version = fields.Int()
    current = fields.Bool()
    user = fields.Nested(UserSchemaBase, exclude=("password",))

    @post_load
    def make(self, data: dict, **kwargs) -> ReportItemAttribute:  # noqa: ARG002, ANN003
        """Create a new ReportItemAttribute object.

        This method takes in data and creates a new ReportItemAttribute object using the provided data.

        Arguments:
            data (dict): A dictionary containing the data for creating the ReportItemAttribute object.
            **kwargs: Additional keyword arguments.

        Returns:
            ReportItemAttribute: The newly created ReportItemAttribute object.
        """
        return ReportItemAttribute(**data)


class ReportItemBaseSchema(Schema):
    """Schema for the base report item.

    Attributes:
        id (int): The ID of the report item.
        uuid (str): The UUID of the report item.
        title (str): The title of the report item.
        title_prefix (str): The prefix of the report item title.
        created (DateTime): The date and time when the report item was created.
        last_updated (DateTime): The date and time when the report item was last updated.
        report_item_type_id (int): The ID of the report item type.
    """

    class Meta:
        """Meta class for configuring the behavior of the ReportItem schema."""

        unknown = EXCLUDE

    id = fields.Int(load_default=None, allow_none=True)
    uuid = fields.Str(allow_none=True)
    title = fields.Str()
    title_prefix = fields.Str()
    created = fields.DateTime("%d.%m.%Y - %H:%M")
    last_updated = fields.DateTime("%d.%m.%Y - %H:%M")
    report_item_type_id = fields.Int(load_default=None, allow_none=True)
    state_id = fields.Int(allow_none=True)


class RemoteReportItemSchema(ReportItemBaseSchema, PresentationSchema):
    """Schema for remote report items.

    This schema represents the structure and validation rules for remote report items.

    Arguments:
        ReportItemBaseSchema -- Base schema for report items.
        PresentationSchema -- Schema for presentation.

    Attributes:
        remote_user (str): The remote user associated with the report item.
        attributes (list): List of nested report item attributes.
    """

    remote_user = fields.Str(allow_none=True)
    attributes = fields.Nested(ReportItemAttributeSchema, many=True)


class ReportItemAttributeRemoteSchema(Schema):
    """A schema for representing a remote attribute of a report item.

    Attributes:
        attribute_group_item_title (str): The title of the attribute group item.
        value (str): The value of the attribute.
    """

    attribute_group_item_title = fields.Str()
    value = fields.Str()


class ReportItemRemoteSchema(Schema):
    """A schema for representing a remote report item.

    Arguments:
        Schema -- The base schema class.
    """

    uuid = fields.Str(allow_none=True)
    title = fields.Str()
    title_prefix = fields.Str()
    state_id = fields.Int()
    attributes = fields.Nested(ReportItemAttributeRemoteSchema, many=True)


class ReportItemPresentationSchema(ReportItemBaseSchema, ACLEntryStatusSchema, PresentationSchema):
    """Schema for presenting a report item.

    This schema inherits from the ReportItemBaseSchema, ACLEntryStatusSchema, and PresentationSchema classes.

    Arguments:
        ReportItemBaseSchema -- Schema for the base report item.
        ACLEntryStatusSchema -- Schema for the ACL entry status.
        PresentationSchema -- Schema for the presentation.

    Attributes:
        remote_user -- String field representing the remote user. Allows None as a value.
        state -- State associated with the report item.
    """

    remote_user = fields.Str(allow_none=True)
    state = fields.Nested(StateDefinitionSchema, allow_none=True)


class ReportItem:
    """Represents a report item.

    Attributes:
        id (int): The ID of the report item.
        uuid (str): The UUID of the report item.
        title (str): The title of the report item.
        title_prefix (str): The prefix of the report item title.
        created (datetime): The date and time when the report item was created.
        last_updated (datetime): The date and time when the report item was last updated.
        report_item_type_id (int): The ID of the report item type.
        state_id (int): The ID of the state associated with the report item.
        news_item_aggregates (list): A list of news item aggregates associated with the report item.
        remote_report_items (list): A list of remote report items associated with the report item.
        attributes (dict): Additional attributes of the report item.
        remote_user (str): The remote user associated with the report item.
    """

    def __init__(
        self,
        id: int,  # noqa: A002
        uuid: str,
        title: str,
        title_prefix: str,
        created: str,
        last_updated: str,
        report_item_type_id: int,
        state_id: int,
        news_item_aggregates: list,
        remote_report_items: list,
        attributes: dict,
        remote_user: str,
    ) -> None:
        """Initialize a ReportItem object."""
        self.id = id
        self.uuid = uuid
        self.title = title
        self.title_prefix = title_prefix
        self.created = created
        self.last_updated = last_updated
        self.report_item_type_id = report_item_type_id
        self.state_id = state_id
        self.news_item_aggregates = news_item_aggregates
        self.attributes = attributes
        self.remote_report_items = remote_report_items
        self.remote_user = remote_user


class ReportItemSchema(ReportItemBaseSchema):
    """Schema for serializing and deserializing ReportItem objects.

    Inherits from ReportItemBaseSchema.

    Attributes:
        news_item_aggregates (List[NewsItemAggregateSchema]): List of nested NewsItemAggregateSchema objects.
        remote_report_items (List[RemoteReportItemSchema]): List of nested RemoteReportItemSchema objects.
        attributes (List[ReportItemAttributeSchema]): List of nested ReportItemAttributeSchema objects.
        remote_user (str): Remote user associated with the report item.

    Methods:
        make(data, **kwargs): Post-load method to create a ReportItem object from deserialized data.

    Returns:
        ReportItemSchema: An instance of the ReportItemSchema class.
    """

    news_item_aggregates = fields.Nested(NewsItemAggregateSchema, many=True)
    remote_report_items = fields.Nested(RemoteReportItemSchema, many=True)
    attributes = fields.Nested(ReportItemAttributeSchema, many=True)
    remote_user = fields.Str(allow_none=True)

    @post_load
    def make(self, data: dict, **kwargs) -> ReportItem:  # noqa: ARG002, ANN003
        """Create a new ReportItem object.

        This method takes in data and creates a new ReportItem object using the provided data.

        Arguments:
            data (dict): A dictionary containing the data for the ReportItem.
            **kwargs: Additional keyword arguments.

        Returns:
            ReportItem: A new ReportItem object.
        """
        return ReportItem(**data)


class ReportItemId:
    """A class representing the ID of a report item.

    Args:
        id (int): The ID of the report item.

    Attributes:
        id (int): The ID of the report item.
    """

    def __init__(self, id: int) -> None:  # noqa: A002
        """Initialize a ReportItem object.

        Args:
            id (int): The ID of the report item.
        """
        self.id = id


class ReportItemIdSchema(Schema):
    """Schema for Report Item ID.

    This schema defines the structure for the Report Item ID.

    Arguments:
        Schema -- The base schema class.

    Returns:
        An instance of the ReportItemId class.
    """

    class Meta:
        """Meta class for configuring the behavior of the ReportItemId schema."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> ReportItemId:  # noqa: ARG002, ANN003
        """Create a new ReportItemId object.

        This method takes in data and returns a new ReportItemId object.

        Arguments:
            data (dict): The data used to create the ReportItemId object.
            **kwargs: Additional keyword arguments.

        Returns:
            ReportItemId: A new ReportItemId object.
        """
        return ReportItemId(**data)
