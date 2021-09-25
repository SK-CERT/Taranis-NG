from flask_restful import Resource
from flask import request
from managers.auth_manager import auth_required
from managers import auth_manager
from model import asset, notification_template
from model.permission import Permission
from model import attribute
from taranisng.schema.attribute import AttributeType


class AddAssetGroup(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def post(self):
        return '', asset.AssetGroup.add(auth_manager.get_user_from_jwt(), request.json)


class AssetGroups(Resource):

    @auth_required('MY_ASSETS_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return asset.AssetGroup.get_all_json(auth_manager.get_user_from_jwt(), search)


class AssetGroup(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def put(self, id):
        asset.AssetGroup.update(auth_manager.get_user_from_jwt(), id, request.json)

    @auth_required('MY_ASSETS_CONFIG')
    def delete(self, id):
        return asset.AssetGroup.delete(auth_manager.get_user_from_jwt(), id)


class AddNotificationTemplate(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def post(self):
        return '', notification_template.NotificationTemplate.add(auth_manager.get_user_from_jwt(), request.json)


class NotificationTemplates(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return notification_template.NotificationTemplate.get_all_json(auth_manager.get_user_from_jwt(), search)


class NotificationTemplate(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def put(self, id):
        notification_template.NotificationTemplate.update(auth_manager.get_user_from_jwt(), id, request.json)

    @auth_required('MY_ASSETS_CONFIG')
    def delete(self, id):
        return notification_template.NotificationTemplate.delete(auth_manager.get_user_from_jwt(), id)


class AddAsset(Resource):

    @auth_required('MY_ASSETS_CREATE')
    def post(self):
        return '', asset.Asset.add(auth_manager.get_user_from_jwt(), request.json)


class Assets(Resource):

    @auth_required('MY_ASSETS_ACCESS')
    def get(self, id):
        search = None
        sort = None
        vulnerable = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        if 'sort' in request.args and request.args['sort']:
            sort = request.args['sort']
        if 'vulnerable' in request.args and request.args['vulnerable']:
            vulnerable = request.args['vulnerable']
        return asset.Asset.get_all_json(auth_manager.get_user_from_jwt(), id, search, sort, vulnerable)


class Asset(Resource):

    @auth_required('MY_ASSETS_CREATE')
    def put(self, id):
        asset.Asset.update(auth_manager.get_user_from_jwt(), id, request.json)

    @auth_required('MY_ASSETS_CREATE')
    def delete(self, id):
        return asset.Asset.delete(auth_manager.get_user_from_jwt(), id)


class AssetVulnerability(Resource):

    @auth_required('MY_ASSETS_CREATE')
    def post(self):
        return asset.Asset.solve_vulnerability(auth_manager.get_user_from_jwt(), request.json['asset_id'],
                                               request.json['report_item_id'], request.json['solved'])


class GetAttributeCPE(Resource):

    @auth_required('MY_ASSETS_CREATE')
    def get(self):
        cpe = attribute.Attribute.find_by_type(AttributeType.CPE)
        return cpe.id


class AttributeCPEEnums(Resource):

    @auth_required('MY_ASSETS_CREATE')
    def get(self):
        cpe = attribute.Attribute.find_by_type(AttributeType.CPE)
        search = None
        offset = 0
        limit = 10
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        if 'offset' in request.args and request.args['offset']:
            offset = request.args['offset']
        if 'limit' in request.args and request.args['limit']:
            limit = request.args['limit']
        return attribute.AttributeEnum.get_for_attribute_json(cpe.id, search, offset, limit)


def initialize(api):
    api.add_resource(AssetGroups, "/api/assets/groups")
    api.add_resource(AddAssetGroup, "/api/assets/group/add")
    api.add_resource(AssetGroup, "/api/assets/group/<id>")

    api.add_resource(NotificationTemplates, "/api/assets/templates")
    api.add_resource(AddNotificationTemplate, "/api/assets/template/add")
    api.add_resource(NotificationTemplate, "/api/assets/template/<id>")

    api.add_resource(Assets, "/api/assets/<id>")
    api.add_resource(AddAsset, "/api/asset/add")
    api.add_resource(Asset, "/api/asset/<id>")

    api.add_resource(AssetVulnerability, "/api/asset/vulnerability")

    api.add_resource(GetAttributeCPE, "/api/assets/attribute/cpe")
    api.add_resource(AttributeCPEEnums, "/api/assets/attribute/cpe/enums")

    Permission.add("MY_ASSETS_ACCESS", "My Assets access", "Access to My Assets module")
    Permission.add("MY_ASSETS_CREATE", "My Assets create", "Creation of products in My Assets module")
    Permission.add("MY_ASSETS_CONFIG", "My Assets config", "Configuration of access and groups in My Assets module")
