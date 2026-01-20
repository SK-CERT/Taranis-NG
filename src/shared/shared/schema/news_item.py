"""Module for News item schema."""

import datetime

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.common import clean_whitespace
from shared.schema.acl_entry import ACLEntryStatusSchema


class NewsItemAttributeBaseSchema(Schema):
    """Schema for base attributes of a news item."""

    id = fields.Int()
    key = fields.Str()
    value = fields.Str()
    binary_mime_type = fields.Str()


class NewsItemAttributeSchema(NewsItemAttributeBaseSchema):
    """Schema for attributes of a news item with binary value."""

    binary_value = fields.Str()


class NewsItemAttributeRemoteSchema(Schema):
    """Schema for remote attributes of a news item."""

    key = fields.Str()
    value = fields.Str()
    binary_mime_type = fields.Str()
    binary_value = fields.Str()


class NewsItemAttribute:
    """Class representing a news item attribute."""

    def __init__(self, key: str, value: str, binary_mime_type: str, binary_value: bytes) -> None:
        """Initialize a NewsItemAttribute instance.

        Parameters:
            key (str): The key of the attribute.
            value (str): The value of the attribute.
            binary_mime_type (str): The MIME type of the binary value.
            binary_value (bytes): The binary value of the attribute.
        """
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type
        self.binary_value = binary_value


class NewsItemDataBaseSchema(Schema):
    """Base schema for news item data."""

    class Meta:
        """Meta class for defining options for the NewsItemData schema."""

        unknown = EXCLUDE

    id = fields.Str(load_default=None, allow_none=True)
    hash = fields.Str()
    title = fields.Str()
    review = fields.Str()
    source = fields.Str()
    link = fields.Str()
    published = fields.Str()
    author = fields.Str()
    collected = fields.DateTime("%d.%m.%Y - %H:%M")
    osint_source_id = fields.Str(load_default=None, allow_none=True)


class NewsItemData:
    """Class representing news item data."""

    def __init__(
        self,
        id: str,  # noqa: A002
        hash: str,  # noqa: A002
        title: str,
        review: str,
        source: str,
        link: str,
        published: str,
        author: str,
        collected: datetime.datetime,
        content: str,
        osint_source_id: str,
        attributes: list,
    ) -> None:
        """Initialize a NewsItemData instance.

        Parameters:
            id (str): The ID of the news item.
            hash (str): The hash of the news item.
            title (str): The title of the news item.
            review (str): The review of the news item.
            source (str): The source of the news item.
            link (str): The link to the news item.
            published (str): The published date of the news item.
            author (str): The author of the news item.
            collected (datetime): The collected date of the news item.
            content (str): The content of the news item.
            osint_source_id (str): The OSINT source ID of the news item.
            attributes (list): The attributes of the news item.
        """
        self.id = id
        self.hash = hash
        self.title = title
        self.review = review
        self.source = source
        self.link = link
        self.published = published
        self.author = author
        self.collected = collected
        self.content = content
        self.osint_source_id = osint_source_id
        self.attributes = attributes

    def print_news_item(self, logger: object) -> None:
        """Print news item details using the provided logger."""
        if self.title:
            logger.debug(f"__ Title    : {self.title[:100]}")
        if self.review:
            logger.debug(f"__ Review   : {self.review[:100]}")
        if self.content:
            logger.debug(f"__ Content  : {clean_whitespace(self.content)[:100]}")
        if self.published:
            logger.debug(f"__ Published: {self.published}")


class NewsItemDataSchema(NewsItemDataBaseSchema):
    """Schema for news item data with content and attributes."""

    content = fields.Str()
    attributes = fields.Nested(NewsItemAttributeSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> NewsItemData:  # noqa: ANN003, ARG002
        """Create a NewsItemData instance after loading."""
        return NewsItemData(**data)


class NewsItemRemoteSchema(Schema):
    """Schema for remote news item data."""

    hash = fields.Str()
    title = fields.Str()
    review = fields.Str()
    source = fields.Str()
    link = fields.Str()
    published = fields.Str()
    author = fields.Str()
    collected = fields.DateTime("%d.%m.%Y - %H:%M")
    content = fields.Str()
    attributes = fields.Nested(NewsItemAttributeRemoteSchema, many=True)
    relevance = fields.Int()


class NewsItemDataPresentationSchema(NewsItemDataBaseSchema):
    """Schema for presenting news item data."""

    remote_source = fields.Str(allow_none=True)
    osint_source_name = fields.Str()
    osint_source_type = fields.Str()
    content = fields.Str()
    attributes = fields.Nested(NewsItemAttributeBaseSchema, many=True)


class NewsItemBaseSchema(Schema):
    """Base schema for a news item."""

    id = fields.Int()
    likes = fields.Int()
    dislikes = fields.Int()
    read = fields.Bool()
    important = fields.Bool()
    me_like = fields.Bool()
    me_dislike = fields.Bool()
    news_item_data = fields.Nested(NewsItemDataSchema)


class NewsItemTag:
    """Class representing a news item tag."""

    def __init__(self, name: str, tag_type: str) -> None:
        """Initialize a NewsItemTag instance.

        Parameters:
            name (str): The name of the tag.
            tag_type (str): The type of the tag.
        """
        self.name = name
        self.tag_type = tag_type


class NewsItemTagSchema(Schema):
    """Schema for a news item tag."""

    id = fields.Int()
    name = fields.Str()
    tag_type = fields.Str()
    n_i_d = fields.Nested(NewsItemDataSchema, many=True)


class NewsItemSchema(NewsItemBaseSchema):
    """Schema for a news item."""

    news_item_data = fields.Nested(NewsItemDataPresentationSchema)


class NewsItemPresentationSchema(NewsItemSchema, ACLEntryStatusSchema):
    """Schema for presenting a news item with ACL entry status."""


class NewsItemAggregateSchema(Schema):
    """Schema for aggregating news items."""

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    created = fields.DateTime("%d.%m.%Y - %H:%M")
    comments = fields.Str()
    likes = fields.Int()
    dislikes = fields.Int()
    read = fields.Bool()
    important = fields.Bool()
    me_like = fields.Bool()
    me_dislike = fields.Bool()
    in_reports_count = fields.Int()
    news_items = fields.Nested(NewsItemPresentationSchema, many=True)


class NewsItemAggregateId:
    """Class representing a news item aggregate ID."""

    def __init__(self, id: int) -> None:  # noqa: A002
        """Initialize a NewsItemAggregateId instance.

        Parameters:
            id (int): The ID of the news item aggregate.
        """
        self.id = id


class NewsItemAggregateIdSchema(Schema):
    """Schema for news item aggregate ID."""

    class Meta:
        """Meta class for defining options for the NewsItemAggregateId schema."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> NewsItemAggregateId:  # noqa: ANN003, ARG002
        """Create a NewsItemAggregateId instance after loading."""
        return NewsItemAggregateId(**data)
