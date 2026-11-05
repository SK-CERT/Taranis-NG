"""Marshmallow fields implementing the shared UTC wire contract."""

from datetime import datetime
from typing import Any

from marshmallow import fields

from shared.datetime_utils import format_datetime, normalize_timestamp, parse_datetime
from shared.remote_protocol import normalize_remote_publication


class UTCDateTime(fields.DateTime):
    """Emit ISO UTC timestamps and accept ISO and legacy inputs during transition."""

    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> str | None:  # noqa: ANN401, ARG002
        return format_datetime(value)

    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> datetime:  # noqa: ANN401, ARG002
        try:
            return parse_datetime(value)
        except (TypeError, ValueError) as exc:
            error_key = "invalid"
            raise self.make_error(error_key, input=value, obj_type="datetime") from exc


class PublicationTimestamp(fields.String):
    """Preserve free-form source dates, normalizing recognized instants to UTC."""

    def _serialize(self, value: Any, attr: str | None, obj: Any, **kwargs: Any) -> str | None:  # noqa: ANN401, ARG002
        return normalize_remote_publication(value)

    def _deserialize(self, value: Any, attr: str | None, data: Any, **kwargs: Any) -> str:  # noqa: ANN401
        return normalize_timestamp(super()._deserialize(value, attr, data, **kwargs))
