"""Schemas for daily tag-cloud word counts and totals across calendar dates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from marshmallow import EXCLUDE, Schema, fields, post_load

if TYPE_CHECKING:
    from datetime import date


class TagCloudBaseSchema(Schema):
    """Serialize a word, its count, and the calendar date on which it was collected."""

    class Meta:
        """Ignore fields outside the tag-cloud contract when loading data."""

        unknown = EXCLUDE

    word = fields.Str()
    word_quantity = fields.Int()
    collected = fields.Date()


class TagCloudSchema(TagCloudBaseSchema):
    """Load an individual daily word count."""

    @post_load
    def make_tag_cloud(self, data: dict, **_kwargs: object) -> TagCloud:
        """Construct a daily count from validated fields.

        Args:
            data: Word, count, and collected calendar date.
            **_kwargs: Additional Marshmallow hook options, unused here.

        Returns:
            The deserialized daily tag-cloud entry.
        """
        return TagCloud(**data)


class TagCloud:
    """A word count associated with a collection date."""

    def __init__(self, word: str, word_quantity: int, collected: date) -> None:
        """Initialize a daily word count.

        Args:
            word: The counted word.
            word_quantity: Number of occurrences collected on the date.
            collected: Calendar date of collection, without timezone conversion.
        """
        self.word = word
        self.word_quantity = word_quantity
        self.collected = collected


class GroupedWordsSchema(TagCloudBaseSchema):
    """Load totals grouped by word."""

    @post_load
    def make_grouped_words(self, data: dict, **_kwargs: object) -> GroupedWords:
        """Construct a grouped total from validated fields.

        Args:
            data: Word and its total number of occurrences.
            **_kwargs: Additional Marshmallow hook options, unused here.

        Returns:
            The deserialized grouped word count.
        """
        return GroupedWords(**data)


class GroupedWords:
    """A word count aggregated across collection dates."""

    def __init__(self, word: str, word_quantity: int) -> None:
        """Initialize a grouped word total.

        Args:
            word: The counted word.
            word_quantity: Total number of occurrences across the selected dates.
        """
        self.word = word
        self.word_quantity = word_quantity
