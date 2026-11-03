"""UTC wire contract stays independent of process timezone."""

import os
import time
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from marshmallow import Schema, ValidationError
from shared.datetime_utils import format_datetime, normalize_timestamp, parse_datetime, utc_now
from shared.schema.datetime import UTCDateTime
from shared.schema.news_item import NewsItemDataBaseSchema
from shared.schema.product import ProductSchema
from shared.schema.setting import SettingSchema
from shared.time_manager import SchedulerManager


@pytest.mark.parametrize("process_timezone", ["UTC", "Europe/Bratislava", "America/New_York"])
def test_utc_contract_ignores_process_timezone(process_timezone: str) -> None:
    previous = os.environ.get("TZ")
    try:
        os.environ["TZ"] = process_timezone
        time.tzset()
        assert utc_now().tzinfo is UTC
        assert format_datetime("2026-07-10 12:30") == "2026-07-10T12:30:00Z"
        assert parse_datetime("2026-07-10T14:30:00+02:00") == datetime(2026, 7, 10, 12, 30, tzinfo=UTC)
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


@pytest.mark.parametrize(
    "value",
    ["02.11.2026 - 12:30", "02.11.2026 - 12:30:00", "02.11.2026 12:30:00", "2026-11-02 12:30", "2026-11-02T12:30:00Z"],
)
def test_legacy_inputs_are_utc(value: str) -> None:
    assert format_datetime(value) == "2026-11-02T12:30:00Z"


def test_explicit_offsets_and_precision_are_preserved_as_instants() -> None:
    assert format_datetime("2026-11-02T12:30:01.123456-05:00") == "2026-11-02T17:30:01.123456Z"
    assert format_datetime(datetime(2026, 7, 10, 14, 30, tzinfo=timezone(timedelta(hours=2)))) == "2026-07-10T12:30:00Z"
    assert parse_datetime("2026-07-10 14:30", default_timezone=ZoneInfo("Europe/Bratislava")) == datetime(2026, 7, 10, 12, 30, tzinfo=UTC)
    assert format_datetime(None) is None


@pytest.mark.parametrize("value", [None, "", "2026-07-10", "20260710", "2026-W28-5", "10.07.2026", "unknown", "Yesterday"])
def test_source_publication_text_and_calendar_dates_are_preserved(value: str | None) -> None:
    assert normalize_timestamp(value) == value


def test_schemas_emit_iso_utc_instead_of_display_strings() -> None:
    value = datetime(2026, 7, 10, 14, 30, tzinfo=timezone(timedelta(hours=2)))
    assert NewsItemDataBaseSchema().dump({"published": "2026-07-10T14:30:00+02:00", "collected": value}) == {
        "published": "2026-07-10T12:30:00Z",
        "collected": "2026-07-10T12:30:00Z",
    }
    assert ProductSchema().dump({"created": value})["created"] == "2026-07-10T12:30:00Z"
    assert SettingSchema().dump({"updated_at": value})["updated_at"] == "2026-07-10T12:30:00Z"


def test_schema_rejects_invalid_inputs_and_accepts_nullable_values() -> None:
    class Payload(Schema):
        stamp = UTCDateTime(allow_none=True)

    assert Payload().load({"stamp": None}) == {"stamp": None}
    assert Payload().load({"stamp": "2026-11-02T13:30+01:00"}) == {"stamp": datetime(2026, 11, 2, 12, 30, tzinfo=UTC)}
    with pytest.raises(ValidationError):
        Payload().load({"stamp": "not a timestamp"})


def test_wall_clock_schedules_explicitly_use_utc() -> None:
    job = SchedulerManager.schedule_job_every_day("12:30", lambda: None, "UTC test", tags=("utc-test",))
    try:
        assert str(job.at_time_zone) == "UTC"
    finally:
        SchedulerManager.cancel_jobs_by_tag("utc-test")
