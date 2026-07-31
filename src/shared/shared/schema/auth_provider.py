"""This module defines the schema for authentication (identity) providers."""

from marshmallow import EXCLUDE, Schema, fields

from shared.schema.organization import OrganizationSchema
from shared.schema.role import RoleSchema

AUTH_PROVIDER_KINDS = ["local", "oidc", "oauth2", "saml", "ldap"]
PROVISIONING_MODES = ["manual", "approval", "automatic"]


class AuthProviderSchema(Schema):
    """Marshmallow schema for serializing and deserializing authentication providers.

    The stored secret (OIDC/OAuth2 client secret, LDAP bind password) is write-only:
    it is accepted on load but never dumped; `has_secret` tells the GUI whether one
    is stored.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    slug = fields.Str(load_default=None, allow_none=True)
    kind = fields.Str(validate=lambda k: k in AUTH_PROVIDER_KINDS)
    enabled = fields.Bool()
    organization = fields.Nested(OrganizationSchema, allow_none=True)
    default_roles = fields.Nested(RoleSchema, many=True)
    provisioning_mode = fields.Str(validate=lambda m: m in PROVISIONING_MODES)
    allowed_domains = fields.Str(load_default="", allow_none=True)
    require_mfa = fields.Bool(load_default=False)
    config = fields.Dict(load_default=dict)
    secret = fields.Str(load_only=True, load_default=None, allow_none=True)
    has_secret = fields.Bool(dump_only=True)
    updated_by = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)


class AuthProviderLoginSchema(Schema):
    """Public schema for the login page: only what an anonymous client may see."""

    id = fields.Int()
    name = fields.Str()
    kind = fields.Str()
    form = fields.Bool()
    login_url = fields.Str(allow_none=True)
