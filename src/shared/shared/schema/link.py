"""Link reference schema."""

from marshmallow import EXCLUDE, Schema, fields


class LinkRefSchema(Schema):
    """A link that text can cite by its stable key.

    Attributes:
        key: The stable key that citation tokens (``[#key]``) refer to.
        url: The link itself.
    """

    class Meta:
        """Meta class."""

        unknown = EXCLUDE

    key = fields.Str(load_default=None, allow_none=True)
    url = fields.Str(load_default="")
