"""Attribute extraction rule Model.

A rule detects values in news item text with a regular expression and stores each hit as a
news item attribute. Rules are global by default; attaching source groups narrows a rule to
those groups only.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from managers.db_manager import db
from marshmallow import post_load
from model.osint_source import OSINTSourceGroup
from shared.common import TZ
from shared.schema.attribute_extraction_rule import (
    AttributeExtractionRulePresentationSchema,
    AttributeExtractionRuleSchema,
)

if TYPE_CHECKING:
    from model.osint_source import OSINTSource


class NewAttributeExtractionRuleSchema(AttributeExtractionRuleSchema):
    """Schema for creating a rule."""

    @post_load
    def make(self, data: dict, **kwargs) -> AttributeExtractionRule:  # noqa: ANN003, ARG002
        """Create a new rule.

        Args:
            data (dict): Data to create the rule from.
            **kwargs: Additional keyword arguments.

        Returns:
            AttributeExtractionRule: The new rule.
        """
        return AttributeExtractionRule(**data)


class AttributeExtractionRuleOSINTSourceGroup(db.Model):
    """Association between a rule and the OSINT source groups it is limited to."""

    attribute_extraction_rule_id = db.Column(db.Integer, db.ForeignKey("attribute_extraction_rule.id"), primary_key=True)
    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id"), primary_key=True)


class AttributeExtractionRule(db.Model):
    """A regular expression that turns text in a news item into an attribute.

    Attributes:
        id (int): Rule ID.
        name (str): Display name.
        attribute_key (str): Key of the news item attribute written on a hit.
        pattern (str): The regular expression.
        description (str): Free text.
        enabled (bool): Whether the rule runs.
        capture_group (int): Group to take; 0 means the whole match.
        max_matches (int): Upper bound on values this rule may contribute to one item.
        osint_source_groups (list): Groups the rule is limited to; empty means every source.
        updated_by (str): User who last updated the record.
        updated_at (datetime): Timestamp of the last update.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)
    attribute_key = db.Column(db.String(), nullable=False)
    pattern = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), default="", server_default="")
    enabled = db.Column(db.Boolean(), nullable=False, default=True, server_default="true")
    capture_group = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    max_matches = db.Column(db.Integer, nullable=False, default=100, server_default="100")
    updated_by = db.Column(db.String())
    updated_at = db.Column(db.DateTime)

    osint_source_groups = db.relationship(
        "OSINTSourceGroup",
        secondary="attribute_extraction_rule_osint_source_group",
        lazy="selectin",
    )

    def __init__(
        self,
        id: int,  # noqa: A002, ARG002
        name: str,
        attribute_key: str,
        pattern: str,
        description: str = "",
        enabled: bool = True,
        capture_group: int = 0,
        max_matches: int = 100,
        osint_source_groups: list | None = None,
    ) -> None:
        """Create a new rule."""
        self.name = name
        self.attribute_key = attribute_key
        self.pattern = pattern
        self.description = description
        self.enabled = enabled
        self.capture_group = capture_group
        self.max_matches = max_matches
        self.osint_source_groups = self._resolve_groups(osint_source_groups)

    @staticmethod
    def _resolve_groups(groups: list | None) -> list:
        """Turn the schema's group stubs into persisted OSINTSourceGroup rows.

        Args:
            groups (list | None): Group stubs carrying an id, or None.

        Returns:
            list: The matching OSINTSourceGroup rows, ignoring ids that do not exist.
        """
        resolved = []
        for group in groups or []:
            group_id = getattr(group, "id", None) or (group.get("id") if isinstance(group, dict) else None)
            found = OSINTSourceGroup.find(group_id) if group_id else None
            if found:
                resolved.append(found)
        return resolved

    @staticmethod
    def validate_pattern(pattern: str) -> str | None:
        """Compile a pattern so a typo fails here rather than silently in a collector.

        Args:
            pattern (str): The regular expression to check.

        Returns:
            str | None: The compile error, or None when the pattern is valid.
        """
        try:
            re.compile(pattern or "")
        except re.error as error:
            return str(error)
        return None

    def applies_to_source(self, osint_source: OSINTSource | None) -> bool:
        """Tell whether this rule should run for a given source.

        Args:
            osint_source: The OSINT source a news item came from, or None.

        Returns:
            bool: True when the rule is unscoped, or the source is in one of its groups.
        """
        if not self.osint_source_groups:
            return True
        if osint_source is None:
            return False
        rule_group_ids = {group.id for group in self.osint_source_groups}
        source_group_ids = {group.id for group in OSINTSourceGroup.get_for_osint_source(osint_source.id)}
        return bool(rule_group_ids & source_group_ids)

    @classmethod
    def find(cls, id: int) -> AttributeExtractionRule | None:  # noqa: A002
        """Find a rule by ID.

        Args:
            id (int): Rule ID.

        Returns:
            AttributeExtractionRule: The rule, or None.
        """
        return db.session.get(cls, id)

    @classmethod
    def get_all(cls) -> list[AttributeExtractionRule]:
        """Get every rule.

        Returns:
            list: All rules, by name.
        """
        return cls.query.order_by(db.asc(AttributeExtractionRule.name)).all()

    @classmethod
    def get_all_enabled(cls) -> list[AttributeExtractionRule]:
        """Get the enabled rules only.

        Returns:
            list: Enabled rules, by name.
        """
        return cls.query.filter_by(enabled=True).order_by(db.asc(AttributeExtractionRule.name)).all()

    @classmethod
    def get(cls, search_string: str | None) -> tuple[list[AttributeExtractionRule], int]:
        """Get rules matching a search string.

        Args:
            search_string (str): Search string.

        Returns:
            tuple: The rules and the total count.
        """
        query = cls.query
        if search_string is not None:
            search = f"%{search_string}%"
            query = query.filter(
                db.or_(
                    AttributeExtractionRule.name.ilike(search),
                    AttributeExtractionRule.attribute_key.ilike(search),
                ),
            )
        return query.order_by(db.asc(AttributeExtractionRule.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search: str | None) -> dict:
        """Get all rules in JSON format.

        Args:
            search (str): Search query.

        Returns:
            dict: Total count and the rules.
        """
        rules, count = cls.get(search)
        schema = AttributeExtractionRulePresentationSchema(many=True)
        return {"total_count": count, "items": schema.dump(rules)}

    @classmethod
    def add_new(cls, data: dict, user_name: str) -> AttributeExtractionRule:
        """Add a new rule.

        Args:
            data (dict): The rule.
            user_name (str): User creating it.

        Returns:
            AttributeExtractionRule: The new rule.
        """
        schema = NewAttributeExtractionRuleSchema()
        new = schema.load(data)
        new.updated_by = user_name
        new.updated_at = datetime.now(TZ)
        db.session.add(new)
        db.session.commit()
        return new

    @classmethod
    def update(cls, id: int, data: dict, user_name: str) -> AttributeExtractionRule:  # noqa: A002
        """Update a rule.

        Args:
            id (int): Rule ID.
            data (dict): New values.
            user_name (str): User making the change.

        Returns:
            AttributeExtractionRule: The updated rule.
        """
        schema = NewAttributeExtractionRuleSchema()
        new = schema.load(data)
        old = db.session.get(cls, id)
        old.name = new.name
        old.attribute_key = new.attribute_key
        old.pattern = new.pattern
        old.description = new.description
        old.enabled = new.enabled
        old.capture_group = new.capture_group
        old.max_matches = new.max_matches
        old.osint_source_groups = new.osint_source_groups
        old.updated_by = user_name
        old.updated_at = datetime.now(TZ)
        db.session.commit()
        return old

    @classmethod
    def delete(cls, id: int) -> None:  # noqa: A002
        """Delete a rule.

        Args:
            id (int): Rule ID.
        """
        record = db.session.get(cls, id)
        db.session.delete(record)
        db.session.commit()
