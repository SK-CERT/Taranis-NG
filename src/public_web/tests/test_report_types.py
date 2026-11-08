"""The types of reports a web shows: their product presets, named by key or else id (lib.web.report_types)."""

from __future__ import annotations

from lib.web.report_types import find_type, of_type, report_types, type_of


def _report(number: int, preset: dict | None) -> dict:
    return {"id": number, "product_preset": preset}


GCVE = {"id": 13, "title": "GCVE Advisory", "key": "gcve"}
BULLETIN = {"id": 3, "title": "bulletins", "key": None}
REPORTS = [_report(1, GCVE), _report(2, BULLETIN), _report(3, GCVE), _report(4, None), _report(5, {"id": 9, "title": " "})]


def test_a_type_is_the_presets_key_or_else_its_id() -> None:
    assert [type_of(report) for report in REPORTS] == ["gcve", "3", "gcve", None, "9"]


def test_the_types_come_once_each_by_name() -> None:
    # Untitled presets name no tab; reports without a preset have no type.
    assert report_types(REPORTS) == [{"id": "3", "title": "bulletins"}, {"id": "gcve", "title": "GCVE Advisory"}]


def test_the_reports_of_a_type_keep_their_order() -> None:
    assert [report["id"] for report in of_type(REPORTS, "gcve")] == [1, 3]


def test_only_a_type_the_reports_have_is_found() -> None:
    assert find_type(REPORTS, "gcve") == {"id": "gcve", "title": "GCVE Advisory"}
    assert find_type(REPORTS, "13") is None
    assert find_type(REPORTS, None) is None
