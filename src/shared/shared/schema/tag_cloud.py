"""This module contains schemas and classes for the tag cloud."""

import datetime as dt

from marshmallow import EXCLUDE, Schema, fields, post_load


class TagCloudBaseSchema(Schema):
    """Base schema for a word of the tag cloud."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    word = fields.Str()
    word_quantity = fields.Int()
    collected = fields.DateTime("%d.%m.%Y")


class TagCloudSchema(TagCloudBaseSchema):
    """Schema for a word of the tag cloud on the day it was collected."""

    @post_load
    def make_tag_cloud(self, data: dict, **kwargs) -> "TagCloud":  # noqa: ANN003, ARG002
        """Create a TagCloud instance from deserialized data."""
        return TagCloud(**data)


class TagCloud:
    """A word of the tag cloud, how often it occurred, and the day it was collected."""

    def __init__(self, word: str, word_quantity: int, collected: dt.datetime) -> None:
        """Initialize a TagCloud instance."""
        self.word = word
        self.word_quantity = word_quantity
        self.collected = collected


class GroupedWordsSchema(TagCloudBaseSchema):
    """Schema for a word of the tag cloud, summed over the days."""

    @post_load
    def make_grouped_words(self, data: dict, **kwargs) -> "GroupedWords":  # noqa: ANN003, ARG002
        """Create a GroupedWords instance from deserialized data."""
        return GroupedWords(**data)


class GroupedWords:
    """A word of the tag cloud and how often it occurred."""

    def __init__(self, word: str, word_quantity: int) -> None:
        """Initialize a GroupedWords instance."""
        self.word = word
        self.word_quantity = word_quantity
