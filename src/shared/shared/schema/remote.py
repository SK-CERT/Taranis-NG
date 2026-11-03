"""Module for Remote Access schema."""

from marshmallow import EXCLUDE, Schema, fields

from shared.remote_protocol import default_legacy_timezone, validate_legacy_timezone
from shared.schema.datetime import UTCDateTime
from shared.schema.osint_source import OSINTSourcePresentationSchema
from shared.schema.presentation import PresentationSchema
from shared.schema.report_item_type import ReportItemTypePresentationSchema


class RemoteAccessSchema(Schema):
    """Schema for remote access details."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    api_key = fields.Str()
    enabled = fields.Bool()
    legacy_timezone = fields.Str(load_default=default_legacy_timezone, validate=validate_legacy_timezone)
    osint_sources = fields.List(fields.Nested(OSINTSourcePresentationSchema))
    report_item_types = fields.List(fields.Nested(ReportItemTypePresentationSchema))


class RemoteAccessPresentationSchema(RemoteAccessSchema, PresentationSchema):
    """Schema for presenting remote access details."""

    last_synced = UTCDateTime()


class RemoteNodeSchema(Schema):
    """Schema for remote node details."""

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    remote_url = fields.Str()
    events_url = fields.Str()
    api_key = fields.Str()
    enabled = fields.Bool()
    legacy_timezone = fields.Str(load_default=default_legacy_timezone, validate=validate_legacy_timezone)
    sync_news_items = fields.Bool()
    sync_report_items = fields.Bool()
    osint_source_group_id = fields.Str(load_default=None, allow_none=True)


class RemoteNodePresentationSchema(RemoteNodeSchema, PresentationSchema):
    """Schema for presenting remote node details."""

    last_synced = UTCDateTime()
    event_id = fields.Str()
