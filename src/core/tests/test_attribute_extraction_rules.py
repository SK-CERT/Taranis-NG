"""Attribute extraction rules: creation, validation and scoping.

The matching itself is covered exhaustively in `src/shared/tests` — the matcher is a pure
function and lives there. What is left to pin on the core side is everything that depends on
the database or on configuration: creating a rule the way the GUI sends it, rejecting a bad
pattern before it can reach a collector, and limiting a rule to source groups - including the
payload that tells collectors which sources a scoped rule covers.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api.config import _attribute_extraction_rule_rejection
from model.attribute_extraction_rule import (
    AttributeExtractionRule,
    AttributeExtractionRuleOSINTSourceGroup,
    NewAttributeExtractionRuleSchema,
)
from shared.schema.attribute_extraction_rule import AttributeExtractionRuleSchema

VALID_RULE = {"name": "CVE", "attribute_key": "CVE", "pattern": r"CVE-\d{4}-\d{4,}"}


def test_a_new_rule_needs_no_id() -> None:
    # The GUI creates a rule without an id. When the constructor required one, every create
    # failed with a TypeError that surfaced as a generic 400.
    rule = NewAttributeExtractionRuleSchema().load(VALID_RULE)
    assert isinstance(rule, AttributeExtractionRule)
    assert rule.name == "CVE"
    assert rule.osint_source_groups == []


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"name": ""}, "name"),
        ({"attribute_key": ""}, "attribute_key"),
        ({"pattern": ""}, "pattern"),
        ({"capture_group": -1}, "capture_group"),
        ({"max_matches": 0}, "max_matches"),
    ],
)
def test_an_incomplete_or_out_of_range_rule_is_rejected(change: dict, field: str) -> None:
    assert field in AttributeExtractionRuleSchema().validate({**VALID_RULE, **change})


def test_a_complete_rule_passes_validation() -> None:
    assert AttributeExtractionRuleSchema().validate(VALID_RULE) == {}


def test_a_valid_pattern_is_accepted() -> None:
    assert AttributeExtractionRule.validate_pattern(r"CVE-\d{4}-\d{4,}") is None


@pytest.mark.parametrize("pattern", ["(unclosed", "a{2,1}", "[z-a]", "*nothing-to-repeat"])
def test_an_invalid_pattern_is_reported(pattern: str) -> None:
    # The API rejects on this, so a typo fails in the GUI rather than silently inside a
    # collector at its next refresh.
    error = AttributeExtractionRule.validate_pattern(pattern)
    assert error, f"{pattern!r} should not compile"
    assert isinstance(error, str)


@pytest.mark.parametrize("pattern", [r"(?P<id>CVE-\d+)", r"(?i)cve-\d+"])
def test_python_only_syntax_is_accepted(pattern: str) -> None:
    # The collectors run Python patterns; a browser RegExp would reject both of these.
    assert AttributeExtractionRule.validate_pattern(pattern) is None


def test_a_capture_group_the_pattern_lacks_is_reported() -> None:
    assert AttributeExtractionRule.validate_pattern(r"INC-(\d+)", 1) is None
    assert AttributeExtractionRule.validate_pattern(r"INC-(\d+)", 2)


def test_an_invalid_pattern_is_rejected_with_the_engine_message_apart() -> None:
    # The GUI puts `pattern_error` into its own translated sentence; `error` stays for API callers.
    body, status = _attribute_extraction_rule_rejection({**VALID_RULE, "pattern": "(unclosed"})
    assert status == HTTPStatus.BAD_REQUEST
    assert body["pattern_error"] == "missing ) at position 9"
    assert body["error"] == "Invalid regular expression: missing ) at position 9"


def test_an_empty_pattern_compiles() -> None:
    # Empty is not a syntax error; the matcher skips rules with no pattern instead.
    assert AttributeExtractionRule.validate_pattern("") is None
    assert AttributeExtractionRule.validate_pattern(None) is None


def _applies(groups: list, source: object) -> bool:
    """Run the scoping check against a stand-in rule.

    Called unbound with a plain object as `self`: instantiating the model would need a
    SQLAlchemy session for the relationship, and the method only reads one attribute.
    """
    return AttributeExtractionRule.applies_to_source(types.SimpleNamespace(osint_source_groups=groups), source)


def _group(group_id: str, sources: list | None = None) -> types.SimpleNamespace:
    return types.SimpleNamespace(id=group_id, osint_sources=sources or [])


def test_an_unscoped_rule_applies_to_every_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "model.attribute_extraction_rule.OSINTSourceGroup",
        types.SimpleNamespace(get_for_osint_source=lambda _id: []),
    )
    assert _applies([], types.SimpleNamespace(id="any")) is True


def test_an_unscoped_rule_applies_even_without_a_source(monkeypatch: pytest.MonkeyPatch) -> None:
    # A manually added item may carry no source at all.
    monkeypatch.setattr(
        "model.attribute_extraction_rule.OSINTSourceGroup",
        types.SimpleNamespace(get_for_osint_source=lambda _id: []),
    )
    assert _applies([], None) is True


def test_a_scoped_rule_applies_inside_its_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "model.attribute_extraction_rule.OSINTSourceGroup",
        types.SimpleNamespace(get_for_osint_source=lambda _id: [_group("g1"), _group("g2")]),
    )
    assert _applies([_group("g2")], types.SimpleNamespace(id="src")) is True


def test_a_scoped_rule_does_not_apply_outside_its_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "model.attribute_extraction_rule.OSINTSourceGroup",
        types.SimpleNamespace(get_for_osint_source=lambda _id: [_group("g1")]),
    )
    assert _applies([_group("other")], types.SimpleNamespace(id="src")) is False


def test_a_scoped_rule_does_not_apply_to_a_sourceless_item(monkeypatch: pytest.MonkeyPatch) -> None:
    # There is no group membership to check, so a group-limited rule must not fire.
    monkeypatch.setattr(
        "model.attribute_extraction_rule.OSINTSourceGroup",
        types.SimpleNamespace(get_for_osint_source=lambda _id: []),
    )
    assert _applies([_group("g1")], None) is False


def test_a_scoped_rule_covers_every_source_in_its_groups() -> None:
    groups = [
        _group("g1", sources=[types.SimpleNamespace(id="s1"), types.SimpleNamespace(id="s2")]),
        _group("g2", sources=[types.SimpleNamespace(id="s2")]),
    ]
    assert AttributeExtractionRule.osint_source_ids(types.SimpleNamespace(osint_source_groups=groups)) == {"s1", "s2"}


def test_collectors_receive_the_sources_a_scoped_rule_covers(monkeypatch: pytest.MonkeyPatch) -> None:
    # The sources a collector receives do not say which groups they are in, so without these ids
    # a scoped rule could never be matched against a collected item.
    rule = types.SimpleNamespace(
        id=1,
        name="CVE",
        attribute_key="CVE",
        pattern="x",
        description="",
        enabled=True,
        capture_group=0,
        max_matches=100,
        osint_source_groups=[_group("g1")],
        osint_source_ids=lambda: {"s2", "s1"},
    )
    monkeypatch.setattr(AttributeExtractionRule, "get_all_enabled", classmethod(lambda _cls: [rule]))

    [item] = AttributeExtractionRule.get_enabled_for_collectors_json()

    assert item["osint_source_groups"] == [{"id": "g1"}]
    assert item["osint_source_ids"] == ["s1", "s2"]


def test_the_model_scope_table_cascades_like_the_migration() -> None:
    # create_app() runs db.create_all(), so a core started before migration d4f1c8a70b62 builds
    # this table from the model. Without the cascades that table differed from a migrated one.
    foreign_keys = AttributeExtractionRuleOSINTSourceGroup.__table__.foreign_keys
    assert {key.target_fullname: key.ondelete for key in foreign_keys} == {
        "attribute_extraction_rule.id": "CASCADE",
        "osint_source_group.id": "CASCADE",
    }
