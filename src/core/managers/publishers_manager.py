"""Manager for publishers.

Returns:
    _type_: _description_
"""

from http import HTTPStatus

from model.publisher import Publisher
from model.publisher_preset import PublisherPreset
from model.publishers_node import PublishersNode
from remote.publishers_api import PublishersApi

from shared.schema.publisher import PublisherInput, PublisherInputSchema
from shared.schema.publishers_node import PublishersNode as PublishersNodeSchema


def add_publishers_node(data: dict) -> HTTPStatus:
    """Add publishers node.

    Args:
        data (dict): json

    Returns:
        int: HTTP status code
    """
    node = PublishersNodeSchema.create(data)
    publishers_info, status_code = PublishersApi(node.api_url, node.api_key).get_publishers_info()
    if status_code == HTTPStatus.OK:
        publishers = Publisher.create_all(publishers_info)
        PublishersNode.add_new(data, publishers)

    return status_code


def update_publishers_node(node_id: int, data: dict) -> HTTPStatus:
    """Update publishers node.

    Args:
        node_id (int): The ID of the node to update.
        data (dict): json

    Returns:
        int: HTTP status code
    """
    node = PublishersNodeSchema.create(data)
    publishers_info, status_code = PublishersApi(node.api_url, node.api_key).get_publishers_info()
    if status_code == HTTPStatus.OK:
        publishers = Publisher.create_all(publishers_info)
        PublishersNode.update(node_id, data, publishers)

    return status_code


def add_publisher_preset(data: dict) -> None:
    """Add publisher preset.

    Args:
        data (dict): json
    """
    PublisherPreset.add_new(data)


def publish(preset: PublisherPreset, data: dict, message_title: str, message_body: str, recipients: list) -> tuple[dict, HTTPStatus]:
    """Publish.

    Args:
        preset (PublisherPreset): The publisher preset to use.
        data (dict): The data to publish.
        message_title (str): The title of the message.
        message_body (str): The body of the message.
        recipients (list): The list of recipients.

    Returns:
        Response: The response from the publishing API.
    """
    publisher = preset.publisher
    node = publisher.node
    data_data = None
    data_mime = None
    att_file_name = None
    if data is not None:
        data_data = data["data"]
        data_mime = data["mime_type"]
        message_title = data.get("message_title")
        message_body = data.get("message_body")
        att_file_name = data.get("att_file_name")

    input_data = PublisherInput(
        preset.name,
        publisher.type,
        preset.parameter_values,
        data_mime,
        data_data,
        message_title,
        message_body,
        recipients,
        att_file_name,
    )
    input_schema = PublisherInputSchema()

    return PublishersApi(node.api_url, node.api_key).publish(input_schema.dump(input_data))
