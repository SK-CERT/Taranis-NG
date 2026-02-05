"""This module contains the bot manager."""

from model.bot import Bot
from model.bot_preset import BotPreset
from model.bots_node import BotsNode
from remote.bots_api import BotsApi

from shared.schema.bots_node import BotsNode as BotsNodeSchema


def add_bots_node(data):
    """Add a new bots node.

    Parameters:
        data (dict): The data for creating the bots node.

    Returns:
        int: The status code of the operation.
    """
    node = BotsNodeSchema.create(data)
    bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info()
    if status_code == 200:
        bots = Bot.create_all(bots_info)
        BotsNode.add_new(data, bots)

    return status_code


def update_bots_node(node_id, data):
    """Update an existing bots node.

    Parameters:
        node_id (int): The ID of the bots node to update.
        data (dict): The data for updating the bots node.

    Returns:
        int: The status code of the operation.
    """
    node = BotsNodeSchema.create(data)
    bots_info, status_code = BotsApi(node.api_url, node.api_key).get_bots_info()
    if status_code == 200:
        bots = Bot.create_all(bots_info)
        BotsNode.update(node_id, data, bots)

    return status_code


def add_bot_preset(data):
    """Add a new bot preset.

    Parameters:
        data (dict): The data for creating the bot preset.
    """
    BotPreset.add_new(data)
