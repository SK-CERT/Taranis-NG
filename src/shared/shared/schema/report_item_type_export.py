"""Marshmallow schemas for the report type export document.

The export is a portable definition, not a database dump, so it carries no ids. Every reference
is by name: a report type matches an existing one by title, and a field finds its attribute type
by name. What has no name to travel by - AI model references and label translations - is left out
rather than exported as a dangling id.
"""

from __future__ import annotations

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.attribute import AttributeType, AttributeValidator

# The export format this module reads and writes.
EXPORT_VERSION = 1

# Only these attribute types keep their constants in the attribute_enum table, and only these
# are worth shipping. CPE, CVE and CWE hold over a million rows each, loaded from dictionaries.
ENUM_BACKED_TYPES = (AttributeType.RADIO, AttributeType.ENUM, AttributeType.MULTI_CHOICE)


class AttributeEnumExportSchema(Schema):
    """A constant of an exported attribute type.

    Attributes:
        index (fields.Int): The order the constant sits in.
        value (fields.Str): The constant itself.
        description (fields.Str): What the constant means.
    """

    class Meta:  # ty: ignore[incompatible-attribute-override]
        """Unknown keys in an import file are ignored rather than rejected."""

        unknown = EXCLUDE

    index = fields.Int(load_default=-1)
    value = fields.Str(load_default="")
    description = fields.Str(load_default="")

    @post_load
    def make(self, data: dict, **kwargs) -> AttributeEnumExport:  # noqa: ANN003, ARG002
        """Build the exported constant.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            AttributeEnumExport: The exported constant.
        """
        return AttributeEnumExport(**data)


class AttributeEnumExport:
    """A constant of an exported attribute type.

    Attributes:
        index (int): The order the constant sits in.
        value (str): The constant itself.
        description (str): What the constant means.
    """

    def __init__(self, index: int, value: str, description: str) -> None:
        """Initialize an exported constant.

        Args:
            index (int): The order the constant sits in.
            value (str): The constant itself.
            description (str): What the constant means.
        """
        self.index = index
        self.value = value
        self.description = description


class AttributeTypeExportSchema(Schema):
    """An attribute type used by the exported report types.

    Attributes:
        name (fields.Str): The name the fields pair with this attribute type by.
        description (fields.Str): What the attribute type is for.
        type (fields.Enum): The kind of value the field holds.
        default_value (fields.Str): The value a new report starts with.
        validator (fields.Enum): The validator applied to values.
        validator_parameter (fields.Str): The parameter the validator takes.
        attribute_enums (fields.List): The constants, empty unless the type is enum-backed.
    """

    class Meta:  # ty: ignore[incompatible-attribute-override]
        """Unknown keys in an import file are ignored rather than rejected."""

        unknown = EXCLUDE

    name = fields.Str(required=True)
    description = fields.Str(load_default=None, allow_none=True)
    type = fields.Enum(AttributeType, required=True)
    default_value = fields.Str(load_default=None, allow_none=True)
    validator = fields.Enum(AttributeValidator, load_default=None, allow_none=True)
    validator_parameter = fields.Str(load_default=None, allow_none=True)
    attribute_enums = fields.List(fields.Nested(AttributeEnumExportSchema), load_default=list)

    @post_load
    def make(self, data: dict, **kwargs) -> AttributeTypeExport:  # noqa: ANN003, ARG002
        """Build the exported attribute type.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            AttributeTypeExport: The exported attribute type.
        """
        return AttributeTypeExport(**data)


class AttributeTypeExport:
    """An attribute type used by the exported report types.

    Attributes:
        name (str): The name the fields pair with this attribute type by.
        description (str | None): What the attribute type is for.
        type (AttributeType): The kind of value the field holds.
        default_value (str | None): The value a new report starts with.
        validator (AttributeValidator | None): The validator applied to values.
        validator_parameter (str | None): The parameter the validator takes.
        attribute_enums (list[AttributeEnumExport]): The constants.
    """

    def __init__(
        self,
        name: str,
        description: str | None,
        type: AttributeType,  # noqa: A002
        default_value: str | None,
        validator: AttributeValidator | None,
        validator_parameter: str | None,
        attribute_enums: list[AttributeEnumExport],
    ) -> None:
        """Initialize an exported attribute type.

        Args:
            name (str): The name the fields pair with this attribute type by.
            description (str | None): What the attribute type is for.
            type (AttributeType): The kind of value the field holds.
            default_value (str | None): The value a new report starts with.
            validator (AttributeValidator | None): The validator applied to values.
            validator_parameter (str | None): The parameter the validator takes.
            attribute_enums (list[AttributeEnumExport]): The constants.
        """
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter
        self.attribute_enums = attribute_enums


