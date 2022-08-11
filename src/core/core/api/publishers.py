from flask_restful import Resource, reqparse
from flask import request

from core.managers import publishers_manager
from core.managers.auth_manager import auth_required, api_key_required
from core.model import publishers_node, publisher_preset


class AddPublishersNode(Resource):
    @auth_required("CONFIG_PUBLISHERS_NODE_CREATE")
    def post(self):
        return "", publishers_manager.add_publishers_node(request.json)


class PublisherPresets(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return publisher_preset.PublisherPreset.get_all_json(search)

    @api_key_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("collector_type")
        parameters = parser.parse_args()
        return publisher_preset.PublisherPreset.get_all_for_publisher_json(parameters)


class AddPublisherPreset(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self):
        publishers_manager.add_publisher_preset(request.json)


class PublisherPreset(Resource):
    @auth_required("CONFIG_PUBLISHER_PRESET_UPDATE")
    def put(self, id):
        publisher_preset.PublisherPreset.update(id, request.json)

    @auth_required("CONFIG_PUBLISHER_PRESET_DELETE")
    def delete(self, id):
        return publisher_preset.PublisherPreset.delete(id)


class PublisherNodes(Resource):
    @auth_required("CONFIG_PUBLISHERS_NODE_ACCESS")
    def get(self):
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return publishers_node.PublishersNode.get_all_json(search)


class PublishersNode(Resource):
    @auth_required("CONFIG_PUBLISHERS_NODE_UPDATE")
    def put(self, id):
        publishers_manager.update_publishers_node(id, request.json)

    @auth_required("CONFIG_PUBLISHERS_NODE_DELETE")
    def delete(self, id):
        return publishers_node.PublishersNode.delete(id)


def initialize(api):
    api.add_resource(PublisherNodes, "/api/publishers/nodes")
    api.add_resource(AddPublishersNode, "/api/publishers/nodes/add")
    api.add_resource(PublishersNode, "/api/publishers/node/<id>")

    api.add_resource(PublisherPresets, "/api/publishers/presets")
    api.add_resource(AddPublisherPreset, "/api/publishers/presets/add")
    api.add_resource(PublisherPreset, "/api/publishers/preset/<id>")
