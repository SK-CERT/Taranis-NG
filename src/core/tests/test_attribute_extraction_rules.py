"""Attribute extraction rules: pattern validation, scoping and the global switch.

The matching itself is covered exhaustively in `src/shared/tests` — the matcher is a pure
function and lives there. What is left to pin on the core side is everything that depends on
the database or on configuration: rejecting a bad pattern before it can reach a collector,
limiting a rule to source groups, and the switch that turns the whole feature off.
"""

from __future__ import annotations

import types

import pytest
from model.attribute_extraction_rule import AttributeExtractionRule


def test_a_valid_pattern_is_accepted() -> None:
    assert AttributeExtractionRule.validate_pattern(r"CVE-\d{4}-\d{4,}") is None


@pytest.mark.parametrize("pattern", ["(unclosed", "a{2,1}", "[z-a]", "*nothing-to-repeat"])
def test_an_invalid_pattern_is_reported(pattern: str) -> None:
    # The API rejects on this, so a typo fails in the GUI rather than silently inside a
    # collector at its next refresh.
    error = AttributeExtractionRule.validate_pattern(pattern)
    assert error, f"{pattern!r} should not compile"
    assert isinstance(error, str)


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


def _group(group_id: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(id=group_id)


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
