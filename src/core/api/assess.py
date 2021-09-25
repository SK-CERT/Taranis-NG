from flask_restful import Resource
from flask import request, send_file
from model import news_item
from managers.auth_manager import api_key_required, auth_required, ACLCheck
from managers import auth_manager, sse_manager, audit_manager
from managers.auth_manager import ACLCheck
from model import osint_source
from model.permission import Permission
import io


class OSINTSourceGroupsAssess(Resource):

    @auth_required('ASSESS_ACCESS')
    def get(self):
        return osint_source.OSINTSourceGroup.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class AddNewsItems(Resource):

    @api_key_required
    def post(self):
        osint_source_ids = news_item.NewsItemAggregate.add_news_items(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class AddNewsItem(Resource):

    @auth_required('ASSESS_CREATE')
    def post(self):
        osint_source_ids = news_item.NewsItemAggregate.add_news_item(request.json)
        sse_manager.news_items_updated()
        sse_manager.remote_access_news_items_updated(osint_source_ids)


class NewsItemsByGroup(Resource):

    @auth_required('ASSESS_ACCESS', ACLCheck.OSINT_SOURCE_GROUP_ACCESS)
    def post(self, id):
        user = auth_manager.get_user_from_jwt()
        return news_item.NewsItemAggregate.get_by_group_json(id, request.json['filter'], request.json['offset'],
                                                             request.json['limit'], user)


class NewsItem(Resource):

    @auth_required('ASSESS_ACCESS', ACLCheck.NEWS_ITEM_ACCESS)
    def get(self, id):
        return news_item.NewsItem.get_detail_json(id)

    @auth_required('ASSESS_UPDATE', ACLCheck.NEWS_ITEM_MODIFY)
    def put(self, id):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItem.update(id, request.json, user.id)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required('ASSESS_DELETE', ACLCheck.NEWS_ITEM_MODIFY)
    def delete(self, id):
        response, code = news_item.NewsItem.delete(id)
        sse_manager.news_items_updated()
        return response, code


class NewsItemAggregate(Resource):

    @auth_required('ASSESS_UPDATE')
    def put(self, id):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItemAggregate.update(id, request.json, user)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required('ASSESS_DELETE')
    def delete(self, id):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.delete(id, user)
        sse_manager.news_items_updated()
        return response, code


class GroupAction(Resource):

    @auth_required('ASSESS_UPDATE')
    def post(self):
        user = auth_manager.get_user_from_jwt()
        response, osint_source_ids, code = news_item.NewsItemAggregate.group_action(request.json, user)
        sse_manager.news_items_updated()
        if len(osint_source_ids) > 0:
            sse_manager.remote_access_news_items_updated(osint_source_ids)
        return response, code

    @auth_required('ASSESS_DELETE')
    def delete(self):
        user = auth_manager.get_user_from_jwt()
        response, code = news_item.NewsItemAggregate.group_action_delete(request.json, user)
        sse_manager.news_items_updated()
        return response, code


class DownloadAttachment(Resource):

    def get(self, id):
        if 'jwt' in request.args:
            user = auth_manager.decode_user_from_jwt(request.args['jwt'])
            if user is not None:
                permissions = user.get_permissions()
                if 'ASSESS_ACCESS' in permissions:
                    attribute_mapping = news_item.NewsItemDataNewsItemAttribute.find(id)
                    need_check = False
                    if attribute_mapping is not None:
                        need_check = True
                    attribute = news_item.NewsItemAttribute.find(id)
                    if need_check and news_item.NewsItemData.allowed_with_acl(attribute_mapping.news_item_data_id, user,
                                                                              False, True, False):
                        audit_manager.store_user_activity(user, "ASSESS_ACCESS", str({'file': attribute.value}))
                        return send_file(
                            io.BytesIO(attribute.binary_data),
                            attachment_filename=attribute.value,
                            mimetype=attribute.binary_mime_type,
                            as_attachment=True
                        )
                    else:
                        audit_manager.store_auth_error_activity("Unauthorized access attempt to News Item Data")
                else:
                    audit_manager.store_auth_error_activity("Insufficient permissions")
            else:
                audit_manager.store_auth_error_activity("Invalid JWT")
        else:
            audit_manager.store_auth_error_activity("Missing JWT")


class NewsItemData(Resource):

    @api_key_required
    def get(self):
        return news_item.NewsItemData.get_all_news_items_data()


class UpdateNewsItemData(Resource):

    @api_key_required
    def put(self, id):
        news_item.NewsItemData.update_news_item_data(id, request.json)


def initialize(api):
    api.add_resource(OSINTSourceGroupsAssess, "/api/assess/sources/groups")
    api.add_resource(AddNewsItems, "/api/assess/newsitems/add")
    api.add_resource(NewsItemData, "/api/assess/newsitemdata")
    api.add_resource(UpdateNewsItemData, "/api/assess/newsitemdata/<id>")
    api.add_resource(AddNewsItem, "/api/assess/newsitem/add")
    api.add_resource(NewsItemsByGroup, "/api/assess/newsitems/group/<id>")
    api.add_resource(NewsItem, "/api/assess/newsitem/<id>")
    api.add_resource(NewsItemAggregate, "/api/assess/newsitems/aggregate/<id>")
    api.add_resource(GroupAction, "/api/assess/newsitems/group/action")
    api.add_resource(DownloadAttachment, "/api/assess/newsitem/attribute/download/<id>")

    Permission.add("ASSESS_ACCESS", "Assess access", "Access to Assess module")
    Permission.add("ASSESS_CREATE", "Assess create", "Create news item")
    Permission.add("ASSESS_UPDATE", "Assess update", "Update news item")
    Permission.add("ASSESS_DELETE", "Assess delete", "Delete news item")
