"""
This module provides functionality for managing publishers in Taranis-NG.

The publishers manager is responsible for registering publishers, retrieving information about registered publishers,
and publishing data using the appropriate publisher based on the input.

The module defines the following functions:
- initialize(): Initializes the publishers by registering them.
- register_publisher(publisher): Registers a publisher.
- get_registered_publishers_info(): Retrieves information about the registered publishers.
- publish(publisher_input_json): Publishes the given input using the appropriate publisher.

The module also imports the following classes:
- FTPPublisher: Represents an FTP publisher.
- SFTPPublisher: Represents an SFTP publisher.
- EMAILPublisher: Represents an email publisher.
- TWITTERPublisher: Represents a Twitter publisher.
- WORDPRESSPublisher: Represents a WordPress publisher.
- MISPPublisher: Represents a MISP publisher.

The module imports the following modules:
- PublisherInputSchema: Provides a schema for validating the input JSON for publishers.
- log_manager: Provides functionality for logging critical messages.
"""

from publishers.ftp_publisher import FTPPublisher
from publishers.sftp_publisher import SFTPPublisher
from publishers.email_publisher import EMAILPublisher
from publishers.twitter_publisher import TWITTERPublisher
from publishers.wordpress_publisher import WORDPRESSPublisher
from publishers.misp_publisher import MISPPublisher
from shared.schema.publisher import PublisherInputSchema
from managers import log_manager

publishers = {}


def initialize():
    """Initialize the publishers by registering them."""
    register_publisher(FTPPublisher())
    register_publisher(SFTPPublisher())
    register_publisher(EMAILPublisher())
    register_publisher(TWITTERPublisher())
    register_publisher(WORDPRESSPublisher())
    register_publisher(MISPPublisher())


def register_publisher(publisher):
    """
    Register a publisher.

    Args:
        publisher: The publisher object to register.
    """
    publishers[publisher.type] = publisher


def get_registered_publishers_info():
    """
    Retrieve information about the registered publishers.

    Returns:
        A list of dictionaries containing information about each registered publisher.
    """
    publishers_info = []
    for key in publishers:
        publishers_info.append(publishers[key].get_info())
    log_manager.log_critical(publishers_info)

    return publishers_info


def publish(publisher_input_json):
    """
    Publish the given input using the appropriate publisher.

    Args:
        publisher_input_json: The JSON input for the publisher.

    Raises:
        ValidationError: If the input JSON is invalid.
    """
    publisher_input_schema = PublisherInputSchema()
    publisher_input = publisher_input_schema.load(publisher_input_json)
    publishers[publisher_input.type].publish(publisher_input)
