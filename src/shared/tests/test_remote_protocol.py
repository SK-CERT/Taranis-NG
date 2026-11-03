"""Remote protocol boundaries preserve legacy peers without weakening UTC v2."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from marshmallow import ValidationError
from shared.remote_protocol import (
    default_legacy_timezone,
    format_remote_timestamp,
    legacy_news_items,
    normalize_legacy_news_items,
    parse_remote_timestamp,
    validate_remote_news_items,
)
from shared.schema.datetime import PublicationTimestamp
from shared.schema.remote import RemoteAccessSchema, RemoteNodeSchema


@pytest.mark.parametrize(
    ("value", "zone", "expected"),
    [
        ("2026-11-03 11:00:00.000000", "Europe/Bratislava", "2026-11-03T10:00:00+00:00"),
        ("03.07.2026 - 12:00", "Europe/Bratislava", "2026-07-03T10:00:00+00:00"),
        ("2026-11-03 11:00:00.000000+03:00", "Europe/Bratislava", "2026-11-03T08:00:00+00:00"),
        ("2026-11-03 05:00:00.000000", "America/New_York", "2026-11-03T10:00:00+00:00"),
    ],
)
def test_v1_timezone_boundary(value: str, zone: str, expected: str) -> None:
    assert parse_remote_timestamp(value, version=1, legacy_timezone=zone).isoformat() == expected


def test_v1_cursor_is_parseable_by_unmodified_old_node() -> None:
    instant = datetime(2026, 11, 3, 10, tzinfo=UTC)
    cursor = format_remote_timestamp(instant, version=1, legacy_timezone="Europe/Bratislava", cursor=True)
    assert cursor == "2026-11-03 11:00:00.000000"
    assert datetime.strptime(cursor, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=UTC).hour == 11
    assert parse_remote_timestamp(cursor, version=1, legacy_timezone="Europe/Bratislava") == instant


@pytest.mark.parametrize("value", ["2026-11-03 10:00:00", "03.11.2026 - 10:00", "2026-11-03", "bad"])
def test_v2_rejects_missing_offsets(value: str) -> None:
    with pytest.raises(ValidationError):
        parse_remote_timestamp(value, version=2)


def test_v2_normalizes_explicit_offsets() -> None:
    assert parse_remote_timestamp("2026-11-03T11:00:07+01:00", version=2) == datetime(2026, 11, 3, 10, 0, 7, tzinfo=UTC)
    assert format_remote_timestamp("2026-11-03T11:00:07+01:00", version=2) == "2026-11-03T10:00:07Z"


def test_news_adapters_only_change_known_metadata() -> None:
    items = [{"collected": "2026-11-03T10:00:00Z", "published": "2026-11-03T10:00:07Z", "attributes": [{"created": "source text"}]}]
    legacy = legacy_news_items(items, "Europe/Bratislava")
    assert legacy[0]["collected"] == "03.11.2026 - 11:00"
    assert legacy[0]["published"] == "03.11.2026 - 11:00"
    assert items[0]["collected"] == "2026-11-03T10:00:00Z"
    imported = normalize_legacy_news_items(legacy, "Europe/Bratislava")
    assert imported[0]["collected"] == "2026-11-03T10:00:00Z"
    # No provenance says whether an old provider's publication clock was RSS UTC or local.
    assert imported[0]["published"] == "03.11.2026 - 11:00"
    assert imported[0]["attributes"] == [{"created": "source text"}]
    validate_remote_news_items(imported)


def test_naive_legacy_publication_text_survives_serialization() -> None:
    field = PublicationTimestamp()
    assert field.serialize("published", SimpleNamespace(published="03.11.2026 - 10:00")) == "03.11.2026 - 10:00"
    assert field.serialize("published", SimpleNamespace(published="2026-11-03T11:00:07+01:00")) == "2026-11-03T10:00:07Z"


@pytest.mark.parametrize("schema_type", [RemoteNodeSchema, RemoteAccessSchema])
def test_legacy_timezone_is_validated_and_installation_defaulted(schema_type: type, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARANIS_NG_LEGACY_TZ", "Europe/Bratislava")
    monkeypatch.setenv("TZ", "UTC")
    assert default_legacy_timezone() == "Europe/Bratislava"
    assert schema_type().load({})["legacy_timezone"] == "Europe/Bratislava"
    assert schema_type().load({"legacy_timezone": "America/New_York"})["legacy_timezone"] == "America/New_York"
    with pytest.raises(ValidationError):
        schema_type().load({"legacy_timezone": "not-a-timezone"})
