"""Multiple choice attributes must reach templates as a list, not a joined string.

A MULTI_CHOICE attribute keeps every ticked value in one newline-joined row, so the
shape templates receive cannot be derived from ``max_occurrence`` the way it is for
every other type. This is the only place that conversion happens, and the GUI tests
cannot see it.
"""

from __future__ import annotations

from types import SimpleNamespace

from presenters.base_presenter import BasePresenter
from shared.schema.attribute import AttributeType

GROUP_ITEM_ID = 7
REPORT_TYPES = {1: SimpleNamespace(title="Test report", description="")}


def _group_item(title: str, attribute_type: AttributeType, max_occurrence: int) -> SimpleNamespace:
    return SimpleNamespace(
        title=title,
        max_occurrence=max_occurrence,
        attribute=SimpleNamespace(type=attribute_type),
    )


def _attribute(value: str) -> SimpleNamespace:
    return SimpleNamespace(attribute_group_item_id=GROUP_ITEM_ID, value=value, value_description=None)


def _attrs_for(group_item: SimpleNamespace, attributes: list[SimpleNamespace]) -> object:
    report_item = SimpleNamespace(
        title="Example",
        title_prefix="EX",
        uuid="uuid-1",
        created=None,
        last_updated=None,
        report_item_type_id=1,
        news_item_aggregates=[],
        attributes=attributes,
    )
    return BasePresenter.ReportItemObject(report_item, REPORT_TYPES, {GROUP_ITEM_ID: group_item}).attrs


def test_multi_choice_yields_a_list_even_when_max_occurrence_is_one() -> None:
    group_item = _group_item("Sectors", AttributeType.MULTI_CHOICE, max_occurrence=1)

    attrs = _attrs_for(group_item, [_attribute("Energy\nTransport\nHealth")])

    assert attrs.sectors == ["Energy", "Transport", "Health"]


def test_multi_choice_with_nothing_ticked_yields_an_empty_list() -> None:
    group_item = _group_item("Sectors", AttributeType.MULTI_CHOICE, max_occurrence=1)

    attrs = _attrs_for(group_item, [_attribute("")])

    assert attrs.sectors == []


def test_other_types_keep_the_scalar_shape_max_occurrence_asks_for() -> None:
    group_item = _group_item("Description", AttributeType.STRING, max_occurrence=1)

    attrs = _attrs_for(group_item, [_attribute("A single string")])

    assert attrs.description == "A single string"
