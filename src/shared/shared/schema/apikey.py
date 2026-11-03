from marshmallow import EXCLUDE, Schema, fields, post_load

from shared.schema.datetime import UTCDateTime
from shared.schema.user import UserSchemaBase


class ApiKeyBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    key = fields.Str()  # length 40
    created_at = UTCDateTime(load_default=None, allow_none=True)
    user_id = fields.Int(load_default=None, allow_none=True)
    expires_at = UTCDateTime(load_default=None, allow_none=True)


class ApiKeySchema(ApiKeyBaseSchema):
    user = fields.Nested(UserSchemaBase, exclude=("password",))

    @post_load
    def make(self, data, **kwargs):
        return ApiKey(**data)


class ApiKey:
    def __init__(
        self,
        # id,
        name,
        key,
        created_at,
        user_id,
        expires_at,
    ):
        self.id = id
        self.name = name
        self.key = key
        # created_at - database take care about it
        self.user_id = user_id
        self.expires_at = expires_at
