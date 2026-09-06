"""Schema for a single custom mail header."""

from marshmallow import EXCLUDE, Schema, fields


class MessageHeaderSchema(Schema):
    """Schema for one ``{name, value}`` mail header pair.

    Deliberately has no ``@post_load``: nested this way it loads to a plain dict, which is
    what the email publisher wants, and it stays usable from both the presenter output and
    the publisher input schemas without either owning a class the other has to import.

    Header names and values crossing this schema have already been validated by
    ``shared.mail_headers``; the publisher re-validates rather than trusting the wire.
    """

    class Meta:
        """Meta class to define schema behavior."""

        unknown = EXCLUDE

    name = fields.Str()
    value = fields.Str()
