"""This module defines Marshmallow schemas and data models for report item types and their related attribute groups and items."""

from __future__ import annotations

from typing import TYPE_CHECKING

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.attribute import AttributeSchema
from shared.schema.presentation import PresentationSchema

if TYPE_CHECKING:
    from shared.schema.attribute import Attribute


class AttributeGroupItemSchema(Schema):
    """Marshmallow schema for serializing and deserializing AttributeGroupItem objects."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    index = fields.Int()
    min_occurrence = fields.Int()
    max_occurrence = fields.Int()
    attribute = fields.Nested(AttributeSchema)
    ai_provider_id = fields.Int(allow_none=True)
    ai_prompt = fields.Str(allow_none=True)
    translate = fields.Bool(load_default=False)
    translations = fields.Dict(keys=fields.Str(), values=fields.Dict(keys=fields.Str(), values=fields.Str()), load_default=dict)
    # The labels in the language rendered (presenter input only); title and description stay as written.
    label = fields.Str(load_default=None, allow_none=True)
    description_label = fields.Str(load_default=None, allow_none=True)

    @post_load
    def make_attribute_group_item(self, data: dict, **kwargs) -> AttributeGroupItem:  # noqa: ANN003, ARG002
        """Create an AttributeGroupItem instance from deserialized data.

        Args:
            data (dict): The deserialized data.
            **kwargs: Additional keyword arguments.

        Returns:
            AttributeGroupItem: An instance of AttributeGroupItem.
        """
        return AttributeGroupItem(**data)


class AttributeGroupItem:
    """Data model representing an item in an attribute group."""

    def __init__(
        self,
        id: int,  # noqa: A002
        title: str,
        description: str,
        index: int,
        min_occurrence: int,
        max_occurrence: int,
        attribute: Attribute,
        ai_provider_id: int | None,
        ai_prompt: str | None,
        translate: bool = False,
        translations: dict | None = None,
        label: str | None = None,
        description_label: str | None = None,
    ) -> None:
        """Initialize an AttributeGroupItem instance.

        Args:
            id (int): Unique identifier for the item.
            title (str): Title of the item.
            description (str): Description of the item.
            index (int): Index/order of the item.
            min_occurrence (int): Minimum allowed occurrences.
            max_occurrence (int): Maximum allowed occurrences.
            attribute: Associated attribute object.
            ai_provider_id (int): Associated local AI model ID.
            ai_prompt (str): Optional AI prompt.
            translate (bool): Whether reports translate this item's values (text types only).
            translations (dict): Label variants, ``{language: {"title": ..., "description": ...}}``.
            label (str): The name in the language asked for; set when rendering, never stored.
            description_label (str): The description in the language asked for; set when rendering.
        """
        self.id = id
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute = attribute
        self.ai_provider_id = ai_provider_id
        self.ai_prompt = ai_prompt
        self.translate = translate
        self.translations = translations or {}
        self.label = label
        self.description_label = description_label


class AttributeGroupBaseSchema(Schema):
    """Base Marshmallow schema for attribute groups."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    section = fields.Int(allow_none=True)
    section_title = fields.Str(allow_none=True)
    index = fields.Int()
    translations = fields.Dict(keys=fields.Str(), values=fields.Dict(keys=fields.Str(), values=fields.Str()), load_default=dict)
    # The labels in the language rendered (presenter input only).
    label = fields.Str(load_default=None, allow_none=True)
    description_label = fields.Str(load_default=None, allow_none=True)
    section_label = fields.Str(load_default=None, allow_none=True)

    @post_load
    def make_attribute_group(self, data: dict, **kwargs) -> AttributeGroup:  # noqa: ANN003, ARG002
        """Create an AttributeGroup instance from deserialized data.

        Args:
            data (dict): The deserialized data.
            **kwargs: Additional keyword arguments.

        Returns:
            AttributeGroup: An instance of AttributeGroup.
        """
        return AttributeGroup(**data)


class AttributeGroupSchema(AttributeGroupBaseSchema):
    """Marshmallow schema for attribute groups, including nested attribute group items."""

    attribute_group_items = fields.Nested(AttributeGroupItemSchema, many=True)


