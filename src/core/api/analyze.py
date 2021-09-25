from flask import request, jsonify, send_file
from flask_restful import Resource
from managers import asset_manager
from managers.auth_manager import auth_required, ACLCheck
from model import report_item
from model import report_item_type
from model.permission import Permission
from model import attribute
from managers import auth_manager, sse_manager, audit_manager
import io


class ReportItemGroups(Resource):

    @auth_required('ANALYZE_ACCESS')
    def get(self):
        return report_item.ReportItem.get_groups()


class ReportItems(Resource):

    @auth_required('ANALYZE_ACCESS')
    def post(self):
        return report_item.ReportItem.get_json(request.json['group'], request.json['filter'], request.json['offset'],
                                               request.json['limit'], auth_manager.get_user_from_jwt())


class ReportItemNew(Resource):

    @auth_required('ANALYZE_CREATE')
    def post(self):
        new_report_item, status = report_item.ReportItem.add_report_item(request.json, auth_manager.get_user_from_jwt())
        if status == 200:
            asset_manager.report_item_changed(new_report_item)
            sse_manager.remote_access_report_items_updated(new_report_item.report_item_type_id)
            sse_manager.report_items_updated()

        return new_report_item.id, status


class ReportItem(Resource):

    @auth_required('ANALYZE_ACCESS', ACLCheck.REPORT_ITEM_ACCESS)
    def get(self, id):
        return report_item.ReportItem.get_detail_json(id)

    @auth_required('ANALYZE_UPDATE', ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, id):
        modified, data = report_item.ReportItem.update_report_item(id, request.json, auth_manager.get_user_from_jwt())
        if modified is True:
            updated_report_item = report_item.ReportItem.find(id)
            asset_manager.report_item_changed(updated_report_item)
            sse_manager.report_item_updated(data)
            sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)

        return data

    @auth_required('ANALYZE_DELETE', ACLCheck.REPORT_ITEM_MODIFY)
    def delete(self, id):
        result, code = report_item.ReportItem.delete_report_item(id)
        if code == 200:
            sse_manager.report_items_updated()

        return result, code


class ReportItemData(Resource):

    @auth_required('ANALYZE_ACCESS', ACLCheck.REPORT_ITEM_ACCESS)
    def post(self, id):
        return report_item.ReportItem.get_updated_data(id, request.json)


class ReportItemLocks(Resource):

    @auth_required('ANALYZE_UPDATE', ACLCheck.REPORT_ITEM_MODIFY)
    def get(self, id):
        if id in sse_manager.report_item_locks:
            return jsonify(sse_manager.report_item_locks[id])
        else:
            return '{}'


class ReportItemLock(Resource):

    @auth_required('ANALYZE_UPDATE', ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, id):
        sse_manager.report_item_lock(id, request.json['field_id'], auth_manager.get_user_from_jwt().id)


class ReportItemUnlock(Resource):

    @auth_required('ANALYZE_UPDATE', ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, id):
        sse_manager.report_item_unlock(id, request.json['field_id'], auth_manager.get_user_from_jwt().id)


class ReportItemHoldLock(Resource):

    @auth_required('ANALYZE_UPDATE', ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, id):
        sse_manager.report_item_hold_lock(id, request.json['field_id'], auth_manager.get_user_from_jwt().id)


class ReportItemTypes(Resource):

    @auth_required('ANALYZE_ACCESS')
    def get(self):
        return report_item_type.ReportItemType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class ReportItemAttributeEnums(Resource):

    @auth_required('ANALYZE_ACCESS')
    def get(self, id):
        search = None
        offset = 0
        limit = 10
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        if 'offset' in request.args and request.args['offset']:
            offset = request.args['offset']
        if 'limit' in request.args and request.args['limit']:
            limit = request.args['limit']
        return attribute.AttributeEnum.get_for_attribute_json(id, search, offset, limit)


