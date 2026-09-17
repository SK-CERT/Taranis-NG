"""Schema for the rules that detect values in news item text.

Shared because the payload crosses two boundaries: the GUI edits these through core's config
API, and the collectors fetch them to run against the text they have just collected.
"""

from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.osint_source import OSINTSourceGroupIdSchema
from shared.schema.presentation import PresentationSchema


class AttributeExtractionRule:
    """One detection rule."""

    def __init__(
        self,
        id: int,  # noqa: A002
        name: str,
        attribute_key: str,
        pattern: str,
        description: str = "",
        enabled: bool = True,
        capture_group: int = 0,
        max_matches: int = 100,
        osint_source_groups: list | None = None,
    ) -> None:
        """Initialize an AttributeExtractionRule instance.

        Args:
            id (int): Unique identifier.
            name (str): Display name.
            attribute_key (str): Key of the news item attribute written on a hit.
            pattern (str): The regular expression.
            description (str): Free text.
            enabled (bool): Whether the rule runs.
            capture_group (int): Group to take; 0 means the whole match.
            max_matches (int): Upper bound on values this rule may contribute to one item.
            osint_source_groups (list | None): Groups the rule is limited to; empty means all.
        """
        self.id = id
        self.name = name
        self.attribute_key = attribute_key
        self.pattern = pattern
        self.description = description
        self.enabled = enabled
        self.capture_group = capture_group
        self.max_matches = max_matches
        self.osint_source_groups = osint_source_groups or []


class AttributeExtractionRuleSchema(Schema):
    """Marshmallow schema for AttributeExtractionRule."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    attribute_key = fields.Str()
    pattern = fields.Str()
    description = fields.Str(load_default="")
    enabled = fields.Bool(load_default=True)
    capture_group = fields.Int(load_default=0)
    max_matches = fields.Int(load_default=100)
    osint_source_groups = fields.List(fields.Nested(OSINTSourceGroupIdSchema), load_default=list)

    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)

    @post_load
    def make(self, data: dict, **kwargs) -> AttributeExtractionRule:  # noqa: ANN003, ARG002
        """Create an AttributeExtractionRule from deserialized data.

        Args:
            data (dict): The deserialized data.
            **kwargs: Additional keyword arguments.

        Returns:
            AttributeExtractionRule: The instance.
        """
        return AttributeExtractionRule(**data)


class AttributeExtractionRulePresentationSchema(AttributeExtractionRuleSchema, PresentationSchema):
    """Schema with presentation details for the configuration GUI."""
