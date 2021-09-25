from flask_restful import Resource, reqparse
from flask import request
from managers import bots_manager
from managers.auth_manager import auth_required, api_key_required
from model import bots_node
from model import bot_preset
from model.permission import Permission


class BotNodes(Resource):

    @auth_required('CONFIG_BOTS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return bots_node.BotsNode.get_all_json(search)


class BotsNode(Resource):

    @auth_required('CONFIG_BOTS_NODE_UPDATE')
    def put(self, id):
        bots_manager.update_bots_node(id, request.json)

    @auth_required('CONFIG_BOTS_NODE_DELETE')
    def delete(self, id):
        return bots_node.BotsNode.delete(id)


class AddBotsNode(Resource):

    @auth_required('CONFIG_BOTS_NODE_CREATE')
    def post(self):
        return '', bots_manager.add_bots_node(request.json)


class BotPresets(Resource):

    @auth_required('CONFIG_BOT_PRESET_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return bot_preset.BotPreset.get_all_json(search)

    @api_key_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("bot_type")
        parameters = parser.parse_args()
        return bot_preset.BotPreset.get_all_for_bot_json(parameters)


class AddBotPreset(Resource):

    @auth_required('CONFIG_BOT_PRESET_CREATE')
    def post(self):
        bots_manager.add_bot_preset(request.json)


class BotPreset(Resource):

    @auth_required('CONFIG_BOT_PRESET_UPDATE')
    def put(self, id):
        bot_preset.BotPreset.update(id, request.json)

    @auth_required('CONFIG_BOT_PRESET_DELETE')
    def delete(self, id):
        return bot_preset.BotPreset.delete(id)


def initialize(api):
    api.add_resource(BotNodes, "/api/bots/nodes")
    api.add_resource(AddBotsNode, "/api/bots/nodes/add")
    api.add_resource(BotsNode, "/api/bots/node/<id>")

    api.add_resource(BotPresets, "/api/bots/presets")
    api.add_resource(AddBotPreset, "/api/bots/presets/add")
    api.add_resource(BotPreset, "/api/bots/preset/<id>")

    Permission.add("CONFIG_BOTS_NODE_ACCESS", "Config bots nodes access", "Access to bots nodes configuration")
    Permission.add("CONFIG_BOTS_NODE_CREATE", "Config bots node create", "Create bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_UPDATE", "Config bots node update", "Update bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_DELETE", "Config bots node delete", "Delete bots node configuration")

    Permission.add("CONFIG_BOT_PRESET_ACCESS", "Config bot presets access", "Access to bot presets configuration")
    Permission.add("CONFIG_BOT_PRESET_CREATE", "Config bot preset create", "Create bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_UPDATE", "Config bot preset update", "Update bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_DELETE", "Config bot preset delete", "Delete bot preset configuration")
