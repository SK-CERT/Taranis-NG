"""This module provides functionality for managing publishers in Taranis-NG."""

from http import HTTPStatus

from publishers.email_publisher import EMAILPublisher
from publishers.ftp_publisher import FTPPublisher
from publishers.mastodon_publisher import MASTODONPublisher
from publishers.misp_publisher import MISPPublisher
from publishers.sftp_publisher import SFTPPublisher
from publishers.twitter_publisher import TWITTERPublisher
from publishers.wordpress_publisher import WORDPRESSPublisher
from shared.schema.publisher import PublisherInputSchema

publishers = {}


def initialize() -> None:
    """Initialize the publishers by registering them."""
    register_publisher(FTPPublisher())
    register_publisher(SFTPPublisher())
    register_publisher(EMAILPublisher())
    register_publisher(MASTODONPublisher())
    register_publisher(TWITTERPublisher())
    register_publisher(WORDPRESSPublisher())
    register_publisher(MISPPublisher())


def register_publisher(publisher) -> None:  # noqa: ANN001
    """Register a publisher.

    Arguments:
        publisher: The publisher object to register.
    """
    publishers[publisher.type] = publisher


def get_registered_publishers_info() -> list[dict]:
    """Retrieve information about the registered publishers.

    Returns:
       (list): A list of dictionaries containing information about each registered publisher.
    """
    return [pub.get_info() for pub in publishers.values()]


def publish(publisher_input_json: dict) -> tuple[dict, HTTPStatus]:
    """Publish the given input using the appropriate publisher.

    Arguments:
        publisher_input_json: The JSON input for the publisher.

    Raises:
        ValidationError: If the input JSON is invalid.
    """
    publisher_input_schema = PublisherInputSchema()
    publisher_input = publisher_input_schema.load(publisher_input_json)
    return publishers[publisher_input.type].publish(publisher_input)
