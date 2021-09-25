from flask_restful import Resource
from flask import request
from model import attribute
from model import word_list
from model import report_item_type
from model import product_type
from model.permission import Permission
from model import role
from model import organization
from model import user
from model import acl_entry
from managers.auth_manager import auth_required
from taranisng.schema.role import PermissionSchema
from managers import auth_manager


class DictionariesReload(Resource):

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def get(self, dict_type):
        attribute.Attribute.load_dictionaries(dict_type)
        return "success", 200


class Attributes(Resource):

    @auth_required('CONFIG_ATTRIBUTE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return attribute.Attribute.get_all_json(search)


class AttributeNew(Resource):

    @auth_required('CONFIG_ATTRIBUTE_CREATE')
    def post(self):
        attribute.Attribute.add_attribute(request.json)


class Attribute(Resource):

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def put(self, id):
        attribute.Attribute.update(id, request.json)

    @auth_required('CONFIG_ATTRIBUTE_DELETE')
    def delete(self, id):
        return attribute.Attribute.delete_attribute(id)


class AttributeEnums(Resource):

    @auth_required('CONFIG_ATTRIBUTE_ACCESS')
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

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def post(self, id):
        attribute.AttributeEnum.add(id, request.json)

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def put(self, id):
        attribute.AttributeEnum.update(id, request.json)

    @auth_required('CONFIG_ATTRIBUTE_UPDATE')
    def delete(self, id):
        return attribute.AttributeEnum.delete(id)


class ReportItemTypesConfig(Resource):

    @auth_required('CONFIG_REPORT_TYPE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return report_item_type.ReportItemType.get_all_json(search, auth_manager.get_user_from_jwt(), False)


class ReportItemTypeNew(Resource):

    @auth_required('CONFIG_REPORT_TYPE_CREATE')
    def post(self):
        report_item_type.ReportItemType.add_report_item_type(request.json)


class ReportItemType(Resource):

    @auth_required('CONFIG_REPORT_TYPE_UPDATE')
    def put(self, id):
        report_item_type.ReportItemType.update(id, request.json)

    @auth_required('CONFIG_REPORT_TYPE_DELETE')
    def delete(self, id):
        return report_item_type.ReportItemType.delete_report_item_type(id)


class ProductTypeNew(Resource):

    @auth_required('CONFIG_PRODUCT_TYPE_CREATE')
    def post(self):
        product_type.ProductType.add_new(request.json)


class ProductTypes(Resource):

    @auth_required('CONFIG_PRODUCT_TYPE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return product_type.ProductType.get_all_json(search, auth_manager.get_user_from_jwt(), False)


class ProductType(Resource):

    @auth_required('CONFIG_PRODUCT_TYPE_UPDATE')
    def put(self, id):
        product_type.ProductType.update(id, request.json)

    @auth_required('CONFIG_PRODUCT_TYPE_DELETE')
    def delete(self, id):
        return product_type.ProductType.delete(id)


class Permissions(Resource):

    @auth_required('CONFIG_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return Permission.get_all_json(search)


class ExternalPermissions(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def get(self):
        permissions = auth_manager.get_external_permissions()
        permissions_schema = PermissionSchema(many=True)
        return {'total_count': len(permissions), 'items': permissions_schema.dump(permissions)}


class Roles(Resource):

    @auth_required('CONFIG_ROLE_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return role.Role.get_all_json(search)


class RoleNew(Resource):

    @auth_required('CONFIG_ROLE_CREATE')
    def post(self):
        role.Role.add_new(request.json)


class Role(Resource):

    @auth_required('CONFIG_ROLE_UPDATE')
    def put(self, id):
        role.Role.update(id, request.json)

    @auth_required('CONFIG_ROLE_DELETE')
    def delete(self, id):
        return role.Role.delete(id)


class ACLEntries(Resource):

    @auth_required('CONFIG_ACL_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return acl_entry.ACLEntry.get_all_json(search)


class ACLEntryNew(Resource):

    @auth_required('CONFIG_ACL_CREATE')
    def post(self):
        acl_entry.ACLEntry.add_new(request.json)


class ACLEntry(Resource):

    @auth_required('CONFIG_ACL_UPDATE')
    def put(self, id):
        acl_entry.ACLEntry.update(id, request.json)

    @auth_required('CONFIG_ACL_DELETE')
    def delete(self, id):
        return acl_entry.ACLEntry.delete(id)


class Organizations(Resource):

    @auth_required('CONFIG_ORGANIZATION_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return organization.Organization.get_all_json(search)


class OrganizationNew(Resource):

    @auth_required('CONFIG_ORGANIZATION_CREATE')
    def post(self):
        organization.Organization.add_new(request.json)


class Organization(Resource):

    @auth_required('CONFIG_ORGANIZATION_UPDATE')
    def put(self, id):
        organization.Organization.update(id, request.json)

    @auth_required('CONFIG_ORGANIZATION_DELETE')
    def delete(self, id):
        return organization.Organization.delete(id)


class Users(Resource):

    @auth_required('CONFIG_USER_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return user.User.get_all_json(search)


class UserNew(Resource):

    @auth_required('CONFIG_USER_CREATE')
    def post(self):
        user.User.add_new(request.json)


class User(Resource):

    @auth_required('CONFIG_USER_UPDATE')
    def put(self, id):
        user.User.update(id, request.json)

    @auth_required('CONFIG_USER_DELETE')
    def delete(self, id):
        return user.User.delete(id)


class ExternalUsers(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return user.User.get_all_external_json(auth_manager.get_user_from_jwt(), search)


class ExternalUserNew(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def post(self):
        permissions = auth_manager.get_external_permissions_ids()
        user.User.add_new_external(auth_manager.get_user_from_jwt(), permissions, request.json)


class ExternalUser(Resource):

    @auth_required('MY_ASSETS_CONFIG')
    def put(self, id):
        permissions = auth_manager.get_external_permissions_ids()
        user.User.update_external(auth_manager.get_user_from_jwt(), permissions, id, request.json)

    @auth_required('MY_ASSETS_CONFIG')
    def delete(self, id):
        return user.User.delete_external(auth_manager.get_user_from_jwt(), id)


class WordLists(Resource):

    @auth_required('CONFIG_WORD_LIST_ACCESS')
    def get(self):
        search = None
        if 'search' in request.args and request.args['search']:
            search = request.args['search']
        return word_list.WordList.get_all_json(search, auth_manager.get_user_from_jwt(), False)


class WordListNew(Resource):

    @auth_required('CONFIG_WORD_LIST_CREATE')
    def post(self):
        word_list.WordList.add_new(request.json)


class WordList(Resource):

    @auth_required('CONFIG_WORD_LIST_DELETE')
    def delete(self, id):
        return word_list.WordList.delete(id)

    @auth_required('CONFIG_WORD_LIST_UPDATE')
    def put(self, id):
        word_list.WordList.update(id, request.json)


def initialize(api):
    api.add_resource(DictionariesReload, "/api/config/attributes/dictionaries/<dict_type>/reload")
    api.add_resource(Attributes, "/api/config/attributes")
    api.add_resource(AttributeNew, "/api/config/attribute/new")
    api.add_resource(Attribute, "/api/config/attribute/<id>")
    api.add_resource(AttributeEnums, "/api/config/attribute/enums/<id>")

    api.add_resource(ReportItemTypesConfig, "/api/config/reportitemtypes")
    api.add_resource(ReportItemTypeNew, "/api/config/reportitemtype/new")
    api.add_resource(ReportItemType, "/api/config/reportitemtype/<id>")

    api.add_resource(ProductTypes, "/api/config/producttypes")
    api.add_resource(ProductTypeNew, "/api/config/producttype/new")
    api.add_resource(ProductType, "/api/config/producttype/<id>")

    api.add_resource(Permissions, "/api/config/permissions")
    api.add_resource(ExternalPermissions, "/api/config/external/permissions")
    api.add_resource(Roles, "/api/config/roles")
    api.add_resource(RoleNew, "/api/config/roles/new")
    api.add_resource(Role, "/api/config/role/<id>")
    api.add_resource(ACLEntries, "/api/config/acls")
    api.add_resource(ACLEntryNew, "/api/config/acls/new")
    api.add_resource(ACLEntry, "/api/config/acl/<id>")

    api.add_resource(Organizations, "/api/config/organizations")
    api.add_resource(OrganizationNew, "/api/config/organizations/new")
    api.add_resource(Organization, "/api/config/organization/<id>")

    api.add_resource(Users, "/api/config/users")
    api.add_resource(UserNew, "/api/config/users/new")
    api.add_resource(User, "/api/config/user/<id>")

    api.add_resource(ExternalUsers, "/api/config/external/users")
    api.add_resource(ExternalUserNew, "/api/config/external/users/new")
    api.add_resource(ExternalUser, "/api/config/external/user/<id>")

    api.add_resource(WordLists, "/api/config/wordlists")
    api.add_resource(WordListNew, "/api/config/wordlist/new")
    api.add_resource(WordList, "/api/config/wordlist/<id>")

    Permission.add("CONFIG_ACCESS", "Configuration access", "Access to Configuration module")

    Permission.add("CONFIG_ORGANIZATION_ACCESS", "Config organizations access", "Access to attributes configuration")
    Permission.add("CONFIG_ORGANIZATION_CREATE", "Config organization create", "Create organization configuration")
    Permission.add("CONFIG_ORGANIZATION_UPDATE", "Config organization update", "Update organization configuration")
    Permission.add("CONFIG_ORGANIZATION_DELETE", "Config organization delete", "Delete organization configuration")

    Permission.add("CONFIG_USER_ACCESS", "Config users access", "Access to users configuration")
    Permission.add("CONFIG_USER_CREATE", "Config user create", "Create user configuration")
    Permission.add("CONFIG_USER_UPDATE", "Config user update", "Update user configuration")
    Permission.add("CONFIG_USER_DELETE", "Config user delete", "Delete user configuration")

    Permission.add("CONFIG_ROLE_ACCESS", "Config roles access", "Access to roles configuration")
    Permission.add("CONFIG_ROLE_CREATE", "Config role create", "Create role configuration")
    Permission.add("CONFIG_ROLE_UPDATE", "Config role update", "Update role configuration")
    Permission.add("CONFIG_ROLE_DELETE", "Config role delete", "Delete role configuration")

    Permission.add("CONFIG_ACL_ACCESS", "Config acls access", "Access to acls configuration")
    Permission.add("CONFIG_ACL_CREATE", "Config acl create", "Create acl configuration")
    Permission.add("CONFIG_ACL_UPDATE", "Config acl update", "Update acl configuration")
    Permission.add("CONFIG_ACL_DELETE", "Config acl delete", "Delete acl configuration")

    Permission.add("CONFIG_PRODUCT_TYPE_ACCESS", "Config product types access", "Access to product types configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_CREATE", "Config product type create", "Create product type configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_UPDATE", "Config product type update", "Update product type configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_DELETE", "Config product type delete", "Delete product type configuration")

    Permission.add("CONFIG_ATTRIBUTE_ACCESS", "Config attributes access", "Access to attributes configuration")
    Permission.add("CONFIG_ATTRIBUTE_CREATE", "Config attribute create", "Create attribute configuration")
    Permission.add("CONFIG_ATTRIBUTE_UPDATE", "Config attribute update", "Update attribute configuration")
    Permission.add("CONFIG_ATTRIBUTE_DELETE", "Config attribute delete", "Delete attribute configuration")

    Permission.add("CONFIG_REPORT_TYPE_ACCESS", "Config report item types access",
                   "Access to report item types configuration")
    Permission.add("CONFIG_REPORT_TYPE_CREATE", "Config report item type create",
                   "Create report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_UPDATE", "Config report item type update",
                   "Update report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_DELETE", "Config report item type delete",
                   "Delete report item type configuration")

    Permission.add("CONFIG_WORD_LIST_ACCESS", "Config word lists access", "Access to word lists configuration")
    Permission.add("CONFIG_WORD_LIST_CREATE", "Config word list create", "Create word list configuration")
    Permission.add("CONFIG_WORD_LIST_UPDATE", "Config word list update", "Update word list configuration")
    Permission.add("CONFIG_WORD_LIST_DELETE", "Config word list delete", "Delete word list configuration")