class AttributeGroupItemExportSchema(Schema):
    """A field of an exported attribute group.

    Attributes:
        title (fields.Str): The label the field shows in a report.
        description (fields.Str): What the field collects.
        index (fields.Int): The order the field sits in within its group.
        min_occurrence (fields.Int): How many times the field must appear in a report.
        max_occurrence (fields.Int): How many times the field may appear in a report.
        attribute_type_key (fields.Str): The name of the attribute type the field is built on.
    """

    class Meta:  # ty: ignore[incompatible-attribute-override]
        """Unknown keys in an import file are ignored rather than rejected."""

        unknown = EXCLUDE

    title = fields.Str(load_default="")
    description = fields.Str(load_default="")
    index = fields.Int(load_default=0)
    min_occurrence = fields.Int(load_default=0)
    max_occurrence = fields.Int(load_default=1)
    attribute_type_key = fields.Str(load_default=None, allow_none=True)

    @post_load
    def make(self, data: dict, **kwargs) -> AttributeGroupItemExport:  # noqa: ANN003, ARG002
        """Build the exported field.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            AttributeGroupItemExport: The exported field.
        """
        return AttributeGroupItemExport(**data)


class AttributeGroupItemExport:
    """A field of an exported attribute group.

    Attributes:
        title (str): The label the field shows in a report.
        description (str): What the field collects.
        index (int): The order the field sits in within its group.
        min_occurrence (int): How many times the field must appear in a report.
        max_occurrence (int): How many times the field may appear in a report.
        attribute_type_key (str | None): The name of the attribute type the field is built on.
    """

    def __init__(
        self,
        title: str,
        description: str,
        index: int,
        min_occurrence: int,
        max_occurrence: int,
        attribute_type_key: str | None,
    ) -> None:
        """Initialize an exported field.

        Args:
            title (str): The label the field shows in a report.
            description (str): What the field collects.
            index (int): The order the field sits in within its group.
            min_occurrence (int): How many times the field must appear in a report.
            max_occurrence (int): How many times the field may appear in a report.
            attribute_type_key (str | None): The name of the attribute type the field is built on.
        """
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_type_key = attribute_type_key


class AttributeGroupExportSchema(Schema):
    """An attribute group of an exported report type.

    Attributes:
        title (fields.Str): The name the group shows.
        description (fields.Str): What the group collects.
        section (fields.Int): The section number the group belongs to.
        section_title (fields.Str): The title of that section.
        index (fields.Int): The order the group sits in within the report type.
        attribute_group_items (fields.List): The fields in the group.
    """

    class Meta:  # ty: ignore[incompatible-attribute-override]
        """Unknown keys in an import file are ignored rather than rejected."""

        unknown = EXCLUDE

    title = fields.Str(load_default="")
    description = fields.Str(load_default="")
    section = fields.Int(load_default=None, allow_none=True)
    section_title = fields.Str(load_default=None, allow_none=True)
    index = fields.Int(load_default=0)
    attribute_group_items = fields.List(fields.Nested(AttributeGroupItemExportSchema), load_default=list)

    @post_load
    def make(self, data: dict, **kwargs) -> AttributeGroupExport:  # noqa: ANN003, ARG002
        """Build the exported group.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            AttributeGroupExport: The exported group.
        """
        return AttributeGroupExport(**data)


