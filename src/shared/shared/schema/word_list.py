"""This module contains schemas and classes for word lists."""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.presentation import PresentationSchema


class WordListEntrySchema(Schema):
    """Schema for an entry of a word list category."""

    value = fields.Str()
    description = fields.Str()

    @post_load
    def make(self, data: dict, **kwargs) -> "WordListEntry":  # noqa: ANN003, ARG002
        """Create a WordListEntry instance from deserialized data."""
        return WordListEntry(**data)


class WordListCategorySchema(Schema):
    """Schema for a category of a word list, with its entries."""

    name = fields.Str()
    description = fields.Str()
    link = fields.Str(allow_none=True)
    entries = fields.Nested(WordListEntrySchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> "WordListCategory":  # noqa: ANN003, ARG002
        """Create a WordListCategory instance from deserialized data."""
        return WordListCategory(**data)


class WordListSchema(Schema):
    """Schema for Word list, with its categories."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    use_for_stop_words = fields.Bool()
    categories = fields.Nested(WordListCategorySchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> "WordList":  # noqa: ANN003, ARG002
        """Create a WordList instance from deserialized data."""
        return WordList(**data)


class WordListPresentationSchema(WordListSchema, PresentationSchema):
    """Schema for Word list with presentation data."""


class WordList:
    """A word list and its categories."""

    def __init__(
        self,
        id: int,  # noqa: A002
        name: str,
        description: str,
        use_for_stop_words: bool,
        categories: list["WordListCategory"],
    ) -> None:
        """Initialize a WordList instance."""
        self.id = id
        self.name = name
        self.description = description
        self.use_for_stop_words = use_for_stop_words
        self.categories = categories


class WordListCategory:
    """A category of a word list and its entries."""

    def __init__(self, name: str, description: str, link: str | None, entries: list["WordListEntry"]) -> None:
        """Initialize a WordListCategory instance."""
        self.name = name
        self.description = description
        self.link = link
        self.entries = entries


class WordListEntry:
    """An entry of a word list category: a value and its description."""

    def __init__(self, value: str = "", description: str = "") -> None:
        """Initialize a WordListEntry instance."""
        self.value = value
        self.description = description


class WordListIdSchema(Schema):
    """Schema for a word list id."""

    class Meta:  # ty: ignore[invalid-attribute-override]
        """Meta class for configuring the behavior of the schema."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> "WordListId":  # noqa: ANN003, ARG002
        """Create a WordListId instance from deserialized data."""
        return WordListId(**data)


class WordListId:
    """Wrapper class holding a word list id."""

    def __init__(self, id: int) -> None:  # noqa: A002
        """Initialize a WordListId instance."""
        self.id = id
