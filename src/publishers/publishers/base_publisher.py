"""Base abstract type for all publishers."""

from shared.schema.publisher import PublisherSchema
from managers.log_manager import logger


class BasePublisher:
    """Base abstract type for all publishers.

    Attributes:
        type (str): The type of the publisher.
        name (str): The name of the publisher.
        description (str): The description of the publisher.
        parameters (list): The list of parameters for the publisher.
    Methods:
        get_info(): Returns the information schema of the publisher.
        print_exception(error): Prints the exception with debug trace.
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

    def print_exception(self, error):
        """Print the given error message with the name of the publisher.

        Parameters:
            error (str): The error message to be printed.
        """
        logger.exception(f"[{self.name}] {error}")
