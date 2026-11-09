"""Report item type icons: what is stored, and what a type and its reports show.

The models are built in memory (no database); commits are stubbed. Every model module is
imported first so the mappers can be configured.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from managers.db_manager import db

for _module in sorted((Path(__file__).parents[1] / "model").glob("*.py")):
    if _module.stem != "__init__":
        importlib.import_module(f"model.{_module.stem}")

from model.report_item import ReportItem  # noqa: E402 - after every mapper is registered
from model.report_item_type import NewReportItemTypeSchema, ReportItemType  # noqa: E402


def _submitted(**fields: object) -> dict:
    return {"id": -1, "title": "Vulnerability", "description": "", "attribute_groups": [], **fields}


@pytest.mark.parametrize(
    ("icon", "stored"),
    [
        ("mdi-bug", "mdi-bug"),
        ("  mdi-bug  ", "mdi-bug"),
        ("", None),
        (None, None),
        ("mdi-" + "x" * 60, "mdi-" + "x" * 46),
    ],
)
def test_the_icon_is_trimmed_and_an_empty_one_is_none(icon: str | None, stored: str | None) -> None:
    assert NewReportItemTypeSchema().load(_submitted(icon=icon)).icon == stored


def test_an_edit_changes_the_icon(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = ReportItemType(None, "Vulnerability", "", [], icon="mdi-bug")
    monkeypatch.setattr(db, "session", SimpleNamespace(get=lambda _model, _id: stored, commit=lambda: None))
    monkeypatch.setattr(ReportItemType, "_refuse_removing_used_fields", classmethod(lambda _cls, _old, _new: None))

    ReportItemType.update(7, _submitted(icon="mdi-shield-alert"))
    assert stored.icon == "mdi-shield-alert"

    ReportItemType.update(7, _submitted())
    assert stored.icon is None


def test_a_type_and_its_reports_show_its_icon_or_the_default() -> None:
    report_type = ReportItemType(None, "Vulnerability", "", [])
    report = SimpleNamespace(report_item_type=report_type)
    assert report_type.tag == ReportItem.tag.fget(report) == "mdi-file-table-outline"

    report_type.icon = "mdi-bug"
    assert report_type.tag == ReportItem.tag.fget(report) == "mdi-bug"

    report.report_item_type = None
    assert ReportItem.tag.fget(report) == "mdi-file-table-outline"
