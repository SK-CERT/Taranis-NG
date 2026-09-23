"""Attribute extraction in the collector: which rules apply to a source, and when they reload.

The matcher is covered in `src/shared/tests`. What is pinned here is the collector's side of the
contract with core: a scoped rule arrives with the ids of the sources it covers, because the
sources a collector receives do not say which groups they belong to, and rule edits are picked up
without a restart, because core never pushes them.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from collectors.base_collector import BaseCollector
from remote.core_api import CoreApi
from shared.schema.attribute_extraction_rule import AttributeExtractionRule, AttributeExtractionRuleSchema

if TYPE_CHECKING:
    from collections.abc import Iterator


def core_payload(*rules: tuple[str, str, list[str], list[str]]) -> dict:
    """Build the rules response the way core does: schema dump plus the covered source ids.

    Args:
        rules: (name, pattern, group ids, covered source ids) for each rule.

    Returns:
        dict: The response body.
    """
    items = []
    for name, pattern, group_ids, source_ids in rules:
        rule = AttributeExtractionRule(
            name=name,
            attribute_key=name,
            pattern=pattern,
            osint_source_groups=[types.SimpleNamespace(id=group_id) for group_id in group_ids],
            id=len(items) + 1,
        )
        item = AttributeExtractionRuleSchema().dump(rule)
        item["osint_source_ids"] = sorted(source_ids)
        items.append(item)
    return {"enabled": bool(items), "items": items}


def news_item(text: str) -> types.SimpleNamespace:
    """The fields of a collected item that extraction reads and writes."""
    return types.SimpleNamespace(title=text, review="", content="", attributes=[])


def found(item: types.SimpleNamespace) -> list[tuple[str, str]]:
    return [(attribute.key, attribute.value) for attribute in item.attributes]


@pytest.fixture(autouse=True)
def _isolated_rule_cache() -> Iterator[None]:
    """Each test starts with no rules cached, and leaves none behind."""
    saved = (BaseCollector.attribute_extraction_rules, BaseCollector._attribute_extraction_rules_fetched_at)
    BaseCollector.attribute_extraction_rules = []
    BaseCollector._attribute_extraction_rules_fetched_at = None
    yield
    BaseCollector.attribute_extraction_rules, BaseCollector._attribute_extraction_rules_fetched_at = saved


@pytest.fixture
def core(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Stand in for core's rules endpoint; set `.response` and count `.calls`."""
    state = types.SimpleNamespace(response=(core_payload(), HTTPStatus.OK), calls=0)

    def get_rules() -> tuple[dict, HTTPStatus]:
        state.calls += 1
        return state.response

    monkeypatch.setattr(CoreApi, "get_attribute_extraction_rules", get_rules)
    return state


TEXT = "Fixes CVE-2024-1234 and GHSA-2345-6789-cfgh"


def test_an_unscoped_rule_applies_to_every_source(core: types.SimpleNamespace) -> None:
    core.response = (core_payload(("CVE", r"CVE-\d{4}-\d+", [], [])), HTTPStatus.OK)
    collector = BaseCollector()
    collector.refresh_attribute_extraction_rules()

    [item] = collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="any-source"))

    assert found(item) == [("CVE", "CVE-2024-1234")]


def test_a_scoped_rule_applies_only_to_the_sources_it_covers(core: types.SimpleNamespace) -> None:
    core.response = (core_payload(("GHSA", r"GHSA-[\w-]+", ["g1"], ["inside"])), HTTPStatus.OK)
    collector = BaseCollector()
    collector.refresh_attribute_extraction_rules()

    [inside] = collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="inside"))
    [outside] = collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="outside"))

    assert found(inside) == [("GHSA", "GHSA-2345-6789-cfgh")]
    assert found(outside) == []


def test_a_rule_scoped_to_empty_groups_applies_nowhere(core: types.SimpleNamespace) -> None:
    # Limited to groups with no sources in them is not the same as unscoped.
    core.response = (core_payload(("CVE", r"CVE-\d{4}-\d+", ["empty-group"], [])), HTTPStatus.OK)
    collector = BaseCollector()
    collector.refresh_attribute_extraction_rules()

    [item] = collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="any-source"))

    assert found(item) == []


def test_rules_are_reloaded_once_the_cache_is_stale(core: types.SimpleNamespace) -> None:
    collector = BaseCollector()
    collector.refresh_attribute_extraction_rules()
    assert core.calls == 1

    # Fresh: publishing uses the cached (empty) set without asking core again.
    collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="s"))
    assert core.calls == 1

    # An administrator adds a rule; once the cache ages out, the next batch picks it up.
    core.response = (core_payload(("CVE", r"CVE-\d{4}-\d+", [], [])), HTTPStatus.OK)
    BaseCollector._attribute_extraction_rules_fetched_at -= BaseCollector.ATTRIBUTE_EXTRACTION_RULES_MAX_AGE
    [item] = collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="s"))

    assert core.calls == 2
    assert found(item) == [("CVE", "CVE-2024-1234")]


def test_a_failed_fetch_keeps_the_previous_rules(core: types.SimpleNamespace) -> None:
    core.response = (core_payload(("CVE", r"CVE-\d{4}-\d+", [], [])), HTTPStatus.OK)
    collector = BaseCollector()
    collector.refresh_attribute_extraction_rules()

    core.response = ({"error": "Get attribute extraction rules failed"}, HTTPStatus.INTERNAL_SERVER_ERROR)
    collector.refresh_attribute_extraction_rules()
    [item] = collector.extract_attributes([news_item(TEXT)], types.SimpleNamespace(id="s"))

    assert found(item) == [("CVE", "CVE-2024-1234")]
