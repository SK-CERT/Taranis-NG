from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.user import UserSchemaBase
from shared.schema.presentation import PresentationSchema


class ApiKeyBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    key = fields.Str() # length 40
    created_at = fields.DateTime("%d.%m.%Y - %H:%M", load_default=None)
    user_id = fields.Int(load_default=None)
    expires_at = fields.DateTime("%d.%m.%Y - %H:%M", load_default=None)


class ApiKeySchema(ApiKeyBaseSchema):
    user = fields.Nested(UserSchemaBase)

    @post_load
    def make(self, data, **kwargs):
        return ApiKey(**data)


class ApiKey:
    def __init__(
        self,
        #id,
        name,
        key,
        created_at,
        user_id,
        #user, ????
        expires_at
    ):
        self.id = id
        self.name = name
        self.key = key
        # created_at - database take care about it
        self.user_id = user_id
        # self.user = user
        self.expires_at = expires_at