class AttributeGroup:
    """Data model representing an attribute group."""

    def __init__(
        self,
        id: int,  # noqa: A002
        title: str,
        description: str,
        section: int | None,
        section_title: str | None,
        index: int,
        attribute_group_items: list[AttributeGroupItem],
        translations: dict | None = None,
        label: str | None = None,
        description_label: str | None = None,
        section_label: str | None = None,
    ) -> None:
        """Initialize an AttributeGroup instance.

        Args:
            id (int): Unique identifier for the group.
            title (str): Title of the group.
            description (str): Description of the group.
            section (int): Section number (optional).
            section_title (str): Section title (optional).
            index (int): Index/order of the group.
            attribute_group_items (list): List of AttributeGroupItem objects.
            translations (dict): Label variants, ``{language: {"title": ..., "description": ..., "section_title": ...}}``.
            label (str): The name in the language asked for; set when rendering, never stored.
            description_label (str): The description in the language asked for; set when rendering.
            section_label (str): The section title in the language asked for; set when rendering.
        """
        self.id = id
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.attribute_group_items = attribute_group_items
        self.translations = translations or {}
        self.label = label
        self.description_label = description_label
        self.section_label = section_label


class ReportItemTypeBaseSchema(Schema):
    """Base Marshmallow schema for report item types."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    languages = fields.List(fields.Str(), load_default=list)
    translation_ai_provider_id = fields.Int(allow_none=True, load_default=None)
    label_language = fields.Str(allow_none=True, load_default=None)
    translations = fields.Dict(keys=fields.Str(), values=fields.Dict(keys=fields.Str(), values=fields.Str()), load_default=dict)
    # The labels in the language rendered (presenter input only).
    label = fields.Str(load_default=None, allow_none=True)
    description_label = fields.Str(load_default=None, allow_none=True)


class ReportItemTypeSchema(ReportItemTypeBaseSchema):
    """Marshmallow schema for report item types, including nested attribute groups."""

    attribute_groups = fields.Nested(AttributeGroupSchema, many=True)

    @post_load
    def make(self, data: dict, **kwargs) -> ReportItemType:  # noqa: ANN003, ARG002
        """Create a ReportItemType instance from deserialized data.

        Args:
            data (dict): The deserialized data.
            **kwargs: Additional keyword arguments.

        Returns:
            ReportItemType: An instance of ReportItemType.
        """
        return ReportItemType(**data)


class ReportItemTypePresentationSchema(ReportItemTypeSchema, PresentationSchema):
    """Extended schema for report item types, including presentation fields."""


class ReportItemType:
    """Data model representing a report item type."""

    def __init__(
        self,
        id: int,  # noqa: A002
        title: str,
        description: str,
        attribute_groups: list[AttributeGroup],
        languages: list[str] | None = None,
        translation_ai_provider_id: int | None = None,
        label_language: str | None = None,
        translations: dict | None = None,
        label: str | None = None,
        description_label: str | None = None,
    ) -> None:
        """Initialize a ReportItemType instance.

        Args:
            id (int): Unique identifier for the report item type.
            title (str): Title of the report item type.
            description (str): Description of the report item type.
            attribute_groups (list): List of AttributeGroup objects.
            languages (list): Language variants (ISO 639-1) reports of this type are translated into.
            translation_ai_provider_id (int): AI provider that translates reports of this type.
            label_language (str): Language the labels are written in, if stated.
            translations (dict): Label variants, ``{language: {"title": ..., "description": ...}}``.
            label (str): The name in the language asked for; set when rendering, never stored.
            description_label (str): The description in the language asked for; set when rendering.
        """
        self.id = id
        self.title = title
        self.description = description
        self.attribute_groups = attribute_groups
        self.languages = languages or []
        self.translation_ai_provider_id = translation_ai_provider_id
        self.label_language = label_language
        self.translations = translations or {}
        self.label = label
        self.description_label = description_label


class ReportItemTypeIdSchema(Schema):
    """Marshmallow schema for serializing/deserializing only the report item type ID."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data: dict, **kwargs) -> ReportItemTypeId:  # noqa: ANN003, ARG002
        """Create a ReportItemTypeId instance from deserialized data.

        Args:
            data (dict): The deserialized data.
            **kwargs: Additional keyword arguments.

        Returns:
            ReportItemTypeId: An instance of ReportItemTypeId.
        """
        return ReportItemTypeId(**data)


class ReportItemTypeId:
    """Data model representing only the report item type ID."""

    def __init__(self, id: int) -> None:  # noqa: A002
        """Initialize a ReportItemTypeId instance.

        Args:
            id (int): Unique identifier for the report item type.
        """
        self.id = id
