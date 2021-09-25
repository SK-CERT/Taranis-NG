from flask_restful import Resource, reqparse
from flask import request
from managers import collectors_manager
from managers.auth_manager import auth_required, api_key_required
from model import collectors_node
from model import osint_source
from managers import auth_manager
from model.permission import Permission


class CollectorsNodes(Resource):

    @auth_required('CONFIG_COLLECTORS_NODE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return collectors_node.CollectorsNode.get_all_json(search)


class AddCollectorsNode(Resource):

    @auth_required('CONFIG_COLLECTORS_NODE_CREATE')
    def post(self):
        return '', collectors_manager.add_collectors_node(request.json)


class CollectorsNode(Resource):

    @auth_required('CONFIG_COLLECTORS_NODE_UPDATE')
    def put(self, id):
        collectors_manager.update_collectors_node(id, request.json)

    @auth_required('CONFIG_COLLECTORS_NODE_DELETE')
    def delete(self, id):
        collectors_node.CollectorsNode.delete(id)


class OSINTSources(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return osint_source.OSINTSource.get_all_json(search)

    @api_key_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("api_key")
        parser.add_argument("collector_type")
        parameters = parser.parse_args()
        return osint_source.OSINTSource.get_all_for_collector_json(parameters)


class ManualOSINTSources(Resource):

    @auth_required(['ASSESS_ACCESS'])
    def get(self):
        return osint_source.OSINTSource.get_all_manual_json(auth_manager.get_user_from_jwt())


class AddOSINTSource(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_CREATE')
    def post(self):
        collectors_manager.add_osint_source(request.json)


class OSINTSource(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_UPDATE')
    def put(self, id):
        osint_source.OSINTSource.update(id, request.json)

    @auth_required('CONFIG_OSINT_SOURCE_DELETE')
    def delete(self, id):
        osint_source.OSINTSource.delete(id)


class OSINTSourceGroups(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return osint_source.OSINTSourceGroup.get_all_json(search, auth_manager.get_user_from_jwt(), False)


class AddOSINTSourceGroup(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_CREATE')
    def post(self):
        osint_source.OSINTSourceGroup.add(request.json)


class OSINTSourceGroup(Resource):

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_UPDATE')
    def put(self, id):
        osint_source.OSINTSourceGroup.update(id, request.json)

    @auth_required('CONFIG_OSINT_SOURCE_GROUP_DELETE')
    def delete(self, id):
        osint_source.OSINTSourceGroup.delete(id)


def initialize(api):
    api.add_resource(CollectorsNodes, "/api/collectors/nodes")
    api.add_resource(AddCollectorsNode, "/api/collectors/nodes/add")
    api.add_resource(CollectorsNode, "/api/collectors/node/<id>")
    api.add_resource(OSINTSources, "/api/collectors/sources")
    api.add_resource(OSINTSource, "/api/collectors/source/<id>")
    api.add_resource(ManualOSINTSources, "/api/collectors/sources/manual")
    api.add_resource(AddOSINTSource, "/api/collectors/sources/add")
    api.add_resource(OSINTSourceGroups, "/api/collectors/sources/groups")
    api.add_resource(AddOSINTSourceGroup, "/api/collectors/sources/groups/add")
    api.add_resource(OSINTSourceGroup, "/api/collectors/sources/group/<id>")

    Permission.add("CONFIG_COLLECTORS_NODE_ACCESS", "Config collectors nodes access",
                   "Access to collectors nodes configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_CREATE", "Config collectors node create",
                   "Create collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_UPDATE", "Config collectors node update",
                   "Update collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_DELETE", "Config collectors node delete",
                   "Delete collectors node configuration")

    Permission.add("CONFIG_OSINT_SOURCE_ACCESS", "Config OSINT source access", "Access to OSINT sources configuration")
    Permission.add("CONFIG_OSINT_SOURCE_CREATE", "Config OSINT source create", "Create OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_UPDATE", "Config OSINT source update", "Update OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_DELETE", "Config OSINT source delete", "Delete OSINT source configuration")

    Permission.add("CONFIG_OSINT_SOURCE_GROUP_ACCESS", "Config OSINT source group access",
                   "Access to OSINT sources groups configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_CREATE", "Config OSINT source group create",
                   "Create OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_UPDATE", "Config OSINT source group update",
                   "Update OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_DELETE", "Config OSINT source group delete",
                   "Delete OSINT source group configuration")
