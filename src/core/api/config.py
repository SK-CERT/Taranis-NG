"""Configuration module API."""

import io
from flask import request, send_file
from flask_restful import Resource

from managers import (
    auth_manager,
    remote_manager,
    presenters_manager,
    publishers_manager,
    bots_manager,
    external_auth_manager,
    log_manager,
    collectors_manager,
)
from managers.log_manager import logger
from managers.sse_manager import sse_manager
from managers.auth_manager import auth_required, get_user_from_jwt
from model import (
    acl_entry,
    remote,
    presenters_node,
    publisher_preset,
    publishers_node,
    bots_node,
    bot_preset,
    attribute,
    collectors_node,
    organization,
    osint_source,
    product_type,
    report_item_type,
    role,
    user,
    word_list,
)
from model.news_item import NewsItemAggregate
from model.permission import Permission
from shared.schema.role import PermissionSchema


class DictionariesReload(Resource):
    """Dictionaries reload API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def get(self, dictionary_type):
        """Reload dictionaries.

        Args:
            dictionary_type (str): The dictionary type
        Returns:
            (str, int): The result of the reload
        """
        attribute.Attribute.load_dictionaries(dictionary_type)
        return "success", 200


class Attributes(Resource):
    """Attributes API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_ACCESS")
    def get(self):
        """Get all attributes.

        Returns:
            (dict): The attributes
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return attribute.Attribute.get_all_json(search)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self):
        """Create an attribute.

        Returns:
            (str, int): The result of the create
        """
        try:
            attribute.Attribute.add_attribute(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create attribute")
            return "", 400


class Attribute(Resource):
    """Attribute API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id):
        """Update an attribute.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (str, int): The result of the update
        """
        try:
            attribute.Attribute.update(attribute_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update attribute")
            return "", 400

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id):
        """Delete an attribute.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return attribute.Attribute.delete_attribute(attribute_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete attribute")
            return "", 400


class AttributeEnums(Resource):
    """Attribute enums API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_ACCESS")
    def get(self, attribute_id):
        """Get all attribute enums.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (dict): The attribute enums
        """
        search = None
        offset = 0
        limit = 10
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        if "offset" in request.args and request.args["offset"]:
            offset = request.args["offset"]
        if "limit" in request.args and request.args["limit"]:
            limit = request.args["limit"]
        return attribute.AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self, attribute_id):
        """Create an attribute enum.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (str, int): The result of the create
        """
        try:
            attribute.AttributeEnum.add(attribute_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create attribute enum")
            return "", 400


class AttributeEnum(Resource):
    """Attribute enum API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id, enum_id):
        """Update an attribute enum.

        Args:
            attribute_id (int): The attribute ID
            enum_id (int): The enum ID
        Returns:
            (str, int): The result of the update
        """
        try:
            attribute.AttributeEnum.update(enum_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update attribute enum")
            return "", 400

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id, enum_id):
        """Delete an attribute enum.

        Args:
            attribute_id (int): The attribute ID
            enum_id (int): The enum ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return attribute.AttributeEnum.delete(enum_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete attribute enum")
            return "", 400


class ReportItemTypesConfig(Resource):
    """Report item types API endpoint."""

    @auth_required("CONFIG_REPORT_TYPE_ACCESS")
    def get(self):
        """Get all report item types.

        Returns:
            (dict): The report item types
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return report_item_type.ReportItemType.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_REPORT_TYPE_CREATE")
    def post(self):
        """Create a report item type.

        Returns:
            (str, int): The result of the create
        """
        try:
            report_item_type.ReportItemType.add_report_item_type(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create report type")
            return "", 400


class ReportItemType(Resource):
    """Report item type API endpoint."""

    @auth_required("CONFIG_REPORT_TYPE_UPDATE")
    def put(self, type_id):
        """Update a report item type.

        Args:
            type_id (int): The report item type ID
        Returns:
            (str, int): The result of the update
        """
        try:
            report_item_type.ReportItemType.update(type_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update report type")
            return "", 400

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id):
        """Delete a report item type.

        Args:
            type_id (int): The report item type ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return report_item_type.ReportItemType.delete_report_item_type(type_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete report type")
            return "", 400


class ProductTypes(Resource):
    """Product types API endpoint."""

    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def get(self):
        """Get all product types.

        Returns:
            (dict): The product types
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return product_type.ProductType.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self):
        """Create a product type.

        Returns:
            (str, int): The result of the create
        """
        try:
            product_type.ProductType.add_new(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create product type")
            return "", 400


class ProductType(Resource):
    """Product type API endpoint."""

    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id):
        """Update a product type.

        Args:
            type_id (int): The product type ID
        Returns:
            (str, int): The result of the update
        """
        try:
            product_type.ProductType.update(type_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update product type")
            return "", 400

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id):
        """Delete a product type.

        Args:
            type_id (int): The product type ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return product_type.ProductType.delete(type_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete product type")
            return "", 400


class Permissions(Resource):
    """Permissions API endpoint."""

    @auth_required("CONFIG_ACCESS")
    def get(self):
        """Get all permissions.

        Returns:
            (dict): The permissions
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return Permission.get_all_json(search)


class ExternalPermissions(Resource):
    """External permissions API endpoint."""

    @auth_required("MY_ASSETS_CONFIG")
    def get(self):
        """Get all external permissions.

        Returns:
            (dict): The external permissions
        """
        permissions = auth_manager.get_external_permissions()
        permissions_schema = PermissionSchema(many=True)
        return {"total_count": len(permissions), "items": permissions_schema.dump(permissions)}


class Roles(Resource):
    """Roles API endpoint."""

    @auth_required("CONFIG_ROLE_ACCESS")
    def get(self):
        """Get all roles.

        Returns:
            (dict): The roles
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return role.Role.get_all_json(search)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self):
        """Create a role.

        Returns:
            (str, int): The result of the create
        """
        try:
            role.Role.add_new(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create role")
            return "", 400


class Role(Resource):
    """Role API endpoint."""

    @auth_required("CONFIG_ROLE_UPDATE")
    def put(self, role_id):
        """Update a role.

        Args:
            role_id (int): The role ID
        Returns:
            (str, int): The result of the update
        """
        try:
            role.Role.update(role_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update role")
            return "", 400

    @auth_required("CONFIG_ROLE_DELETE")
    def delete(self, role_id):
        """Delete a role.

        Args:
            role_id (int): The role ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return role.Role.delete(role_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete role")
            return "", 400


class ACLEntries(Resource):
    """ACL entries API endpoint."""

    @auth_required("CONFIG_ACL_ACCESS")
    def get(self):
        """Get all ACL entries.

        Returns:
            (dict): The ACL entries
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return acl_entry.ACLEntry.get_all_json(search)

    @auth_required("CONFIG_ACL_CREATE")
    def post(self):
        """Create an ACL entry.

        Returns:
            (str, int): The result of the create
        """
        try:
            acl_entry.ACLEntry.add_new(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create acl entry")
            return "", 400


class ACLEntry(Resource):
    """ACL entry API endpoint."""

    @auth_required("CONFIG_ACL_UPDATE")
    def put(self, acl_id):
        """Update an ACL entry.

        Args:
            acl_id (int): The ACL entry ID
        Returns:
            (str, int): The result of the update
        """
        try:
            acl_entry.ACLEntry.update(acl_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update acl entry")
            return "", 400

    @auth_required("CONFIG_ACL_DELETE")
    def delete(self, acl_id):
        """Delete an ACL entry.

        Args:
            acl_id (int): The ACL entry ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return acl_entry.ACLEntry.delete(acl_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete acl entry")
            return "", 400


class Organizations(Resource):
    """Organizations API endpoint."""

    @auth_required("CONFIG_ORGANIZATION_ACCESS")
    def get(self):
        """Get all organizations.

        Returns:
            (dict): The organizations
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return organization.Organization.get_all_json(search)

    @auth_required("CONFIG_ORGANIZATION_CREATE")
    def post(self):
        """Create an organization.

        Returns:
            (str, int): The result of the create
        """
        try:
            organization.Organization.add_new(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create organization")
            return "", 400


class Organization(Resource):
    """Organization API endpoint."""

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id):
        """Update an organization.

        Args:
            organization_id (int): The organization ID
        Returns:
            (str, int): The result of the update
        """
        try:
            organization.Organization.update(organization_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update organization")
            return "", 400

    @auth_required("CONFIG_ORGANIZATION_DELETE")
    def delete(self, organization_id):
        """Delete an organization.

        Args:
            organization_id (int): The organization ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return organization.Organization.delete(organization_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete organization")
            return "", 400


class Users(Resource):
    """Users API endpoint."""

    @auth_required("CONFIG_USER_ACCESS")
    def get(self):
        """Get all users.

        Returns:
            (dict): The users
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return user.User.get_all_json(search)

    @auth_required("CONFIG_USER_CREATE")
    def post(self):
        """Create a user.

        Returns:
            (str, int): The result of the create
        """
        try:
            external_auth_manager.create_user(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create user in external auth system")
            return "", 400

        user.User.add_new(request.json)


class User(Resource):
    """User API endpoint."""

    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id):
        """Update a user.

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the update
        """
        original_user = user.User.find_by_id(user_id)
        original_username = original_user.username

        try:
            external_auth_manager.update_user(request.json, original_username)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update user in external auth system")
            return "", 400

        user.User.update(user_id, request.json)

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id):
        """Delete a user.

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the delete
        """
        original_user = user.User.find_by_id(user_id)
        original_username = original_user.username

        user.User.delete(user_id)

        try:
            external_auth_manager.delete_user(original_username)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete user in external auth system")
            return "", 400


class ExternalUsers(Resource):
    """External users API endpoint."""

    @auth_required("MY_ASSETS_CONFIG")
    def get(self):
        """Get all external users.

        Returns:
            (dict): The external users
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return user.User.get_all_external_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self):
        """Create an external user.

        Returns:
            (str, int): The result of the create
        """
        try:
            permissions = auth_manager.get_external_permissions_ids()
            user.User.add_new_external(auth_manager.get_user_from_jwt(), permissions, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create external user")
            return "", 400


class ExternalUser(Resource):
    """External user API endpoint."""

    @auth_required("MY_ASSETS_CONFIG")
    def put(self, user_id):
        """Update an external user.

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the update
        """
        try:
            permissions = auth_manager.get_external_permissions_ids()
            user.User.update_external(auth_manager.get_user_from_jwt(), permissions, user_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update external user")
            return "", 400

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, user_id):
        """Delete an external user.

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return user.User.delete_external(auth_manager.get_user_from_jwt(), user_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete external user")
            return "", 400


class WordLists(Resource):
    """Word lists API endpoint."""

    @auth_required("CONFIG_WORD_LIST_ACCESS")
    def get(self):
        """Get all word lists.

        Returns:
            (dict): The word lists
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return word_list.WordList.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_WORD_LIST_CREATE")
    def post(self):
        """Create a word list.

        Returns:
            (str, int): The result of the create
        """
        try:
            word_list.WordList.add_new(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create word list")
            return "", 400


class WordList(Resource):
    """Word list API endpoint."""

    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id):
        """Delete a word list.

        Args:
            word_list_id (int): The word list ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return word_list.WordList.delete(word_list_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete word list")
            return "", 400

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id):
        """Update a word list.

        Args:
            word_list_id (int): The word list ID
        Returns:
            (str, int): The result of the update
        """
        try:
            word_list.WordList.update(word_list_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update word list")
            return "", 400


class CollectorsNodes(Resource):
    """Collectors nodes API endpoint."""

    @auth_required("CONFIG_COLLECTORS_NODE_ACCESS")
    def get(self):
        """Get all collectors nodes.

        Returns:
            (dict): The collectors nodes
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return collectors_node.CollectorsNode.get_all_json(search)

    @auth_required("CONFIG_COLLECTORS_NODE_CREATE")
    def post(self):
        """Create a collectors node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", collectors_manager.add_collectors_node(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create collectors node")
            return "", 400


class CollectorsNode(Resource):
    """Collectors node API endpoint."""

    @auth_required("CONFIG_COLLECTORS_NODE_UPDATE")
    def put(self, node_id):
        """Update a collectors node.

        Args:
            node_id (int): The collectors node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            collectors_manager.update_collectors_node(node_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update collectors node")
            return "", 400

    @auth_required("CONFIG_COLLECTORS_NODE_DELETE")
    def delete(self, node_id):
        """Delete a collectors node.

        Args:
            node_id (int): The collectors node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            collectors_node.CollectorsNode.delete(node_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete collectors node")
            return "", 400


class OSINTSources(Resource):
    """OSINT sources API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self):
        """Get all OSINT sources.

        Returns:
            (dict): The OSINT sources
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return osint_source.OSINTSource.get_all_json(search)

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        """Create an OSINT source.

        Returns:
            (str, int): The result of the create
        """
        try:
            collectors_manager.add_osint_source(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create OSINT source")
            return "", 400


class OSINTSource(Resource):
    """OSINT source API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id):
        """Update an OSINT source.

        Args:
            source_id (int): The OSINT source ID
        Returns:
            (str, int): The result of the update
        """
        try:
            updated_osint_source, default_group = collectors_manager.update_osint_source(source_id, request.json)
            if default_group is not None:
                NewsItemAggregate.reassign_to_new_groups(updated_osint_source.id, default_group.id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update OSINT source")
            return "", 400

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id):
        """Delete an OSINT source.

        Args:
            source_id (int): The OSINT source ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            collectors_manager.delete_osint_source(source_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete OSINT source")
            return "", 400


class OSINTSourcesExport(Resource):
    """OSINT sources export API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def post(self):
        """Export OSINT sources.

        Returns:
            (str, int): The result of the export
        """
        try:
            data = collectors_manager.export_osint_sources(request.json)
            return send_file(
                io.BytesIO(data), attachment_filename="osint_sources_export.json", mimetype="application/json", as_attachment=True
            )
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not export OSINT source")
            return "", 400


class OSINTSourcesImport(Resource):
    """OSINT sources import API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self):
        """Import OSINT sources.

        Returns:
            (str, int): The result of the import
        """
        try:
            file = request.files.get("file")
            if file:
                collectors_node_id = request.form["collectors_node_id"]
                collectors_manager.import_osint_sources(collectors_node_id, file)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not import OSINT source")
            return "", 400


class OSINTSourceGroups(Resource):
    """OSINT source groups API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    def get(self):
        """Get all OSINT source groups.

        Returns:
            (dict): The OSINT source groups
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return osint_source.OSINTSourceGroup.get_all_json(search, auth_manager.get_user_from_jwt(), False)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self):
        """Create an OSINT source group.

        Returns:
            (str, int): The result of the create
        """
        try:
            osint_source.OSINTSourceGroup.add(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create OSINT source group")
            return "", 400


class OSINTSourceGroup(Resource):
    """OSINT source group API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id):
        """Update an OSINT source group.

        Args:
            group_id (int): The OSINT source group ID
        Returns:
            (str, int): The result of the update
        """
        try:
            sources_in_default_group, message, code = osint_source.OSINTSourceGroup.update(group_id, request.json)
            if sources_in_default_group is not None:
                default_group = osint_source.OSINTSourceGroup.get_default()
                for source in sources_in_default_group:
                    NewsItemAggregate.reassign_to_new_groups(source.id, default_group.id)
            return message, code
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update OSINT source group")
            return "", 400

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id):
        """Delete an OSINT source group.

        Args:
            group_id (int): The OSINT source group ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return osint_source.OSINTSourceGroup.delete(group_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete OSINT source group")
            return "", 400


class RemoteAccesses(Resource):
    """Remote accesses API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self):
        """Get all remote accesses.

        Returns:
            (dict): The remote accesses
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return remote.RemoteAccess.get_all_json(search)

    @auth_required("CONFIG_REMOTE_ACCESS_CREATE")
    def post(self):
        """Create a remote access.

        Returns:
            (str, int): The result of the create
        """
        try:
            remote.RemoteAccess.add(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create remote access")
            return "", 400


class RemoteAccess(Resource):
    """Remote access API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_UPDATE")
    def put(self, remote_access_id):
        """Update a remote access.

        Args:
            remote_access_id (int): The remote access ID
        Returns:
            (str, int): The result of the update
        """
        try:
            event_id, disconnect = remote.RemoteAccess.update(remote_access_id, request.json)
            if disconnect:
                sse_manager.remote_access_disconnect([event_id])
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update remote access")
            return "", 400

    @auth_required("CONFIG_REMOTE_ACCESS_DELETE")
    def delete(self, remote_access_id):
        """Delete a remote access.

        Args:
            remote_access_id (int): The remote access ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return remote.RemoteAccess.delete(remote_access_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete remote access")
            return "", 400


class RemoteNodes(Resource):
    """Remote nodes API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self):
        """Get all remote nodes.

        Returns:
            (dict): The remote nodes
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return remote.RemoteNode.get_all_json(search)

    @auth_required("CONFIG_REMOTE_ACCESS_CREATE")
    def post(self):
        """Create a remote node.

        Returns:
            (str, int): The result of the create
        """
        try:
            remote.RemoteNode.add(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create remote node")
            return "", 400


class RemoteNode(Resource):
    """Remote node API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_UPDATE")
    def put(self, remote_node_id):
        """Update a remote node.

        Args:
            remote_node_id (int): The remote node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            if remote.RemoteNode.update(id, request.json) is False:
                remote_manager.disconnect_from_node(remote_node_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update remote node")
            return "", 400

    @auth_required("CONFIG_REMOTE_ACCESS_DELETE")
    def delete(self, remote_node_id):
        """Delete a remote node.

        Args:
            remote_node_id (int): The remote node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            remote_manager.disconnect_from_node(remote_node_id)
            return remote.RemoteNode.delete(id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete remote node")
            return "", 400


class RemoteNodeConnect(Resource):
    """Remote node connect API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self, remote_node_id):
        """Connect to a remote node.

        Args:
            remote_node_id (int): The remote node ID
        Returns:
            (str, int): The result of the connect
        """
        try:
            return remote_manager.connect_to_node(remote_node_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not connect to node")
            return "", 400


class PresentersNodes(Resource):
    """Presenters nodes API endpoint."""

    @auth_required("CONFIG_PRESENTERS_NODE_ACCESS")
    def get(self):
        """Get all presenters nodes.

        Returns:
            (dict): The presenters nodes
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return presenters_node.PresentersNode.get_all_json(search)

    @auth_required("CONFIG_PRESENTERS_NODE_CREATE")
    def post(self):
        """Create a presenters node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", presenters_manager.add_presenters_node(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create presenters node")
            return "", 400


class PresentersNode(Resource):
    """Presenters node API endpoint."""

    @auth_required("CONFIG_PRESENTERS_NODE_UPDATE")
    def put(self, node_id):
        """Update a presenters node.

        Args:
            node_id (int): The presenters node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            presenters_manager.update_presenters_node(node_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update presenters node")
            return "", 400

    @auth_required("CONFIG_PRESENTERS_NODE_DELETE")
    def delete(self, node_id):
        """Delete a presenters node.

        Args:
            node_id (int): The presenters node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return presenters_node.PresentersNode.delete(node_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete presenters node")
            return "", 400


class PublisherNodes(Resource):
    """Publisher nodes API endpoint."""

    @auth_required("CONFIG_PUBLISHERS_NODE_ACCESS")
    def get(self):
        """Get all publisher nodes.

        Returns:
            (dict): The publisher nodes
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return publishers_node.PublishersNode.get_all_json(search)

    @auth_required("CONFIG_PUBLISHERS_NODE_CREATE")
    def post(self):
        """Create a publisher node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", publishers_manager.add_publishers_node(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create publishers node")
            return "", 400


class PublishersNode(Resource):
    """Publisher node API endpoint."""

    @auth_required("CONFIG_PUBLISHERS_NODE_UPDATE")
    def put(self, node_id):
        """Update a publisher node.

        Args:
            node_id (int): The publisher node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            publishers_manager.update_publishers_node(node_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update publishers node")
            return "", 400

    @auth_required("CONFIG_PUBLISHERS_NODE_DELETE")
    def delete(self, node_id):
        """Delete a publisher node.

        Args:
            node_id (int): The publisher node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return publishers_node.PublishersNode.delete(node_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete publishers node")
            return "", 400


class PublisherPresets(Resource):
    """Publisher presets API endpoint."""

    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self):
        """Get all publisher presets.

        Returns:
            (dict): The publisher presets
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return publisher_preset.PublisherPreset.get_all_json(search)

    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self):
        """Create a publisher preset.

        Returns:
            (str, int): The result of the create
        """
        try:
            publishers_manager.add_publisher_preset(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create publishers preset")
            return "", 400


class PublisherPreset(Resource):
    """Publisher preset API endpoint."""

    @auth_required("CONFIG_PUBLISHER_PRESET_UPDATE")
    def put(self, preset_id):
        """Update a publisher preset.

        Args:
            preset_id (int): The publisher preset ID
        Returns:
            (str, int): The result of the update
        """
        try:
            publisher_preset.PublisherPreset.update(preset_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update publishers preset")
            return "", 400

    @auth_required("CONFIG_PUBLISHER_PRESET_DELETE")
    def delete(self, preset_id):
        """Delete a publisher preset.

        Args:
            preset_id (int): The publisher preset ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return publisher_preset.PublisherPreset.delete(preset_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete publishers preset")
            return "", 400


class BotNodes(Resource):
    """Bot nodes API endpoint."""

    @auth_required("CONFIG_BOTS_NODE_ACCESS")
    def get(self):
        """Get all bot nodes.

        Returns:
            (dict): The bot nodes
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return bots_node.BotsNode.get_all_json(search)

    @auth_required("CONFIG_BOTS_NODE_CREATE")
    def post(self):
        """Create a bot node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", bots_manager.add_bots_node(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create bots node")
            return "", 400


class BotsNode(Resource):
    """Bot node API endpoint."""

    @auth_required("CONFIG_BOTS_NODE_UPDATE")
    def put(self, node_id):
        """Update a bot node.

        Args:
            node_id (int): The bot node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            bots_manager.update_bots_node(node_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update bots node")
            return "", 400

    @auth_required("CONFIG_BOTS_NODE_DELETE")
    def delete(self, node_id):
        """Delete a bot node.

        Args:
            node_id (int): The bot node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return bots_node.BotsNode.delete(node_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete bots node")
            return "", 400


class BotPresets(Resource):
    """Bot presets API endpoint."""

    @auth_required("CONFIG_BOT_PRESET_ACCESS")
    def get(self):
        """Get all bot presets.

        Returns:
            (dict): The bot presets
        """
        search = None
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        return bot_preset.BotPreset.get_all_json(search)

    @auth_required("CONFIG_BOT_PRESET_CREATE")
    def post(self):
        """Create a bot preset.

        Returns:
            (str, int): The result of the create
        """
        try:
            bots_manager.add_bot_preset(request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not create bots preset")
            return "", 400


class BotPreset(Resource):
    """Bot preset API endpoint."""

    @auth_required("CONFIG_BOT_PRESET_UPDATE")
    def put(self, preset_id):
        """Update a bot preset.

        Args:
            preset_id (int): The bot preset ID
        Returns:
            (str, int): The result of the update
        """
        try:
            bot_preset.BotPreset.update(preset_id, request.json)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not update bots preset")
            return "", 400

    @auth_required("CONFIG_BOT_PRESET_DELETE")
    def delete(self, preset_id):
        """Delete a bot preset.

        Args:
            preset_id (int): The bot preset ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return bot_preset.BotPreset.delete(preset_id)
        except Exception as ex:
            logger.critical(ex)
            log_manager.store_data_error_activity(get_user_from_jwt(), "Could not delete bots preset")
            return "", 400


def initialize(api):
    """Initialize the API.

    Args:
        api (Flask): The Flask application
    """
    api.add_resource(DictionariesReload, "/api/v1/config/reload-enum-dictionaries/<string:dictionary_type>")
    api.add_resource(Attributes, "/api/v1/config/attributes")
    api.add_resource(Attribute, "/api/v1/config/attributes/<int:attribute_id>")
    api.add_resource(AttributeEnums, "/api/v1/config/attributes/<int:attribute_id>/enums")
    api.add_resource(AttributeEnum, "/api/v1/config/attributes/<int:attribute_id>/enums/<int:enum_id>")

    api.add_resource(ReportItemTypesConfig, "/api/v1/config/report-item-types")
    api.add_resource(ReportItemType, "/api/v1/config/report-item-types/<int:type_id>")

    api.add_resource(ProductTypes, "/api/v1/config/product-types")
    api.add_resource(ProductType, "/api/v1/config/product-types/<int:type_id>")

    api.add_resource(Permissions, "/api/v1/config/permissions")
    api.add_resource(ExternalPermissions, "/api/v1/config/external-permissions")
    api.add_resource(Roles, "/api/v1/config/roles")
    api.add_resource(Role, "/api/v1/config/roles/<int:role_id>")
    api.add_resource(ACLEntries, "/api/v1/config/acls")
    api.add_resource(ACLEntry, "/api/v1/config/acls/<int:acl_id>")

    api.add_resource(Organizations, "/api/v1/config/organizations")
    api.add_resource(Organization, "/api/v1/config/organizations/<int:organization_id>")

    api.add_resource(Users, "/api/v1/config/users")
    api.add_resource(User, "/api/v1/config/users/<int:user_id>")

    api.add_resource(ExternalUsers, "/api/v1/config/external-users")
    api.add_resource(ExternalUser, "/api/v1/config/external-users/<int:user_id>")

    api.add_resource(WordLists, "/api/v1/config/word-lists")
    api.add_resource(WordList, "/api/v1/config/word-lists/<int:word_list_id>")

    api.add_resource(CollectorsNodes, "/api/v1/config/collectors-nodes")
    api.add_resource(CollectorsNode, "/api/v1/config/collectors-nodes/<string:node_id>")
    api.add_resource(OSINTSources, "/api/v1/config/osint-sources")
    api.add_resource(OSINTSource, "/api/v1/config/osint-sources/<string:source_id>")
    api.add_resource(OSINTSourcesExport, "/api/v1/config/export-osint-sources")
    api.add_resource(OSINTSourcesImport, "/api/v1/config/import-osint-sources")
    api.add_resource(OSINTSourceGroups, "/api/v1/config/osint-source-groups")
    api.add_resource(OSINTSourceGroup, "/api/v1/config/osint-source-groups/<string:group_id>")

    api.add_resource(RemoteAccesses, "/api/v1/config/remote-accesses")
    api.add_resource(RemoteAccess, "/api/v1/config/remote-accesses/<int:remote_access_id>")

    api.add_resource(RemoteNodes, "/api/v1/config/remote-nodes")
    api.add_resource(RemoteNode, "/api/v1/config/remote-nodes/<int:remote_node_id>")
    api.add_resource(RemoteNodeConnect, "/api/v1/config/remote-nodes/<int:remote_node_id>/connect")

    api.add_resource(PresentersNodes, "/api/v1/config/presenters-nodes")
    api.add_resource(PresentersNode, "/api/v1/config/presenters-nodes/<string:node_id>")

    api.add_resource(PublisherNodes, "/api/v1/config/publishers-nodes")
    api.add_resource(PublishersNode, "/api/v1/config/publishers-nodes/<string:node_id>")

    api.add_resource(PublisherPresets, "/api/v1/config/publishers-presets")
    api.add_resource(PublisherPreset, "/api/v1/config/publishers-presets/<string:preset_id>")

    api.add_resource(BotNodes, "/api/v1/config/bots-nodes")
    api.add_resource(BotsNode, "/api/v1/config/bots-nodes/<string:node_id>")

    api.add_resource(BotPresets, "/api/v1/config/bots-presets")
    api.add_resource(BotPreset, "/api/v1/config/bots-presets/<string:preset_id>")

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

    Permission.add("CONFIG_REPORT_TYPE_ACCESS", "Config report item types access", "Access to report item types configuration")
    Permission.add("CONFIG_REPORT_TYPE_CREATE", "Config report item type create", "Create report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_UPDATE", "Config report item type update", "Update report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_DELETE", "Config report item type delete", "Delete report item type configuration")

    Permission.add("CONFIG_WORD_LIST_ACCESS", "Config word lists access", "Access to word lists configuration")
    Permission.add("CONFIG_WORD_LIST_CREATE", "Config word list create", "Create word list configuration")
    Permission.add("CONFIG_WORD_LIST_UPDATE", "Config word list update", "Update word list configuration")
    Permission.add("CONFIG_WORD_LIST_DELETE", "Config word list delete", "Delete word list configuration")

    Permission.add("CONFIG_COLLECTORS_NODE_ACCESS", "Config collectors nodes access", "Access to collectors nodes configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_CREATE", "Config collectors node create", "Create collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_UPDATE", "Config collectors node update", "Update collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_DELETE", "Config collectors node delete", "Delete collectors node configuration")

    Permission.add("CONFIG_OSINT_SOURCE_ACCESS", "Config OSINT source access", "Access to OSINT sources configuration")
    Permission.add("CONFIG_OSINT_SOURCE_CREATE", "Config OSINT source create", "Create OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_UPDATE", "Config OSINT source update", "Update OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_DELETE", "Config OSINT source delete", "Delete OSINT source configuration")

    Permission.add("CONFIG_OSINT_SOURCE_GROUP_ACCESS", "Config OSINT source group access", "Access to OSINT sources groups configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_CREATE", "Config OSINT source group create", "Create OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_UPDATE", "Config OSINT source group update", "Update OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_DELETE", "Config OSINT source group delete", "Delete OSINT source group configuration")

    Permission.add("CONFIG_REMOTE_ACCESS_ACCESS", "Config remote access access", "Access to remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_CREATE", "Config remote access create", "Create remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_UPDATE", "Config remote access update", "Update remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_DELETE", "Config remote access delete", "Delete remote access configuration")

    Permission.add("CONFIG_REMOTE_NODE_ACCESS", "Config remote nodes access", "Access to remote nodes configuration")
    Permission.add("CONFIG_REMOTE_NODE_CREATE", "Config remote node create", "Create remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_UPDATE", "Config remote node update", "Update remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_DELETE", "Config remote node delete", "Delete remote node configuration")

    Permission.add("CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access", "Access to presenters nodes configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create", "Create presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update", "Update presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete", "Delete presenters node configuration")

    Permission.add("CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access", "Access to publishers nodes configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create", "Create publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update", "Update publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete", "Delete publishers node configuration")

    Permission.add("CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access", "Access to publisher presets configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create", "Create publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update", "Update publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete", "Delete publisher preset configuration")

    Permission.add("CONFIG_BOTS_NODE_ACCESS", "Config bots nodes access", "Access to bots nodes configuration")
    Permission.add("CONFIG_BOTS_NODE_CREATE", "Config bots node create", "Create bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_UPDATE", "Config bots node update", "Update bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_DELETE", "Config bots node delete", "Delete bots node configuration")

    Permission.add("CONFIG_BOT_PRESET_ACCESS", "Config bot presets access", "Access to bot presets configuration")
    Permission.add("CONFIG_BOT_PRESET_CREATE", "Config bot preset create", "Create bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_UPDATE", "Config bot preset update", "Update bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_DELETE", "Config bot preset delete", "Delete bot preset configuration")
