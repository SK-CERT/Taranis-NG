"""This module defines the schema for site-wide security settings."""

from marshmallow import EXCLUDE, Schema, fields


def _allowlist_lines(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value).splitlines() if line.strip()]


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
    passkey_first_factor = fields.Bool(load_default=True)
    passkey_second_factor = fields.Bool(load_default=True)
    require_mfa = fields.Bool(load_default=False)
    rp_id = fields.Str(load_default="", allow_none=True)
    rp_name = fields.Str(load_default="", allow_none=True)
    origins = fields.Str(load_default="", allow_none=True)
    # API key policy. No load default: a payload without them leaves the stored values alone.
    api_key_require_expiry = fields.Bool()
    api_key_max_days = fields.Int(allow_none=True)
    api_key_require_allowlist = fields.Bool()
    api_key_allowed_ips = fields.Method("dump_allowed_ips", deserialize="load_allowed_ips", allow_none=True)
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)

    def dump_allowed_ips(self, obj: object) -> list[str]:
        """Dump the site-wide allowlist as a list of networks."""
        stored = obj.get("api_key_allowed_ips") if isinstance(obj, dict) else getattr(obj, "api_key_allowed_ips", None)
        return _allowlist_lines(stored)

    def load_allowed_ips(self, value: object) -> list[str]:
        """Accept the site-wide allowlist as a list or as text; the model validates the entries."""
        return _allowlist_lines(value)
