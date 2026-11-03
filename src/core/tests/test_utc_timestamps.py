"""UTC storage defaults and direct API responses obey the shared wire contract."""

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from api.public_web import _serialize_product
from managers.db_manager import db
from marshmallow import ValidationError
from model.attribute import Attribute
from model.log_record import LogRecord
from model.report_item import ReportItemAttribute, _normalize_datetime_attributes
from shared.datetime_utils import format_datetime
from shared.schema.attribute import AttributeType
from sqlalchemy import create_engine, insert, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable


def test_model_timestamp_columns_are_timezone_aware() -> None:
    columns = [column for table in db.metadata.tables.values() for column in table.columns if isinstance(column.type, db.DateTime)]
    assert columns
    assert all(column.type.timezone for column in columns)
    assert "TIMESTAMP WITH TIME ZONE" in str(CreateTable(LogRecord.__table__).compile(dialect=postgresql.dialect()))


def test_timestamp_defaults_are_evaluated_for_each_insert() -> None:
    engine = create_engine("sqlite://")
    table = LogRecord.__table__
    table.create(engine)
    with engine.begin() as connection:
        connection.execute(insert(table).values(id=1))
        first = connection.execute(select(table.c.timestamp).where(table.c.id == 1)).scalar_one()
        connection.execute(insert(table).values(id=2))
        second = connection.execute(select(table.c.timestamp).where(table.c.id == 2)).scalar_one()
    assert second > first
    assert abs((datetime.now(UTC) - first.replace(tzinfo=UTC)).total_seconds()) < 5


def test_direct_public_web_response_normalizes_offsets() -> None:
    stamp = datetime(2026, 7, 10, 1, 30, tzinfo=timezone(timedelta(hours=2)))
    report = SimpleNamespace(
        title="Report",
        title_prefix="",
        uuid="uuid",
        created=stamp,
        last_updated=stamp,
        report_item_type=None,
        attributes=[],
        links=[],
    )
    product = SimpleNamespace(id=1, title="Product", description="", created=stamp, user=None, report_items=[report], links=[])
    response = _serialize_product(product)
    assert response["created"] == "2026-07-09T23:30:00Z"
    assert response["report_items"][0]["created"] == response["created"]
    assert response["report_items"][0]["last_updated"] == response["created"]


@pytest.mark.parametrize(
    ("kind", "value", "expected"),
    [
        (AttributeType.DATE_TIME, "2026-07-10T01:30:00+02:00", "2026-07-09T23:30:00Z"),
        (AttributeType.DATE_TIME, "2026-07-10T01:30", "2026-07-10T01:30:00Z"),
        (AttributeType.DATE, "2026-07-10", "2026-07-10"),
        (AttributeType.TEXT, "2026-07-10T01:30", "2026-07-10T01:30"),
        (AttributeType.DATE_TIME, "", ""),
    ],
)
def test_datetime_attribute_writes_are_normalized(kind: AttributeType, value: str, expected: str) -> None:
    attribute = ReportItemAttribute(None, value, "", None, 0, None, 1, "Timestamp")
    group = SimpleNamespace(attribute=SimpleNamespace(type=kind))
    session = SimpleNamespace(new={attribute}, dirty=set(), get=lambda *_: group)
    _normalize_datetime_attributes(session, None, None)
    assert attribute.value == expected


def test_invalid_datetime_attribute_is_validation_error() -> None:
    attribute = ReportItemAttribute(None, "invalid", "", None, 0, None, 1, "Timestamp")
    group = SimpleNamespace(attribute=SimpleNamespace(type=AttributeType.DATE_TIME))
    session = SimpleNamespace(new={attribute}, dirty=set(), get=lambda *_: group)
    with pytest.raises(ValidationError):
        _normalize_datetime_attributes(session, None, None)


def test_all_creation_defaults_return_aware_utc_values() -> None:
    columns = [
        column for table in db.metadata.tables.values() for column in table.columns if isinstance(column.type, db.DateTime) and column.default
    ]
    assert columns
    for column in columns:
        assert column.default.is_callable, column
        value = column.default.arg(None)
        assert value.tzinfo is UTC, column
        assert format_datetime(value).endswith("Z")


@pytest.mark.parametrize(
    ("kind", "value", "expected"),
    [
        (AttributeType.DATE_TIME, "2026-07-10T01:30:00+02:00", "2026-07-09T23:30:00Z"),
        (AttributeType.DATE_TIME, "2026-07-10T01:30", "2026-07-10T01:30:00Z"),
        (AttributeType.DATE, "2026-07-10", "2026-07-10"),
        (AttributeType.TEXT, "arbitrary", "arbitrary"),
    ],
)
def test_configured_datetime_defaults_are_canonical(kind: AttributeType, value: str, expected: str) -> None:
    attribute = Attribute(None, "Default", "", kind, value, None, None, [])
    assert attribute.default_value == expected
