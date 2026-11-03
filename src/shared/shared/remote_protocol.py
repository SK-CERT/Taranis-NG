"""Versioned remote timestamp contracts and the legacy timezone boundary."""

import copy
import os
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from marshmallow import ValidationError

from shared.datetime_utils import format_datetime, parse_datetime


def validate_legacy_timezone(value: str) -> None:
    """Require an explicit, valid IANA timezone for legacy peer wall clocks."""
    try:
        ZoneInfo(value)
    except (ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        message = "Use a valid IANA timezone, for example Europe/Bratislava or UTC."
        raise ValidationError(message) from exc


def default_legacy_timezone() -> str:
    """Use the preserved installation timezone for new legacy peer configurations."""
    value = os.environ.get("TARANIS_NG_LEGACY_TZ") or os.environ.get("TZ") or "UTC"
    validate_legacy_timezone(value)
    return value


def parse_remote_timestamp(value: str | datetime, *, version: int = 2, legacy_timezone: str = "UTC") -> datetime:
    """Read v1 wall clocks in the peer's timezone, or require an offset for v2."""
    if version not in (1, 2):
        message = "Unsupported remote API version."
        raise ValidationError(message)
    try:
        if version == 1:
            return parse_datetime(value, default_timezone=ZoneInfo(legacy_timezone))
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    except (ValueError, TypeError, ZoneInfoNotFoundError) as exc:
        raise ValidationError({"timestamp": [str(exc)]}) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        message = "Remote API v2 timestamps must include a timezone offset."
        raise ValidationError({"timestamp": [message]})
    return parsed.astimezone(UTC)


def format_remote_timestamp(
    value: str | datetime | None,
    *,
    version: int = 2,
    legacy_timezone: str = "UTC",
    cursor: bool = False,
) -> str | None:
    """Write UTC in v2 and the original timezone-free formats in v1."""
    if value is None:
        return None
    instant = parse_datetime(value)
    if version == 2:  # noqa: PLR2004 - the public protocol version
        return format_datetime(instant)
    if version != 1:
        message = "Unsupported remote API version."
        raise ValidationError(message)
    local = instant.astimezone(ZoneInfo(legacy_timezone))
    return local.strftime("%Y-%m-%d %H:%M:%S.%f" if cursor else "%d.%m.%Y - %H:%M")


def _aware_publication(value: str | None) -> datetime | None:
    """Only explicit offsets establish the instant of otherwise free-form source text."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def normalize_remote_publication(value: str | None) -> str | None:
    """Keep ambiguous legacy publications opaque; normalize known offset-bearing instants."""
    parsed = _aware_publication(value)
    return format_datetime(parsed) if parsed is not None else value


def legacy_news_items(items: list[dict], legacy_timezone: str) -> list[dict]:
    """Adapt only timestamp metadata, never arbitrary news attributes or content."""
    result = copy.deepcopy(items)
    for item in result:
        if item.get("collected") is not None:
            item["collected"] = format_remote_timestamp(item["collected"], version=1, legacy_timezone=legacy_timezone)
        published = _aware_publication(item.get("published"))
        if published is not None:
            item["published"] = format_remote_timestamp(published, version=1, legacy_timezone=legacy_timezone)
    return result


def normalize_legacy_news_items(items: list[dict], legacy_timezone: str) -> list[dict]:
    """Read a legacy provider's collected times without inventing publication offsets."""
    result = copy.deepcopy(items)
    for item in result:
        if item.get("collected") is not None:
            item["collected"] = format_datetime(parse_remote_timestamp(item["collected"], version=1, legacy_timezone=legacy_timezone))
        if "published" in item:
            item["published"] = normalize_remote_publication(item["published"])
    return result


def validate_remote_news_items(items: list[dict]) -> list[dict]:
    """Validate typed v2 timestamps; published remains source-supplied text."""
    for item in items:
        if item.get("collected") is not None:
            parse_remote_timestamp(item["collected"], version=2)
    return items
