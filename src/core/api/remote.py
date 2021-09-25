from flask_restful import Resource
from flask import request
from model import remote
from model.permission import Permission
from managers.auth_manager import auth_required, access_key_required
from managers import auth_manager, remote_manager, sse_manager
from model import news_item
from model import report_item


class RemoteAccesses(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return remote.RemoteAccess.get_all_json(search)


class RemoteAccessNew(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_CREATE')
    def post(self):
        remote.RemoteAccess.add(request.json)


class RemoteAccess(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_UPDATE')
    def put(self, id):
        event_id, disconnect = remote.RemoteAccess.update(id, request.json)
        if disconnect:
            sse_manager.remote_access_disconnect([event_id])

        @auth_required('CONFIG_REMOTE_ACCESS_DELETE')
        def delete(self, id):
            return remote.RemoteAccess.delete(id)


class RemoteNodes(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return remote.RemoteNode.get_all_json(search)


class RemoteNodeNew(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_CREATE')
    def post(self):
        remote.RemoteNode.add(request.json)


class RemoteNode(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_UPDATE')
    def put(self, id):
        if remote.RemoteNode.update(id, request.json) is False:
            remote_manager.disconnect_from_node(id)

    @auth_required('CONFIG_REMOTE_ACCESS_DELETE')
    def delete(self, id):
        remote_manager.disconnect_from_node(id)
        return remote.RemoteNode.delete(id)


class RemoteNodeConnect(Resource):

    @auth_required('CONFIG_REMOTE_ACCESS_ACCESS')
    def get(self, id):
        return remote_manager.connect_to_node(id)


class RemoteConnect(Resource):

    @access_key_required
    def get(self):
        return remote.RemoteAccess.connect(auth_manager.get_access_key())


class RemoteDisconnect(Resource):

    @access_key_required
    def get(self):
        return remote.RemoteAccess.disconnect(auth_manager.get_access_key())


class RemoteSyncNewsItems(Resource):

    @access_key_required
    def get(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        news_items, last_sync_time = news_item.NewsItemData.get_for_sync(remote_access.last_synced_news_items,
                                                                         remote_access.osint_sources)
        return {'last_sync_time': format(last_sync_time), 'news_items': news_items}

    @access_key_required
    def put(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        remote_access.update_news_items_sync(request.json)


class RemoteSyncReportItems(Resource):

    @access_key_required
    def get(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        report_items, last_sync_time = report_item.ReportItem.get_for_sync(remote_access.last_synced_report_items,
                                                                           remote_access.report_item_types)
        return {'last_sync_time': format(last_sync_time), 'report_items': report_items}

    @access_key_required
    def put(self):
        remote_access = remote.RemoteAccess.find_by_access_key(auth_manager.get_access_key())
        remote_access.update_report_items_sync(request.json)


def initialize(api):
    api.add_resource(RemoteAccesses, "/api/config/remote/accesses")
    api.add_resource(RemoteAccessNew, "/api/config/remote/access/new")
    api.add_resource(RemoteAccess, "/api/config/remote/access/<id>")

    api.add_resource(RemoteNodes, "/api/config/remote/nodes")
    api.add_resource(RemoteNodeNew, "/api/config/remote/node/new")
    api.add_resource(RemoteNode, "/api/config/remote/node/<id>")
    api.add_resource(RemoteNodeConnect, "/api/config/remote/node/connect/<id>")

    api.add_resource(RemoteConnect, "/api/remote/connect")
    api.add_resource(RemoteDisconnect, "/api/remote/disconnect")
    api.add_resource(RemoteSyncNewsItems, "/api/remote/sync/newsitems")
    api.add_resource(RemoteSyncReportItems, "/api/remote/sync/reportitems")

    Permission.add("CONFIG_REMOTE_ACCESS_ACCESS", "Config remote access access",
                   "Access to remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_CREATE", "Config remote access create", "Create remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_UPDATE", "Config remote access update", "Update remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_DELETE", "Config remote access delete", "Delete remote access configuration")

    Permission.add("CONFIG_REMOTE_NODE_ACCESS", "Config remote nodes access",
                   "Access to remote nodes configuration")
    Permission.add("CONFIG_REMOTE_NODE_CREATE", "Config remote node create", "Create remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_UPDATE", "Config remote node update", "Update remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_DELETE", "Config remote node delete", "Delete remote node configuration")
