"""Presenter timestamps stay UTC while calendar dates keep their template shape."""

from datetime import date, datetime, timedelta, timezone

import pytest
from presenters.base_presenter import BasePresenter
from presenters.jinja_filters import filter_strfdate


def test_datetime_serialization_preserves_utc_instant() -> None:
    instant = datetime(2026, 7, 2, 0, 30, tzinfo=timezone(timedelta(hours=2)))
    assert BasePresenter.json_default(instant) == "2026-07-01T22:30:00Z"
    assert BasePresenter.to_template_data({"created": instant}) == {"created": "2026-07-01T22:30:00Z"}


def test_calendar_date_serialization_is_unchanged() -> None:
    value = date(2026, 7, 2)
    assert BasePresenter.json_default(value) == {"year": 2026, "month": 7, "day": 2}
    assert BasePresenter.to_template_data(value) == {"year": 2026, "month": 7, "day": 2}


@pytest.mark.parametrize("value", ["2026-07-01T22:30:00Z", "2026-07-02T00:30:00+02:00"])
def test_template_date_filter_accepts_api_timestamps(value: str) -> None:
    assert filter_strfdate(value, fmtout="%Y-%m-%d %H:%M") == "2026-07-01 22:30"


def test_template_date_filter_honors_explicit_offsets() -> None:
    assert filter_strfdate("2026/07/02 00:30 +0200", fmtin="%Y/%m/%d %H:%M %z", fmtout="%Y-%m-%d %H:%M") == "2026-07-01 22:30"
