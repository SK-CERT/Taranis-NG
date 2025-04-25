"""Base abstract type for all publishers."""

from shared.schema.publisher import PublisherSchema


class BasePublisher:
    """Base abstract type for all publishers.

    Attributes:
        type (str): The type of the publisher.
        name (str): The name of the publisher.
        description (str): The description of the publisher.
        parameters (list): The list of parameters for the publisher.
    Methods:
        get_info(): Returns the information schema of the publisher.
    """

    type = "BASE_PUBLISHER"
    name = "Base Publisher"
    description = "Base abstract type for all publishers"
    parameters = []

    def get_info(self):
        """Return the information of the publisher.

        Returns:
            (dict): The information of the publisher.
        """
        info_schema = PublisherSchema()
        return info_schema.dump(self)