class ReportItemAddAttachment(Resource):

    @auth_required(['ANALYZE_CREATE', 'ANALYZE_UPDATE'], ACLCheck.REPORT_ITEM_MODIFY)
    def post(self, id):
        file = request.files.get('file')
        if file:
            user = auth_manager.get_user_from_jwt()
            attribute_group_item_id = request.form['attribute_group_item_id']
            description = request.form['description']
            data = report_item.ReportItem.add_attachment(id, attribute_group_item_id, user, file, description)
            updated_report_item = report_item.ReportItem.find(id)
            asset_manager.report_item_changed(updated_report_item)
            sse_manager.report_item_updated(data)
            sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)

            return data


class ReportItemRemoveAttachment(Resource):

    @auth_required('ANALYZE_UPDATE', ACLCheck.REPORT_ITEM_MODIFY)
    def post(self, id):
        user = auth_manager.get_user_from_jwt()
        data = report_item.ReportItem.remove_attachment(id, request.json['attribute_id'], user)
        updated_report_item = report_item.ReportItem.find(id)
        asset_manager.report_item_changed(updated_report_item)
        sse_manager.report_item_updated(data)
        sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)


class ReportItemDownloadAttachment(Resource):

    def get(self, id):
        if 'jwt' in request.args:
            user = auth_manager.decode_user_from_jwt(request.args['jwt'])
            if user is not None:
                permissions = user.get_permissions()
                if 'ANALYZE_ACCESS' in permissions:
                    report_item_attribute = report_item.ReportItemAttribute.find(id)
                    if report_item.ReportItem.allowed_with_acl(report_item_attribute.report_item.id, user, False, True,
                                                               False):
                        audit_manager.store_user_activity(user, "ANALYZE_ACCESS",
                                                          str({'file': report_item_attribute.value}))

                        return send_file(
                            io.BytesIO(report_item_attribute.binary_data),
                            attachment_filename=report_item_attribute.value,
                            mimetype=report_item_attribute.binary_mime_type,
                            as_attachment=True
                        )
                    else:
                        audit_manager.store_auth_error_activity("Unauthorized access attempt to Report Item Attribute")
                else:
                    audit_manager.store_auth_error_activity("Insufficient permissions")
            else:
                audit_manager.store_auth_error_activity("Invalid JWT")
        else:
            audit_manager.store_auth_error_activity("Missing JWT")


def initialize(api):
    api.add_resource(ReportItemGroups, "/api/analyze/reportitems/groups")
    api.add_resource(ReportItems, "/api/analyze/reportitems")
    api.add_resource(ReportItemNew, "/api/analyze/reportitem/new")
    api.add_resource(ReportItemTypes, "/api/analyze/reportitem/types")
    api.add_resource(ReportItem, "/api/analyze/reportitem/<id>")
    api.add_resource(ReportItemData, "/api/analyze/reportitem/data/<id>")
    api.add_resource(ReportItemLocks, "/api/analyze/reportitem/locks/<id>")
    api.add_resource(ReportItemLock, "/api/analyze/reportitem/lock/<id>")
    api.add_resource(ReportItemUnlock, "/api/analyze/reportitem/unlock/<id>")
    api.add_resource(ReportItemHoldLock, "/api/analyze/reportitem/holdlock/<id>")
    api.add_resource(ReportItemAttributeEnums, "/api/analyze/attribute/enums/<id>")
    api.add_resource(ReportItemAddAttachment, "/api/analyze/attribute/addattachment/<id>")
    api.add_resource(ReportItemRemoveAttachment, "/api/analyze/attribute/removeattachment/<id>")
    api.add_resource(ReportItemDownloadAttachment, "/api/analyze/attribute/download/<id>")

    Permission.add("ANALYZE_ACCESS", "Analyze access", "Access to Analyze module")
    Permission.add("ANALYZE_CREATE", "Analyze create", "Create report item")
    Permission.add("ANALYZE_UPDATE", "Analyze update", "Update report item")
    Permission.add("ANALYZE_DELETE", "Analyze delete", "Delete report item")