class AttributeGroupExport:
    """An attribute group of an exported report type.

    Attributes:
        title (str): The name the group shows.
        description (str): What the group collects.
        section (int | None): The section number the group belongs to.
        section_title (str | None): The title of that section.
        index (int): The order the group sits in within the report type.
        attribute_group_items (list[AttributeGroupItemExport]): The fields in the group.
    """

    def __init__(
        self,
        title: str,
        description: str,
        section: int | None,
        section_title: str | None,
        index: int,
        attribute_group_items: list[AttributeGroupItemExport],
    ) -> None:
        """Initialize an exported group.

        Args:
            title (str): The name the group shows.
            description (str): What the group collects.
            section (int | None): The section number the group belongs to.
            section_title (str | None): The title of that section.
            index (int): The order the group sits in within the report type.
            attribute_group_items (list[AttributeGroupItemExport]): The fields in the group.
        """
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.attribute_group_items = attribute_group_items


class ReportTypeExportSchema(Schema):
    """A report type in the export document.

    Attributes:
        title (fields.Str): The name the report type shows; what an import matches an existing one by.
        description (fields.Str): What the report type is for.
        icon (fields.Str): The MDI icon it shows, None for the default.
        attribute_groups (fields.List): The groups of the report type.
    """

    class Meta:  # ty: ignore[incompatible-attribute-override]
        """Unknown keys in an import file are ignored rather than rejected."""

        unknown = EXCLUDE

    title = fields.Str(required=True)
    description = fields.Str(load_default="")
    icon = fields.Str(load_default=None, allow_none=True)
    attribute_groups = fields.List(fields.Nested(AttributeGroupExportSchema), load_default=list)

    @post_load
    def make(self, data: dict, **kwargs) -> ReportTypeExport:  # noqa: ANN003, ARG002
        """Build the exported report type.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            ReportTypeExport: The exported report type.
        """
        return ReportTypeExport(**data)


class ReportTypeExport:
    """A report type in the export document.

    Attributes:
        title (str): The name the report type shows; what an import matches an existing one by.
        description (str): What the report type is for.
        icon (str | None): The MDI icon it shows, None for the default.
        attribute_groups (list[AttributeGroupExport]): The groups of the report type.
    """

    def __init__(self, title: str, description: str, icon: str | None, attribute_groups: list[AttributeGroupExport]) -> None:
        """Initialize an exported report type.

        Args:
            title (str): The name the report type shows.
            description (str): What the report type is for.
            icon (str | None): The MDI icon it shows, None for the default.
            attribute_groups (list[AttributeGroupExport]): The groups of the report type.
        """
        self.title = title
        self.description = description
        self.icon = icon
        self.attribute_groups = attribute_groups


class ReportTypeExportRootSchema(Schema):
    """The root of a report type export document.

    Attributes:
        version (fields.Int): The format version, so a later change can be told from this one.
        report_types (fields.List): The report types being exported.
        attribute_types (fields.List): Definitions of every attribute type those report types use.
    """

    class Meta:  # ty: ignore[incompatible-attribute-override]
        """Unknown keys in an import file are ignored rather than rejected."""

        unknown = EXCLUDE

    version = fields.Int(required=True)
    report_types = fields.List(fields.Nested(ReportTypeExportSchema), load_default=list)
    attribute_types = fields.List(fields.Nested(AttributeTypeExportSchema), load_default=list)

    @post_load
    def make(self, data: dict, **kwargs) -> ReportTypeExportRoot:  # noqa: ANN003, ARG002
        """Build the export document.

        Args:
            data (dict): The loaded data.
            **kwargs: Extra arguments marshmallow passes to post_load hooks.

        Returns:
            ReportTypeExportRoot: The export document.
        """
        return ReportTypeExportRoot(**data)


class ReportTypeExportRoot:
    """The root of a report type export document.

    Attributes:
        version (int): The format version.
        report_types (list[ReportTypeExport]): The report types being exported.
        attribute_types (list[AttributeTypeExport]): Definitions of every attribute type they use.
    """

    def __init__(self, version: int, report_types: list[ReportTypeExport], attribute_types: list[AttributeTypeExport]) -> None:
        """Initialize the export document.

        Args:
            version (int): The format version.
            report_types (list[ReportTypeExport]): The report types being exported.
            attribute_types (list[AttributeTypeExport]): Definitions of every attribute type they use.
        """
        self.version = version
        self.report_types = report_types
        self.attribute_types = attribute_types
