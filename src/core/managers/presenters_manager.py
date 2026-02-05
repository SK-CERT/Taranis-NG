"""This module contains the pressenters manager."""

from http import HTTPStatus

from model.presenter import Presenter
from model.presenters_node import PresentersNode
from remote.presenters_api import PresentersApi

from shared.schema.presenters_node import PresentersNode as PresentersNodeSchema


def add_presenters_node(data: dict) -> HTTPStatus:
    """Add a new presenters node.

    Args:
        data: Mapping with presenters node configuration (e.g., api_url, api_key, name).

    Returns:
        HTTPStatus: status code returned by the remote presenters API.
    """
    node = PresentersNodeSchema.create(data)
    presenters_info, status_code = PresentersApi(node.api_url, node.api_key).get_presenters_info()
    if status_code == HTTPStatus.OK:
        presenters = Presenter.create_all(presenters_info)
        PresentersNode.add_new(data, presenters)

    return status_code


def update_presenters_node(node_id: str, data: dict) -> HTTPStatus:
    """Update an existing presenters node.

    Args:
        node_id: Identifier of the existing presenters node to update.
        data: Mapping with presenters node configuration (e.g., api_url, api_key, name).

    Returns:
        HTTPStatus: status code returned by the remote presenters API.
    """
    node = PresentersNodeSchema.create(data)
    presenters_info, status_code = PresentersApi(node.api_url, node.api_key).get_presenters_info()
    if status_code == HTTPStatus.OK:
        presenters = Presenter.create_all(presenters_info)
        PresentersNode.update(node_id, data, presenters)

    return status_code
