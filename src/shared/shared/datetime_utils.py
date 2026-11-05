"""UTC timestamps for storage and machine interfaces; local time belongs to the GUI."""

from datetime import UTC, date, datetime, tzinfo
from typing import overload

LEGACY_DATETIME_FORMATS = (
    "%d.%m.%Y - %H:%M:%S",
    "%d.%m.%Y - %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


def utc_now() -> datetime:
    """Return the current instant as an aware UTC datetime."""
    return datetime.now(UTC)


def parse_datetime(value: str | datetime, *, default_timezone: tzinfo = UTC) -> datetime:
    """Parse ISO or legacy timestamps and normalize to UTC.

    Timezone-free input uses UTC by default, independent of the process timezone.
    Migration callers may explicitly supply the historical source timezone.
    """
    if isinstance(value, datetime):
        parsed = value
    else:
        if isinstance(value, str):
            value = value.strip()
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            for fmt in LEGACY_DATETIME_FORMATS:
                try:
                    parsed = datetime.strptime(value, fmt)  # noqa: DTZ007 - source timezone is attached below
                    break
                except (TypeError, ValueError):
                    continue
            else:
                msg = f"Invalid timestamp: {value!r}"
                raise ValueError(msg) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(UTC)


@overload
def format_datetime(value: None) -> None: ...


@overload
def format_datetime(value: str | datetime) -> str: ...


def format_datetime(value: str | datetime | None) -> str | None:
    """Serialize an instant as ISO 8601 UTC with an explicit Z suffix."""
    if value is None:
        return None
    return parse_datetime(value).isoformat().replace("+00:00", "Z")


@overload
def normalize_timestamp(value: None, *, default_timezone: tzinfo = UTC) -> None: ...


@overload
def normalize_timestamp(value: str | datetime, *, default_timezone: tzinfo = UTC) -> str: ...


def normalize_timestamp(value: str | datetime | None, *, default_timezone: tzinfo = UTC) -> str | None:
    """Normalize source timestamps, preserving missing, date-only and arbitrary text."""
    if value is None:
        return None
    if value == "":
        return ""
    if isinstance(value, datetime):
        return format_datetime(value)
    # A publication date without a time is a calendar date, not a known instant.
    if isinstance(value, str):
        try:
            date.fromisoformat(value.strip())
        except ValueError:
            pass
        else:
            return value
        if len(value.strip()) == 10:  # noqa: PLR2004 - legacy DD.MM.YYYY calendar date
            return value
    try:
        return format_datetime(parse_datetime(value, default_timezone=default_timezone))
    except ValueError:
        return value
