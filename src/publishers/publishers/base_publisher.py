"""Base abstract type for all publishers."""

from typing import ClassVar

from shared.schema.publisher import PublisherSchema


class BasePublisher:
    """Base abstract type for all publishers.

    Attributes:
        publisher_type (str): The type of the publisher.
        name (str): The name of the publisher.
        description (str): The description of the publisher.
        parameters (list): The list of parameters for the publisher.

    Methods:
        get_info(): Returns the information schema of the publisher.
    """

    publisher_type = "BASE_PUBLISHER"
    name = "Base Publisher"
    description = "Base abstract type for all publishers"
    parameters: ClassVar[list] = []

    @property
    def type(self) -> str:
        """Alias for ``publisher_type``.

        ``PublisherSchema`` serializes a field named ``type``, but each concrete
        publisher declares its kind as the class attribute ``publisher_type``.
        Without this alias Marshmallow's ``dump`` omits ``type`` from the output,
        which in turn makes core's ``Publisher(**data)`` fail with
        ``__init__() missing 1 required positional argument: 'type'`` when a
        publishers node is created.
        """
        return self.publisher_type

    def get_info(self) -> dict:
        """Return the information of the publisher.

        Returns:
            (dict): The information of the publisher.
        """
        info_schema = PublisherSchema()
        return info_schema.dump(self)
