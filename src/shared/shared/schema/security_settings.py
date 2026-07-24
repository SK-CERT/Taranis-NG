"""This module defines the schema for site-wide security settings."""

from marshmallow import EXCLUDE, Schema, fields


class SecuritySettingsSchema(Schema):
    """Marshmallow schema for the site-wide security settings.

    Currently holds the WebAuthn relying-party configuration that passkey
    sign-in needs. This is not an identity provider: passkeys are credentials
    owned by users, these fields only describe *this* site to the authenticator.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    passkey_enabled = fields.Bool(load_default=False)
    passkey_second_factor = fields.Bool(load_default=True)
    require_mfa = fields.Bool(load_default=False)
    rp_id = fields.Str(load_default="", allow_none=True)
    rp_name = fields.Str(load_default="", allow_none=True)
    origins = fields.Str(load_default="", allow_none=True)
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)
