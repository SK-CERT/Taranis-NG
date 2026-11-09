"""Schemas for how records are presented in lists: card texts, and keys the GUI never receives."""

from marshmallow import Schema, fields


class HiddenApiKeySchema(Schema):
    """For a record holding an API key: whether one is stored (``api_key_set``), never the key.

    Put it before the record's schema in the bases, so its ``api_key`` wins. The GUI saves an
    empty key to keep the stored one (core managers/stored_secrets.py).
    """

    api_key = fields.Constant("", dump_only=True)
    api_key_set = fields.Method("_api_key_set", dump_only=True)

    def _api_key_set(self, obj: object) -> bool:
        return bool(getattr(obj, "api_key", None))


class PresentationSchema(Schema):
    """The texts a list shows for a record: title, subtitle and tag."""

    title = fields.Str()
    subtitle = fields.Str()
    tag = fields.Str()
