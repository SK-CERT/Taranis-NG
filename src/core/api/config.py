"""Configuration module API."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_restful import Api

import io
from http import HTTPStatus

import requests
from auth import saml_authenticator, saml_federation, saml_metadata
from auth import url_guard as saml_url_guard
from flask import request, send_file
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from managers import (
    auth_manager,
    bots_manager,
    collectors_manager,
    external_auth_manager,
    log_manager,
    presenters_manager,
    publishers_manager,
    remote_manager,
)
from managers.auth_manager import auth_required, get_user_from_jwt
from managers.db_manager import db
from managers.sse_manager import sse_manager
from model import (
    acl_entry,
    ai_provider,
    attribute,
    auth_provider,
    bot_preset,
    bots_node,
    collectors_node,
    data_provider,
    organization,
    osint_source,
    presenters_node,
    product_type,
    public_web,
    public_web_node,
    publisher_preset,
    publishers_node,
    remote,
    report_item_type,
    role,
    security_settings,
    setting,
    user,
    word_list,
)
from model.news_item import NewsItemAggregate
from model.permission import Permission
from model.state import StateDefinition, StateEntityType
from shared.schema.ai_provider import AiProviderSchema
from shared.schema.auth_provider import AuthProviderSchema
from shared.schema.data_provider import DataProviderSchema
from shared.schema.role import PermissionSchema
from shared.schema.security_settings import SecuritySettingsSchema
from shared.schema.state import StateDefinitionSchema, StateEntityTypeSchema

# Fetching an admin-supplied metadata URL is a server-side request: keep it tight.
SAML_METADATA_TIMEOUT = 10
SAML_METADATA_MAX_BYTES = 2 * 1024 * 1024


class DictionariesReloadResource(Resource):
    """Dictionaries reload API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def get(self, dictionary_type: str) -> tuple[str, HTTPStatus]:
        """Reload dictionaries.

        Args:
            dictionary_type (str): The dictionary type
        Returns:
            (str, int): The result of the reload
        """
        attribute.Attribute.load_dictionaries(dictionary_type)
        return "success", HTTPStatus.OK


class AttributesResource(Resource):
    """Attributes API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all attributes.

        Returns:
            (dict): The attributes
        """
        search = request.args.get("search")
        return attribute.Attribute.get_all_json(search)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self) -> tuple[dict, int] | None:
        """Create an attribute.

        Returns:
            (str, int): The result of the create
        """
        try:
            attribute.Attribute.add_attribute(request.json)
        except Exception as ex:
            msg = "Could not create attribute"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AttributeResource(Resource):
    """Attribute API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id: int) -> tuple[dict, int]:
        """Update an attribute.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (str, int): The result of the update
        """
        try:
            attribute.Attribute.update(attribute_id, request.json)
        except Exception as ex:
            msg = "Could not update attribute"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an attribute.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return attribute.Attribute.delete_attribute(attribute_id)
        except Exception as ex:
            msg = "Could not delete attribute"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AttributeEnumsResource(Resource):
    """Attribute enums API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_ACCESS")
    def get(self, attribute_id: int) -> tuple[str, dict]:
        """Get all attribute enums.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (dict): The attribute enums
        """
        search = request.args.get("search")
        offset = request.args.get("offset", 0)
        limit = request.args.get("limit", 10)
        return attribute.AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)

    @auth_required("CONFIG_ATTRIBUTE_CREATE")
    def post(self, attribute_id: int) -> tuple[dict, HTTPStatus] | None:
        """Create an attribute enum.

        Args:
            attribute_id (int): The attribute ID
        Returns:
            (str, int): The result of the create
        """
        try:
            attribute.AttributeEnum.add(attribute_id, request.json)
        except Exception as ex:
            msg = "Could not create attribute enum"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AttributeEnumResource(Resource):
    """Attribute enum API endpoint."""

    @auth_required("CONFIG_ATTRIBUTE_UPDATE")
    def put(self, attribute_id: int, enum_id: int) -> tuple[dict, HTTPStatus] | None:  # noqa: ARG002
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
            msg = "Could not update attribute enum"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_ATTRIBUTE_DELETE")
    def delete(self, attribute_id: int, enum_id: int) -> tuple[dict, HTTPStatus] | None:  # noqa: ARG002
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
            msg = "Could not delete attribute enum"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AiProvidersResource(Resource):
    """AI models API endpoint."""

    @auth_required("CONFIG_AI_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all local AI models.

        Returns:
            (dict): The AI models
        """
        search = request.args.get("search")
        return ai_provider.AiProvider.get_all_json(search)

    @auth_required("CONFIG_AI_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Create an local AI model.

        Returns:
            (str, int): The result of the create
        """
        try:
            user = auth_manager.get_user_from_jwt()
            record = ai_provider.AiProvider.add_new(request.json, user.name)
            schema = AiProviderSchema()
            return schema.dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = "Could not create AI model"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AiProviderResource(Resource):
    """AI model API endpoint."""

    @auth_required("CONFIG_AI_UPDATE")
    def put(self, ai_provider_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update an local AI model.

        Args:
            ai_provider_id (int): The AI model ID
        Returns:
            (str, int): The result of the update
        """
        try:
            user = auth_manager.get_user_from_jwt()
            record = ai_provider.AiProvider.update(ai_provider_id, request.json, user.name)
            schema = AiProviderSchema()
            return schema.dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = "Could not update AI model"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_AI_DELETE")
    def delete(self, ai_provider_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an local AI model.

        Args:
            ai_provider_id (int): The AI model ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return ai_provider.AiProvider.delete(ai_provider_id)
        except Exception as ex:
            msg = "Could not delete AI model"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AuthProvidersResource(Resource):
    """Authentication providers API endpoint."""

    @auth_required("CONFIG_AUTH_PROVIDER_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all authentication providers (secrets are never returned).

        Returns:
            (dict): The authentication providers
        """
        search = request.args.get("search")
        return auth_provider.AuthProvider.get_all_json(search)

    @auth_required("CONFIG_AUTH_PROVIDER_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Create an authentication provider.

        Returns:
            (str, int): The result of the create
        """
        try:
            user_object = auth_manager.get_user_from_jwt()
            record = auth_provider.AuthProvider.add_new(request.json, user_object.name)
            schema = AuthProviderSchema()
            return schema.dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = f"Could not create authentication provider: {ex}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class AuthProviderResource(Resource):
    """Authentication provider API endpoint."""

    @auth_required("CONFIG_AUTH_PROVIDER_UPDATE")
    def put(self, auth_provider_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update an authentication provider (an empty secret keeps the stored one).

        Args:
            auth_provider_id (int): The authentication provider ID
        Returns:
            (str, int): The result of the update
        """
        try:
            user_object = auth_manager.get_user_from_jwt()
            record = auth_provider.AuthProvider.update(auth_provider_id, request.json, user_object.name)
            schema = AuthProviderSchema()
            return schema.dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = f"Could not update authentication provider: {ex}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_AUTH_PROVIDER_DELETE")
    def delete(self, auth_provider_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an authentication provider (identity links are removed with it).

        Args:
            auth_provider_id (int): The authentication provider ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return auth_provider.AuthProvider.delete(auth_provider_id)
        except Exception as ex:
            msg = "Could not delete authentication provider"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


def _read_idp_metadata_xml(data: dict) -> str:
    """Return the IdP metadata XML from the request payload, fetching it when a URL is given.

    Args:
        data (dict): The request payload with either "xml" or "url".

    Returns:
        str: The metadata XML document.

    Raises:
        ValueError: If neither is provided, the URL is not http(s), points at a
            non-public host, or the document is too large.
    """
    xml = data.get("xml")
    url = (data.get("url") or "").strip()
    if url:
        # Rejects http(s)-only and, crucially, non-public hosts: this endpoint
        # reflects the fetched document back, so an unguarded fetch is an SSRF.
        saml_url_guard.assert_public_url(url)
        response = requests.get(url, timeout=SAML_METADATA_TIMEOUT, stream=True)
        response.raise_for_status()
        xml = response.raw.read(SAML_METADATA_MAX_BYTES + 1, decode_content=True).decode("utf-8", errors="replace")
        if len(xml.encode()) > SAML_METADATA_MAX_BYTES:
            msg = "The metadata document is too large"
            raise ValueError(msg)
    if not xml:
        msg = "Provide the metadata URL or the metadata XML"
        raise ValueError(msg)
    return xml


class SamlMetadataImportResource(Resource):
    """Read the SAML provider settings out of an identity provider's metadata."""

    @auth_required("CONFIG_AUTH_PROVIDER_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Extract entityID, SSO URL and signing certificate(s) from IdP metadata.

        Accepts the metadata document itself ("xml") or a URL to fetch it from
        ("url"). Nothing is stored - the values are handed back for the admin to
        review and save.

        Returns:
            (dict, int): The extracted provider settings, or an error.
        """
        try:
            xml = _read_idp_metadata_xml(request.json or {})
            settings = saml_metadata.parse_idp_metadata(xml)
            # fail here rather than at the first login if the certificates are unusable
            settings["certificate_count"] = len(saml_authenticator.load_idp_certificates(settings["idp_certificate"]))
            return settings, HTTPStatus.OK
        except ValueError as ex:
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        except Exception as ex:
            msg = f"The metadata could not be read: {ex}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class SamlKeypairResource(Resource):
    """Generate the service provider keypair an identity provider encrypts assertions to."""

    @auth_required("CONFIG_AUTH_PROVIDER_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Generate an SP keypair.

        Nothing is stored: the private key and certificate are handed back for the
        admin to review and save with the provider. The certificate is the value a
        federation's "encryption certificate" field wants.

        Returns:
            (dict, int): The generated private_key and certificate (PEM).
        """
        entity_id = (request.json or {}).get("sp_entity_id") or "taranis-ng"
        return saml_authenticator.generate_sp_keypair(entity_id), HTTPStatus.OK


class SamlFederationVerifyResource(Resource):
    """Fetch and signature-verify a SAML federation's metadata for the admin preview."""

    @auth_required("CONFIG_AUTH_PROVIDER_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Verify federation metadata and report the resolvable identity providers.

        Accepts ``federation_metadata_url`` and ``federation_metadata_cert``.
        Nothing is stored: the metadata is fetched, its signature verified against
        the given trust anchor, and the number of usable identity providers (plus
        the document's validUntil) handed back so the admin can confirm the URL and
        anchor before saving.

        Returns:
            (dict, int): ``entity_count`` and ``valid_until``, or an error.
        """
        data = request.json or {}
        try:
            result = saml_federation.verify_metadata(
                data.get("federation_metadata_url", ""),
                data.get("federation_metadata_cert", ""),
            )
            return result, HTTPStatus.OK
        except ValueError as ex:
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        except Exception as ex:
            msg = f"The federation metadata could not be verified: {ex}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class SecuritySettingsResource(Resource):
    """Site-wide security settings API endpoint (WebAuthn relying party)."""

    @auth_required("CONFIG_AUTH_PROVIDER_ACCESS")
    def get(self) -> tuple[dict, HTTPStatus]:
        """Get the security settings.

        Returns:
            (dict): The security settings
        """
        return security_settings.SecuritySettings.get_json(), HTTPStatus.OK

    @auth_required("CONFIG_AUTH_PROVIDER_UPDATE")
    def put(self) -> tuple[dict, HTTPStatus]:
        """Update the security settings.

        Returns:
            (str, int): The result of the update
        """
        try:
            user_object = auth_manager.get_user_from_jwt()
            record = security_settings.SecuritySettings.update(request.json, user_object.name)
            return SecuritySettingsSchema().dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = f"Could not update security settings: {ex}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class DataProviderResource(Resource):
    """Data provider API endpoint."""

    @auth_required("CONFIG_DATA_PROVIDER_UPDATE")
    def put(self, data_provider_id: int) -> tuple[dict, int]:
        """Update a data provider.

        Args:
            data_provider_id (int): The data provider ID
        Returns:
            (dict, int): The result of the update
        """
        try:
            user = auth_manager.get_user_from_jwt()
            record = data_provider.DataProvider.update(data_provider_id, request.json, user.name)
            schema = DataProviderSchema()
            return schema.dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = "Could not update data provider"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_DATA_PROVIDER_DELETE")
    def delete(self, data_provider_id: int) -> tuple[dict, int] | None:
        """Delete a data provider.

        Args:
            data_provider_id (int): The data provider ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return data_provider.DataProvider.delete(data_provider_id)
        except Exception as ex:
            msg = "Could not delete data provider"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class DataProvidersResource(Resource):
    """Data provider API endpoint."""

    @auth_required("CONFIG_DATA_PROVIDER_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all data providers.

        Returns:
            (dict): The data providers
        """
        search = request.args.get("search")
        return data_provider.DataProvider.get_all_json(search)

    @auth_required("CONFIG_DATA_PROVIDER_CREATE")
    def post(self) -> tuple[dict, int] | None:
        """Create a data provider.

        Returns:
            (str, int): The result of the create
        """
        try:
            user = auth_manager.get_user_from_jwt()
            record = data_provider.DataProvider.add_new(request.json, user.name)
            schema = DataProviderSchema()
            return schema.dump(record), HTTPStatus.OK
        except Exception as ex:
            msg = "Could not create data provider"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ReportItemTypesConfigResource(Resource):
    """Report item types API endpoint."""

    @auth_required("CONFIG_REPORT_TYPE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all report item types.

        Returns:
            (dict): The report item types
        """
        search = request.args.get("search")
        return report_item_type.ReportItemType.get_all_json(search, auth_manager.get_user_from_jwt(), acl_check=False)

    @auth_required("CONFIG_REPORT_TYPE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a report item type.

        Returns:
            (str, int): The result of the create
        """
        try:
            report_item_type.ReportItemType.add_report_item_type(request.json)
        except Exception as ex:
            msg = "Could not create report type"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ReportItemTypeResource(Resource):
    """Report item type API endpoint."""

    @auth_required("CONFIG_REPORT_TYPE_UPDATE")
    def put(self, type_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a report item type.

        Args:
            type_id (int): The report item type ID
        Returns:
            (str, int): The result of the update
        """
        try:
            report_item_type.ReportItemType.update(type_id, request.json)
        except Exception as ex:
            msg = "Could not update report type"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_REPORT_TYPE_DELETE")
    def delete(self, type_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a report item type.

        Args:
            type_id (int): The report item type ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return report_item_type.ReportItemType.delete_report_item_type(type_id)
        except Exception as ex:
            msg = "Could not delete report type"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ProductTypesResource(Resource):
    """Product types API endpoint."""

    @auth_required("CONFIG_PRODUCT_TYPE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all product types.

        Returns:
            (dict): The product types
        """
        search = request.args.get("search")
        return product_type.ProductType.get_all_json(search, auth_manager.get_user_from_jwt(), acl_check=False)

    @auth_required("CONFIG_PRODUCT_TYPE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a product type.

        Returns:
            (str, int): The result of the create
        """
        try:
            product_type.ProductType.add_new(request.json)
        except Exception as ex:
            msg = "Could not create product type"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ProductTypeResource(Resource):
    """Product type API endpoint."""

    @auth_required("CONFIG_PRODUCT_TYPE_UPDATE")
    def put(self, type_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a product type.

        Args:
            type_id (int): The product type ID
        Returns:
            (str, int): The result of the update
        """
        try:
            product_type.ProductType.update(type_id, request.json)
        except Exception as ex:
            msg = "Could not update product type"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PRODUCT_TYPE_DELETE")
    def delete(self, type_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a product type.

        Args:
            type_id (int): The product type ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return product_type.ProductType.delete(type_id)
        except Exception as ex:
            msg = "Could not delete product type"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PermissionsResource(Resource):
    """Permissions API endpoint."""

    @auth_required("CONFIG_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all permissions.

        Returns:
            (dict): The permissions
        """
        search = request.args.get("search")
        return Permission.get_all_json(search)


class ExternalPermissionsResource(Resource):
    """External permissions API endpoint."""

    @auth_required("MY_ASSETS_CONFIG")
    def get(self) -> tuple[dict, dict]:
        """Get all external permissions.

        Returns:
            (dict): The external permissions
        """
        permissions = auth_manager.get_external_permissions()
        permissions_schema = PermissionSchema(many=True)
        return {"total_count": len(permissions), "items": permissions_schema.dump(permissions)}


class RolesResource(Resource):
    """Roles API endpoint."""

    @auth_required("CONFIG_ROLE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all roles.

        Returns:
            (dict): The roles
        """
        search = request.args.get("search")
        return role.Role.get_all_json(search)

    @auth_required("CONFIG_ROLE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a role.

        Returns:
            (str, int): The result of the create
        """
        try:
            role.Role.add_new(request.json)
        except Exception as ex:
            msg = "Could not create role"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class RoleResource(Resource):
    """Role API endpoint."""

    @auth_required("CONFIG_ROLE_UPDATE")
    def put(self, role_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a role.

        Args:
            role_id (int): The role ID
        Returns:
            (str, int): The result of the update
        """
        try:
            role.Role.update(role_id, request.json)
        except Exception as ex:
            msg = "Could not update role"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_ROLE_DELETE")
    def delete(self, role_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a role.

        Args:
            role_id (int): The role ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return role.Role.delete(role_id)
        except Exception as ex:
            msg = "Could not delete role"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ACLEntriesResource(Resource):
    """ACL entries API endpoint."""

    @auth_required("CONFIG_ACL_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all ACL entries.

        Returns:
            (dict): The ACL entries
        """
        search = request.args.get("search")
        return acl_entry.ACLEntry.get_all_json(search)

    @auth_required("CONFIG_ACL_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create an ACL entry.

        Returns:
            (str, int): The result of the create
        """
        try:
            acl_entry.ACLEntry.add_new(request.json)
        except Exception as ex:
            msg = "Could not create acl entry"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ACLEntryResource(Resource):
    """ACL entry API endpoint."""

    @auth_required("CONFIG_ACL_UPDATE")
    def put(self, acl_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update an ACL entry.

        Args:
            acl_id (int): The ACL entry ID
        Returns:
            (str, int): The result of the update
        """
        try:
            acl_entry.ACLEntry.update(acl_id, request.json)
        except Exception as ex:
            msg = "Could not update acl entry"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_ACL_DELETE")
    def delete(self, acl_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an ACL entry.

        Args:
            acl_id (int): The ACL entry ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return acl_entry.ACLEntry.delete(acl_id)
        except Exception as ex:
            msg = "Could not delete acl entry"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OrganizationsResource(Resource):
    """Organizations API endpoint."""

    @auth_required("CONFIG_ORGANIZATION_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all organizations.

        Returns:
            (dict): The organizations
        """
        search = request.args.get("search")
        return organization.Organization.get_all_json(search)

    @auth_required("CONFIG_ORGANIZATION_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create an organization.

        Returns:
            (str, int): The result of the create
        """
        try:
            organization.Organization.add_new(request.json)
        except Exception as ex:
            msg = "Could not create organization"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OrganizationResource(Resource):
    """Organization API endpoint."""

    @auth_required("CONFIG_ORGANIZATION_UPDATE")
    def put(self, organization_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update an organization.

        Args:
            organization_id (int): The organization ID
        Returns:
            (str, int): The result of the update
        """
        try:
            organization.Organization.update(organization_id, request.json)
        except Exception as ex:
            msg = "Could not update organization"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_ORGANIZATION_DELETE")
    def delete(self, organization_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an organization.

        Args:
            organization_id (int): The organization ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return organization.Organization.delete(organization_id)
        except Exception as ex:
            msg = "Could not delete organization"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class UsersResource(Resource):
    """Users API endpoint."""

    @auth_required("CONFIG_USER_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all users.

        Returns:
            (dict): The users
        """
        search = request.args.get("search")
        return user.User.get_all_json(search)

    @auth_required("CONFIG_USER_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a user.

        Returns:
            (str, int): The result of the create
        """
        try:
            external_auth_manager.create_user(request.json)
        except Exception as ex:
            msg = "Could not create user in external auth system"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

        try:
            user.User.add_new(request.json)
        except ValueError as ex:
            # a rejected identity link or status change: the message names what to fix
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        return None


class UserResource(Resource):
    """User API endpoint."""

    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id: int) -> tuple[dict, HTTPStatus] | None:
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
            msg = "Could not update user in external auth system"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

        try:
            user.User.update(user_id, request.json)
        except ValueError as ex:
            # a rejected identity link or status change: the message names what to fix
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        return None

    @auth_required("CONFIG_USER_DELETE")
    def delete(self, user_id: int) -> tuple[dict, HTTPStatus] | None:
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
            msg = "Could not delete user in external auth system"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class UserStatusResource(Resource):
    """User account status API endpoint (approve / disable / re-enable)."""

    @auth_required("CONFIG_USER_UPDATE")
    def put(self, user_id: int) -> tuple[dict, HTTPStatus]:
        """Set a user's account status.

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the status change
        """
        try:
            updated_user = user.User.set_status(user_id, (request.json or {}).get("status", ""))
            log_manager.store_user_activity(get_user_from_jwt(), "USER_STATUS", f"User {updated_user.username} set to {updated_user.status}")
            return {"status": updated_user.status}, HTTPStatus.OK
        except Exception as ex:
            msg = f"Could not change user status: {ex}"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class UserMfaResetResource(Resource):
    """Admin MFA reset API endpoint (recovery when a user loses their second factor)."""

    @auth_required("CONFIG_USER_UPDATE")
    def post(self, user_id: int) -> tuple[dict, HTTPStatus]:
        """Reset a user's MFA enrollments (TOTP and/or passkeys).

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the reset
        """
        try:
            data = request.json or {}
            user.User.reset_mfa(user_id, reset_totp=data.get("reset_totp", True), reset_passkeys=data.get("reset_passkeys", True))
            log_manager.store_user_activity(get_user_from_jwt(), "USER_MFA_RESET", f"MFA reset for user id {user_id}")
            return {}, HTTPStatus.OK
        except Exception as ex:
            msg = "Could not reset user MFA"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ExternalUsersResource(Resource):
    """External users API endpoint."""

    @auth_required("MY_ASSETS_CONFIG")
    def get(self) -> tuple[str, dict]:
        """Get all external users.

        Returns:
            (dict): The external users
        """
        search = request.args.get("search")
        return user.User.get_all_external_json(auth_manager.get_user_from_jwt(), search)

    @auth_required("MY_ASSETS_CONFIG")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create an external user.

        Returns:
            (str, int): The result of the create
        """
        try:
            permissions = auth_manager.get_external_permissions_ids()
            user.User.add_new_external(auth_manager.get_user_from_jwt(), permissions, request.json)
        except Exception as ex:
            msg = "Could not create external user"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class ExternalUserResource(Resource):
    """External user API endpoint."""

    @auth_required("MY_ASSETS_CONFIG")
    def put(self, user_id: int) -> tuple[dict, HTTPStatus] | None:
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
            msg = "Could not update external user"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("MY_ASSETS_CONFIG")
    def delete(self, user_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an external user.

        Args:
            user_id (int): The user ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return user.User.delete_external(auth_manager.get_user_from_jwt(), user_id)
        except Exception as ex:
            msg = "Could not delete external user"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class SettingsResource(Resource):
    """Settings API endpoint."""

    @jwt_required()
    def get(self) -> tuple[str, dict]:
        """Get all global settings.

        Returns:
            (dict): The Settings
        """
        search = request.args.get("search")
        user = auth_manager.get_user_from_jwt()
        return setting.Setting.get_all_json(user, search)


class SettingResource(Resource):
    """Settings API endpoint."""

    @auth_required("CONFIG_SETTINGS_UPDATE")
    def put(self, setting_id: int) -> tuple[dict, HTTPStatus]:
        """Update a global setting.

        Parameters:
            setting_id (int): The setting ID
        Returns:
            (str, int): The result of the update
        """
        try:
            user = auth_manager.get_user_from_jwt()
            setting.Setting.update_value(setting_id, user.name, request.json)
            json = setting.Setting.get_all_json(user, "")
            return json, HTTPStatus.OK
        except Exception as ex:
            msg = "Could not update global setting"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class UserSettingResource(Resource):
    """Settings API endpoint."""

    @jwt_required()
    def put(self, setting_id: int) -> tuple[dict, HTTPStatus]:
        """Update a user setting.

        Parameters:
            user_setting_id (int): The user setting ID
        Returns:
            (str, int): The result of the update
        """
        msg = "Could not update user setting"
        try:
            user = auth_manager.get_user_from_jwt()
            if not setting.SettingUser.update_value(setting_id, user.id, request.json):
                return {"error": msg}, HTTPStatus.BAD_REQUEST
            json = setting.Setting.get_all_json(user, "")
            return json, HTTPStatus.OK
        except Exception as ex:
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class WordListsResource(Resource):
    """Word lists API endpoint."""

    @auth_required("CONFIG_WORD_LIST_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all word lists.

        Returns:
            (dict): The word lists
        """
        search = request.args.get("search")
        return word_list.WordList.get_all_json(search, auth_manager.get_user_from_jwt(), acl_check=False)

    @auth_required("CONFIG_WORD_LIST_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a word list.

        Returns:
            (str, int): The result of the create
        """
        try:
            word_list.WordList.add_new(request.json)
        except Exception as ex:
            msg = "Could not create word list"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class WordListResource(Resource):
    """Word list API endpoint."""

    @auth_required("CONFIG_WORD_LIST_DELETE")
    def delete(self, word_list_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a word list.

        Args:
            word_list_id (int): The word list ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return word_list.WordList.delete(word_list_id)
        except Exception as ex:
            msg = "Could not delete word list"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_WORD_LIST_UPDATE")
    def put(self, word_list_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a word list.

        Args:
            word_list_id (int): The word list ID
        Returns:
            (str, int): The result of the update
        """
        try:
            word_list.WordList.update(word_list_id, request.json)
        except Exception as ex:
            msg = "Could not update word list"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class CollectorsNodesResource(Resource):
    """Collectors nodes API endpoint."""

    @auth_required("CONFIG_COLLECTORS_NODE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all collectors nodes.

        Returns:
            (dict): The collectors nodes
        """
        search = request.args.get("search")
        return collectors_node.CollectorsNode.get_all_json(search)

    @auth_required("CONFIG_COLLECTORS_NODE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a collectors node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", collectors_manager.add_collectors_node(request.json)
        except Exception as ex:
            msg = "Could not create collectors node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class CollectorsNodeResource(Resource):
    """Collectors node API endpoint."""

    @auth_required("CONFIG_COLLECTORS_NODE_UPDATE")
    def put(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a collectors node.

        Args:
            node_id (int): The collectors node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            collectors_manager.update_collectors_node(node_id, request.json)
        except Exception as ex:
            msg = "Could not update collectors node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_COLLECTORS_NODE_DELETE")
    def delete(self, node_id: int) -> tuple[dict, HTTPStatus]:
        """Delete a collectors node.

        Args:
            node_id (int): The collectors node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return collectors_node.CollectorsNode.delete(node_id)
        except Exception as ex:
            msg = "Could not delete collectors node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OSINTSourcesResource(Resource):
    """OSINT sources API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all OSINT sources.

        Returns:
            (dict): The OSINT sources
        """
        search = request.args.get("search")
        return osint_source.OSINTSource.get_all_json(search)

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create an OSINT source.

        Returns:
            (str, int): The result of the create
        """
        try:
            collectors_manager.add_osint_source(request.json)
        except Exception as ex:
            msg = "Could not create OSINT source"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OSINTSourceResource(Resource):
    """OSINT source API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_UPDATE")
    def put(self, source_id: int) -> tuple[dict, HTTPStatus] | None:
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
            msg = "Could not update OSINT source"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_OSINT_SOURCE_DELETE")
    def delete(self, source_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an OSINT source.

        Args:
            source_id (int): The OSINT source ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            collectors_manager.delete_osint_source(source_id)
        except Exception as ex:
            msg = "Could not delete OSINT source"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OSINTSourcesExportResource(Resource):
    """OSINT sources export API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_ACCESS")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Export OSINT sources.

        Returns:
            (str, int): The result of the export
        """
        try:
            data = collectors_manager.export_osint_sources(request.json)
            return send_file(io.BytesIO(data), download_name="osint_sources_export.json", mimetype="application/json", as_attachment=True)
        except Exception as ex:
            msg = "Could not export OSINT source"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OSINTSourcesImportResource(Resource):
    """OSINT sources import API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
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
            msg = "Could not import OSINT source"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OSINTSourceGroupsResource(Resource):
    """OSINT source groups API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all OSINT source groups.

        Returns:
            (dict): The OSINT source groups
        """
        search = request.args.get("search")
        return osint_source.OSINTSourceGroup.get_all_json(search, auth_manager.get_user_from_jwt(), acl_check=False)

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create an OSINT source group.

        Returns:
            (str, int): The result of the create
        """
        try:
            osint_source.OSINTSourceGroup.add(request.json)
        except Exception as ex:
            msg = "Could not create OSINT source group"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class OSINTSourceGroupResource(Resource):
    """OSINT source group API endpoint."""

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_UPDATE")
    def put(self, group_id: int) -> tuple[dict, HTTPStatus]:
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
            msg = "Could not update OSINT source group"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_OSINT_SOURCE_GROUP_DELETE")
    def delete(self, group_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete an OSINT source group.

        Args:
            group_id (int): The OSINT source group ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return osint_source.OSINTSourceGroup.delete(group_id)
        except Exception as ex:
            msg = "Could not delete OSINT source group"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class RemoteAccessesResource(Resource):
    """Remote accesses API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all remote accesses.

        Returns:
            (dict): The remote accesses
        """
        search = request.args.get("search")
        return remote.RemoteAccess.get_all_json(search)

    @auth_required("CONFIG_REMOTE_ACCESS_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a remote access.

        Returns:
            (str, int): The result of the create
        """
        try:
            remote.RemoteAccess.add(request.json)
        except Exception as ex:
            msg = "Could not create remote access"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class RemoteAccessResource(Resource):
    """Remote access API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_UPDATE")
    def put(self, remote_access_id: int) -> tuple[dict, HTTPStatus] | None:
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
            msg = "Could not update remote access"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_REMOTE_ACCESS_DELETE")
    def delete(self, remote_access_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a remote access.

        Args:
            remote_access_id (int): The remote access ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return remote.RemoteAccess.delete(remote_access_id)
        except Exception as ex:
            msg = "Could not delete remote access"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublicWebNodesResource(Resource):
    """Public-web nodes API endpoint."""

    @auth_required("CONFIG_PUBLIC_WEB_NODE_ACCESS")
    def get(self) -> dict:
        """Get all public-web nodes.

        Returns:
            (dict): The public-web nodes
        """
        search = request.args.get("search")
        return public_web_node.PublicWebNode.get_all_json(search)

    @auth_required("CONFIG_PUBLIC_WEB_NODE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a public-web node.

        Returns:
            (str, int): The result of the create
        """
        try:
            public_web_node.PublicWebNode.add(request.json)
        except Exception as ex:
            msg = "Could not create public-web node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublicWebNodeResource(Resource):
    """Public-web node API endpoint."""

    @auth_required("CONFIG_PUBLIC_WEB_NODE_UPDATE")
    def put(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a public-web node.

        Args:
            node_id (int): The public-web node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            public_web_node.PublicWebNode.update(node_id, request.json)
        except Exception as ex:
            msg = "Could not update public-web node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PUBLIC_WEB_NODE_DELETE")
    def delete(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a public-web node.

        Args:
            node_id (int): The public-web node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return public_web_node.PublicWebNode.delete(node_id)
        except Exception as ex:
            msg = "Could not delete public-web node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


def _notify_public_web_node(node_id: int) -> None:
    """Best-effort: push a cache reset to the node so a config change shows now.

    Never raises — a down/unreachable node just means the change appears after the
    node's cache TTL instead of immediately.
    """
    try:
        node = db.session.get(public_web_node.PublicWebNode, node_id)
        if node and node.api_url:
            from remote.public_web_api import PublicWebApi  # noqa: PLC0415 (avoid import cycle at load)

            PublicWebApi(node.api_url, node.api_key).reset_cache()
    except Exception as ex:
        log_manager.store_data_error_activity(get_user_from_jwt(), "Could not notify public-web node", ex)


class PublicWebsResource(Resource):
    """The webs (branded feeds) hosted by a public-web node."""

    @auth_required("CONFIG_PUBLIC_WEB_NODE_ACCESS")
    def get(self, node_id: int) -> dict:
        """Get all webs of a public-web node.

        Args:
            node_id (int): The public-web node ID
        Returns:
            (dict): The webs
        """
        search = request.args.get("search")
        return public_web.PublicWeb.get_all_json_for_node(node_id, search)

    @auth_required("CONFIG_PUBLIC_WEB_NODE_CREATE")
    def post(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Create a web under a public-web node.

        Args:
            node_id (int): The public-web node ID
        Returns:
            (dict, int): The id of the created web
        """
        try:
            web = public_web.PublicWeb.add(node_id, request.json)
            _notify_public_web_node(node_id)
            return {"id": web.id}, HTTPStatus.OK
        except Exception as ex:
            msg = "Could not create public web"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublicWebResource(Resource):
    """A single web of a public-web node."""

    @auth_required("CONFIG_PUBLIC_WEB_NODE_UPDATE")
    def put(self, node_id: int, web_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a web.

        Args:
            node_id (int): The public-web node ID
            web_id (int): The web ID
        """
        try:
            public_web.PublicWeb.update(web_id, request.json)
            _notify_public_web_node(node_id)
        except Exception as ex:
            msg = "Could not update public web"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PUBLIC_WEB_NODE_DELETE")
    def delete(self, node_id: int, web_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a web.

        Args:
            node_id (int): The public-web node ID
            web_id (int): The web ID
        """
        try:
            result = public_web.PublicWeb.delete(web_id)
            _notify_public_web_node(node_id)
            return result
        except Exception as ex:
            msg = "Could not delete public web"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublicWebImageResource(Resource):
    """Upload / preview / remove one image (logo, favicon, preview) of a web."""

    @auth_required("CONFIG_PUBLIC_WEB_NODE_ACCESS")
    def get(self, node_id: int, web_id: int, kind: str):  # noqa: ANN201, ARG002
        """Serve the image binary for previewing in the configuration UI."""
        web = public_web.PublicWeb.find(web_id)
        image = web.get_image(kind) if web else None
        if image is None or image.data is None:
            return {"error": "Image not found"}, HTTPStatus.NOT_FOUND
        return send_file(io.BytesIO(image.data), mimetype=image.mime_type, download_name=image.filename or kind)

    @auth_required("CONFIG_PUBLIC_WEB_NODE_UPDATE")
    def post(self, node_id: int, web_id: int, kind: str) -> tuple[dict, HTTPStatus] | None:
        """Upload (create/replace) an image of the given kind."""
        try:
            if kind not in public_web.IMAGE_KINDS:
                return {"error": "Invalid image kind"}, HTTPStatus.BAD_REQUEST
            web = public_web.PublicWeb.find(web_id)
            if web is None:
                return {"error": "Web not found"}, HTTPStatus.NOT_FOUND
            file = request.files.get("file")
            if not file:
                return {"error": "No file provided"}, HTTPStatus.BAD_REQUEST
            web.set_image(kind, file.mimetype, file.filename, file.read())
            _notify_public_web_node(node_id)
        except Exception as ex:
            msg = "Could not upload public web image"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PUBLIC_WEB_NODE_UPDATE")
    def delete(self, node_id: int, web_id: int, kind: str) -> tuple[dict, HTTPStatus] | None:
        """Remove an image of the given kind."""
        try:
            web = public_web.PublicWeb.find(web_id)
            if web is not None:
                web.remove_image(kind)
            _notify_public_web_node(node_id)
        except Exception as ex:
            msg = "Could not delete public web image"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublicWebEmailTestResource(Resource):
    """Send a test e-mail via a public-web node using provided SMTP settings."""

    @auth_required("CONFIG_PUBLIC_WEB_NODE_UPDATE")
    def post(self, node_id: int) -> tuple[dict, HTTPStatus]:
        """Send a test e-mail through the given public-web node.

        The payload is forwarded to the node management API without persistence,
        so admins can validate SMTP credentials/settings before saving a web.
        """
        try:
            node = db.session.get(public_web_node.PublicWebNode, node_id)
            if node is None:
                return {"error": "Public-web node not found"}, HTTPStatus.NOT_FOUND
            if not node.api_url:
                return {"error": "Public-web node API URL is not configured"}, HTTPStatus.BAD_REQUEST

            from remote.public_web_api import PublicWebApi  # noqa: PLC0415

            payload = request.json if isinstance(request.json, dict) else {}
            body, status = PublicWebApi(node.api_url, node.api_key).test_email(payload)
            return body, status
        except Exception as ex:
            msg = "Could not send public-web test e-mail"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class RemoteNodesResource(Resource):
    """Remote nodes API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all remote nodes.

        Returns:
            (dict): The remote nodes
        """
        search = request.args.get("search")
        return remote.RemoteNode.get_all_json(search)

    @auth_required("CONFIG_REMOTE_ACCESS_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a remote node.

        Returns:
            (str, int): The result of the create
        """
        try:
            remote.RemoteNode.add(request.json)
        except Exception as ex:
            msg = "Could not create remote node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class RemoteNodeResource(Resource):
    """Remote node API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_UPDATE")
    def put(self, remote_node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a remote node.

        Args:
            remote_node_id (int): The remote node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            if remote.RemoteNode.update(remote_node_id, request.json) is False:
                remote_manager.disconnect_from_node(remote_node_id)
        except Exception as ex:
            msg = "Could not update remote node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_REMOTE_ACCESS_DELETE")
    def delete(self, remote_node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a remote node.

        Args:
            remote_node_id (int): The remote node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            remote_manager.disconnect_from_node(remote_node_id)
            return remote.RemoteNode.delete(remote_node_id)
        except Exception as ex:
            msg = "Could not delete remote node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class RemoteNodeConnectResource(Resource):
    """Remote node connect API endpoint."""

    @auth_required("CONFIG_REMOTE_ACCESS_ACCESS")
    def get(self, remote_node_id: int) -> tuple[dict, HTTPStatus]:
        """Connect to a remote node.

        Args:
            remote_node_id (int): The remote node ID
        Returns:
            (str, int): The result of the connect
        """
        try:
            return remote_manager.connect_to_node(remote_node_id)
        except Exception as ex:
            msg = "Could not connect to node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PresentersNodesResource(Resource):
    """Presenters nodes API endpoint."""

    @auth_required("CONFIG_PRESENTERS_NODE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all presenters nodes.

        Returns:
            (dict): The presenters nodes
        """
        search = request.args.get("search")
        return presenters_node.PresentersNode.get_all_json(search)

    @auth_required("CONFIG_PRESENTERS_NODE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a presenters node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", presenters_manager.add_presenters_node(request.json)
        except Exception as ex:
            msg = "Could not create presenters node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PresentersNodeResource(Resource):
    """Presenters node API endpoint."""

    @auth_required("CONFIG_PRESENTERS_NODE_UPDATE")
    def put(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a presenters node.

        Args:
            node_id (int): The presenters node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            presenters_manager.update_presenters_node(node_id, request.json)
        except Exception as ex:
            msg = "Could not update presenters node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PRESENTERS_NODE_DELETE")
    def delete(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a presenters node.

        Args:
            node_id (int): The presenters node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return presenters_node.PresentersNode.delete(node_id)
        except Exception as ex:
            msg = "Could not delete presenters node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublisherNodesResource(Resource):
    """Publisher nodes API endpoint."""

    @auth_required("CONFIG_PUBLISHERS_NODE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all publisher nodes.

        Returns:
            (dict): The publisher nodes
        """
        search = request.args.get("search")
        return publishers_node.PublishersNode.get_all_json(search)

    @auth_required("CONFIG_PUBLISHERS_NODE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Create a publisher node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", publishers_manager.add_publishers_node(request.json)
        except Exception as ex:
            msg = "Could not create publishers node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublishersNodeResource(Resource):
    """Publisher node API endpoint."""

    @auth_required("CONFIG_PUBLISHERS_NODE_UPDATE")
    def put(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a publisher node.

        Args:
            node_id (int): The publisher node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            publishers_manager.update_publishers_node(node_id, request.json)
        except Exception as ex:
            msg = "Could not update publishers node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PUBLISHERS_NODE_DELETE")
    def delete(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a publisher node.

        Args:
            node_id (int): The publisher node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return publishers_node.PublishersNode.delete(node_id)
        except Exception as ex:
            msg = "Could not delete publishers node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublisherPresetsResource(Resource):
    """Publisher presets API endpoint."""

    @auth_required("CONFIG_PUBLISHER_PRESET_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all publisher presets.

        Returns:
            (dict): The publisher presets
        """
        search = request.args.get("search")
        return publisher_preset.PublisherPreset.get_all_json(search)

    @auth_required("CONFIG_PUBLISHER_PRESET_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a publisher preset.

        Returns:
            (str, int): The result of the create
        """
        try:
            publishers_manager.add_publisher_preset(request.json)
        except Exception as ex:
            msg = "Could not create publishers preset"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class PublisherPresetResource(Resource):
    """Publisher preset API endpoint."""

    @auth_required("CONFIG_PUBLISHER_PRESET_UPDATE")
    def put(self, preset_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a publisher preset.

        Args:
            preset_id (int): The publisher preset ID
        Returns:
            (str, int): The result of the update
        """
        try:
            publisher_preset.PublisherPreset.update(preset_id, request.json)
        except Exception as ex:
            msg = "Could not update publishers preset"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_PUBLISHER_PRESET_DELETE")
    def delete(self, preset_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a publisher preset.

        Args:
            preset_id (int): The publisher preset ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return publisher_preset.PublisherPreset.delete(preset_id)
        except Exception as ex:
            msg = "Could not delete publishers preset"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class BotNodesResource(Resource):
    """Bot nodes API endpoint."""

    @auth_required("CONFIG_BOTS_NODE_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all bot nodes.

        Returns:
            (dict): The bot nodes
        """
        search = request.args.get("search")
        return bots_node.BotsNode.get_all_json(search)

    @auth_required("CONFIG_BOTS_NODE_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Create a bot node.

        Returns:
            (str, int): The result of the create
        """
        try:
            return "", bots_manager.add_bots_node(request.json)
        except Exception as ex:
            msg = "Could not create bots node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class BotsNodeResource(Resource):
    """Bot node API endpoint."""

    @auth_required("CONFIG_BOTS_NODE_UPDATE")
    def put(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a bot node.

        Args:
            node_id (int): The bot node ID
        Returns:
            (str, int): The result of the update
        """
        try:
            bots_manager.update_bots_node(node_id, request.json)
        except Exception as ex:
            msg = "Could not update bots node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_BOTS_NODE_DELETE")
    def delete(self, node_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a bot node.

        Args:
            node_id (int): The bot node ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return bots_node.BotsNode.delete(node_id)
        except Exception as ex:
            msg = "Could not delete bots node"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class BotPresetsResource(Resource):
    """Bot presets API endpoint."""

    @auth_required("CONFIG_BOT_PRESET_ACCESS")
    def get(self) -> tuple[str, dict]:
        """Get all bot presets.

        Returns:
            (dict): The bot presets
        """
        search = request.args.get("search")
        return bot_preset.BotPreset.get_all_json(search)

    @auth_required("CONFIG_BOT_PRESET_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a bot preset.

        Returns:
            (str, int): The result of the create
        """
        try:
            bots_manager.add_bot_preset(request.json)
        except Exception as ex:
            msg = "Could not create bots preset"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class BotPresetResource(Resource):
    """Bot preset API endpoint."""

    @auth_required("CONFIG_BOT_PRESET_UPDATE")
    def put(self, preset_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a bot preset.

        Args:
            preset_id (int): The bot preset ID
        Returns:
            (str, int): The result of the update
        """
        try:
            bot_preset.BotPreset.update(preset_id, request.json)
        except Exception as ex:
            msg = "Could not update bots preset"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_BOT_PRESET_DELETE")
    def delete(self, preset_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a bot preset.

        Args:
            preset_id (int): The bot preset ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            return bot_preset.BotPreset.delete(preset_id)
        except Exception as ex:
            msg = "Could not delete bots preset"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class StatesResource(Resource):
    """State definitions API endpoint."""

    @auth_required("CONFIG_WORKFLOW_ACCESS")
    def get(self) -> tuple[dict, HTTPStatus]:
        """Get all state definitions.

        Returns:
            (dict): The state definitions
        """
        try:
            search = request.args["search"]
            return StateDefinition.get_all_json(search)
        except Exception as ex:
            msg = "Could not get state definitions"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_WORKFLOW_CREATE")
    def post(self) -> tuple[dict, HTTPStatus] | None:
        """Create a state definition.

        Returns:
            (str, int): The result of the create
        """
        try:
            user = auth_manager.get_user_from_jwt()
            state_def = StateDefinition.add_new(request.json, user.name)
            schema = StateDefinitionSchema()
            return schema.dump(state_def), HTTPStatus.CREATED

        except Exception as ex:
            msg = "Could not create state definition"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class StateResource(Resource):
    """State definition API endpoint."""

    @auth_required("CONFIG_WORKFLOW_UPDATE")
    def put(self, state_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a state.

        Args:
            state_id (int): The state ID
        Returns:
            (str, int): The result of the update
        """
        try:
            state_def = db.session.get(StateDefinition, state_id)
            if not state_def:
                return {"error": "State definition not found"}, HTTPStatus.NOT_FOUND

            user = auth_manager.get_user_from_jwt()
            state_def = state_def.update(request.json, user.name)
            schema = StateDefinitionSchema()
            return schema.dump(state_def), HTTPStatus.OK

        except ValueError as valerr:
            return {"error": str(valerr)}, HTTPStatus.BAD_REQUEST
        except Exception as exception:
            msg = "Could not update state definition"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, exception)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

    @auth_required("CONFIG_WORKFLOW_DELETE")
    def delete(self, state_id: int) -> tuple[dict, HTTPStatus] | None:
        """Delete a state definition.

        Args:
            state_id (int): The state definition ID
        Returns:
            (str, int): The result of the delete
        """
        try:
            state_def = db.session.get(StateDefinition, state_id)
            if not state_def:
                return {"error": "State definition not found"}, HTTPStatus.NOT_FOUND

            result, status_code = state_def.delete()
            return result, status_code

        except Exception as ex:
            msg = "Could not delete state definition"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class StateEntityTypesResource(Resource):
    """State entity type associations API endpoint."""

    @auth_required("CONFIG_WORKFLOW_ACCESS")
    def get(self) -> tuple[dict, HTTPStatus]:
        """Get all state-entity type associations.

        Returns:
            (dict, int): The state-entity type associations
        """
        try:
            entity_type = request.args.get("entity_type")
            return StateEntityType.get_all_json(entity_type)

        except Exception as ex:
            msg = "Could not get state-entity type associations"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_WORKFLOW_CREATE")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Create a state-entity type association.

        Returns:
            (dict, int): The created association
        """
        try:
            user = auth_manager.get_user_from_jwt()
            state_def = StateEntityType.add_new(request.json, user.name)
            schema = StateEntityTypeSchema()
            return schema.dump(state_def), HTTPStatus.CREATED

        except Exception as ex:
            db.session.rollback()
            msg = "Could not create state-entity type association"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


class StateEntityTypeResource(Resource):
    """State entity type association API endpoint."""

    @auth_required("CONFIG_WORKFLOW_UPDATE")
    def put(self, state_entity_type_id: int) -> tuple[dict, HTTPStatus]:
        """Update a state-entity type association.

        Args:
            state_entity_type_id (int): The association ID
        Returns:
            (dict, int): The updated association
        """
        try:
            state_type = db.session.get(StateEntityType, state_entity_type_id)
            if not state_type:
                return {"error": "State entity-type not found"}, HTTPStatus.NOT_FOUND

            if not state_type.editable:
                return {"error": "Cannot modify system state-entity type"}, HTTPStatus.FORBIDDEN

            user = auth_manager.get_user_from_jwt()
            state_type = state_type.update(request.json, user.name)
            schema = StateDefinitionSchema()
            return schema.dump(state_type), HTTPStatus.OK

        except Exception as ex:
            db.session.rollback()
            msg = "Could not update state-entity type association"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST

    @auth_required("CONFIG_WORKFLOW_DELETE")
    def delete(self, state_entity_type_id: int) -> tuple[dict, HTTPStatus]:
        """Delete a state-entity type association.

        Args:
            state_entity_type_id (int): The association ID
        Returns:
            (dict, int): The result
        """
        try:
            state_type = db.session.get(StateEntityType, state_entity_type_id)
            if not state_type:
                return {"error": "Association not found"}, HTTPStatus.NOT_FOUND

            if not state_type.editable:
                return {"error": "Cannot delete system state association"}, HTTPStatus.FORBIDDEN

            db.session.delete(state_type)
            db.session.commit()

            return {"message": "Association deleted successfully"}, HTTPStatus.OK

        except Exception as ex:
            db.session.rollback()
            msg = "Could not delete state-entity type association"
            log_manager.store_data_error_activity(get_user_from_jwt(), msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST


def initialize(api: Api) -> None:  # noqa: PLR0915
    """Initialize the API.

    Args:
        api (Flask): The Flask application
    """
    api.add_resource(DictionariesReloadResource, "/api/v1/config/reload-enum-dictionaries/<string:dictionary_type>")
    api.add_resource(AttributesResource, "/api/v1/config/attributes")
    api.add_resource(AttributeResource, "/api/v1/config/attributes/<int:attribute_id>")
    api.add_resource(AttributeEnumsResource, "/api/v1/config/attributes/<int:attribute_id>/enums")
    api.add_resource(AttributeEnumResource, "/api/v1/config/attributes/<int:attribute_id>/enums/<int:enum_id>")
    api.add_resource(AiProvidersResource, "/api/v1/config/aiproviders")
    api.add_resource(AiProviderResource, "/api/v1/config/aiprovider/<int:ai_provider_id>")
    api.add_resource(DataProvidersResource, "/api/v1/config/data-providers")
    api.add_resource(DataProviderResource, "/api/v1/config/data-provider/<int:data_provider_id>")

    api.add_resource(ReportItemTypesConfigResource, "/api/v1/config/report-item-types")
    api.add_resource(ReportItemTypeResource, "/api/v1/config/report-item-types/<int:type_id>")

    api.add_resource(ProductTypesResource, "/api/v1/config/product-types")
    api.add_resource(ProductTypeResource, "/api/v1/config/product-types/<int:type_id>")

    api.add_resource(PermissionsResource, "/api/v1/config/permissions")
    api.add_resource(ExternalPermissionsResource, "/api/v1/config/external-permissions")
    api.add_resource(RolesResource, "/api/v1/config/roles")
    api.add_resource(RoleResource, "/api/v1/config/roles/<int:role_id>")
    api.add_resource(ACLEntriesResource, "/api/v1/config/acls")
    api.add_resource(ACLEntryResource, "/api/v1/config/acls/<int:acl_id>")

    api.add_resource(OrganizationsResource, "/api/v1/config/organizations")
    api.add_resource(OrganizationResource, "/api/v1/config/organizations/<int:organization_id>")

    api.add_resource(UsersResource, "/api/v1/config/users")
    api.add_resource(UserResource, "/api/v1/config/users/<int:user_id>")
    api.add_resource(UserStatusResource, "/api/v1/config/users/<int:user_id>/status")
    api.add_resource(UserMfaResetResource, "/api/v1/config/users/<int:user_id>/reset-mfa")

    api.add_resource(AuthProvidersResource, "/api/v1/config/auth-providers")
    api.add_resource(AuthProviderResource, "/api/v1/config/auth-providers/<int:auth_provider_id>")
    api.add_resource(SamlMetadataImportResource, "/api/v1/config/auth-providers/saml/import-metadata")
    api.add_resource(SamlKeypairResource, "/api/v1/config/auth-providers/saml/generate-keypair")
    api.add_resource(SamlFederationVerifyResource, "/api/v1/config/auth-providers/saml/verify-federation")
    api.add_resource(SecuritySettingsResource, "/api/v1/config/security")

    api.add_resource(ExternalUsersResource, "/api/v1/config/external-users")
    api.add_resource(ExternalUserResource, "/api/v1/config/external-users/<int:user_id>")

    api.add_resource(SettingsResource, "/api/v1/config/settings")
    api.add_resource(SettingResource, "/api/v1/config/settings/<int:setting_id>")
    api.add_resource(UserSettingResource, "/api/v1/config/user-settings/<int:setting_id>")
    api.add_resource(WordListsResource, "/api/v1/config/word-lists")
    api.add_resource(WordListResource, "/api/v1/config/word-lists/<int:word_list_id>")

    api.add_resource(CollectorsNodesResource, "/api/v1/config/collectors-nodes")
    api.add_resource(CollectorsNodeResource, "/api/v1/config/collectors-nodes/<string:node_id>")
    api.add_resource(OSINTSourcesResource, "/api/v1/config/osint-sources")
    api.add_resource(OSINTSourceResource, "/api/v1/config/osint-sources/<string:source_id>")
    api.add_resource(OSINTSourcesExportResource, "/api/v1/config/export-osint-sources")
    api.add_resource(OSINTSourcesImportResource, "/api/v1/config/import-osint-sources")
    api.add_resource(OSINTSourceGroupsResource, "/api/v1/config/osint-source-groups")
    api.add_resource(OSINTSourceGroupResource, "/api/v1/config/osint-source-groups/<string:group_id>")

    api.add_resource(RemoteAccessesResource, "/api/v1/config/remote-accesses")
    api.add_resource(RemoteAccessResource, "/api/v1/config/remote-accesses/<int:remote_access_id>")

    api.add_resource(PublicWebNodesResource, "/api/v1/config/public-web-nodes")
    api.add_resource(PublicWebNodeResource, "/api/v1/config/public-web-nodes/<int:node_id>")
    api.add_resource(PublicWebsResource, "/api/v1/config/public-web-nodes/<int:node_id>/webs")
    api.add_resource(PublicWebResource, "/api/v1/config/public-web-nodes/<int:node_id>/webs/<int:web_id>")
    api.add_resource(PublicWebEmailTestResource, "/api/v1/config/public-web-nodes/<int:node_id>/webs/test-email")
    api.add_resource(
        PublicWebImageResource,
        "/api/v1/config/public-web-nodes/<int:node_id>/webs/<int:web_id>/images/<string:kind>",
    )

    api.add_resource(RemoteNodesResource, "/api/v1/config/remote-nodes")
    api.add_resource(RemoteNodeResource, "/api/v1/config/remote-nodes/<int:remote_node_id>")
    api.add_resource(RemoteNodeConnectResource, "/api/v1/config/remote-nodes/<int:remote_node_id>/connect")

    api.add_resource(PresentersNodesResource, "/api/v1/config/presenters-nodes")
    api.add_resource(PresentersNodeResource, "/api/v1/config/presenters-nodes/<string:node_id>")

    api.add_resource(PublisherNodesResource, "/api/v1/config/publishers-nodes")
    api.add_resource(PublishersNodeResource, "/api/v1/config/publishers-nodes/<string:node_id>")

    api.add_resource(PublisherPresetsResource, "/api/v1/config/publishers-presets")
    api.add_resource(PublisherPresetResource, "/api/v1/config/publishers-presets/<string:preset_id>")

    api.add_resource(BotNodesResource, "/api/v1/config/bots-nodes")
    api.add_resource(BotsNodeResource, "/api/v1/config/bots-nodes/<string:node_id>")

    api.add_resource(BotPresetsResource, "/api/v1/config/bots-presets")
    api.add_resource(BotPresetResource, "/api/v1/config/bots-presets/<string:preset_id>")

    api.add_resource(StatesResource, "/api/v1/config/state-definitions")
    api.add_resource(StateResource, "/api/v1/config/state-definitions/<int:state_id>")
    api.add_resource(StateEntityTypesResource, "/api/v1/config/state-entity-types")
    api.add_resource(StateEntityTypeResource, "/api/v1/config/state-entity-types/<int:state_entity_type_id>")

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

    Permission.add("CONFIG_SETTINGS_ACCESS", "Config settings access", "Access to settings configuration")
    Permission.add("CONFIG_SETTINGS_CREATE", "Config setting create", "Create setting configuration")
    Permission.add("CONFIG_SETTINGS_UPDATE", "Config setting update", "Update setting configuration")
    Permission.add("CONFIG_SETTINGS_DELETE", "Config setting delete", "Delete setting configuration")

    Permission.add("CONFIG_WORD_LIST_ACCESS", "Config word lists access", "Access to word lists configuration")
    Permission.add("CONFIG_WORD_LIST_CREATE", "Config word list create", "Create word list configuration")
    Permission.add("CONFIG_WORD_LIST_UPDATE", "Config word list update", "Update word list configuration")
    Permission.add("CONFIG_WORD_LIST_DELETE", "Config word list delete", "Delete word list configuration")

    Permission.add("CONFIG_AI_ACCESS", "Config AI access", "Access to AI configuration")
    Permission.add("CONFIG_AI_CREATE", "Config AI create", "Create AI configuration")
    Permission.add("CONFIG_AI_UPDATE", "Config AI update", "Update AI configuration")
    Permission.add("CONFIG_AI_DELETE", "Config AI delete", "Delete AI configuration")

    Permission.add("CONFIG_AUTH_PROVIDER_ACCESS", "Config auth providers access", "Access to authentication providers configuration")
    Permission.add("CONFIG_AUTH_PROVIDER_CREATE", "Config auth provider create", "Create authentication provider configuration")
    Permission.add("CONFIG_AUTH_PROVIDER_UPDATE", "Config auth provider update", "Update authentication provider configuration")
    Permission.add("CONFIG_AUTH_PROVIDER_DELETE", "Config auth provider delete", "Delete authentication provider configuration")

    Permission.add("CONFIG_DATA_PROVIDER_ACCESS", "Config data provider access", "Access to data provider configuration")
    Permission.add("CONFIG_DATA_PROVIDER_CREATE", "Config data provider create", "Create data provider configuration")
    Permission.add("CONFIG_DATA_PROVIDER_UPDATE", "Config data provider update", "Update data provider configuration")
    Permission.add("CONFIG_DATA_PROVIDER_DELETE", "Config data provider delete", "Delete data provider configuration")

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

    Permission.add("CONFIG_PUBLIC_WEB_NODE_ACCESS", "Config public-web nodes access", "Access to public-web nodes configuration")
    Permission.add("CONFIG_PUBLIC_WEB_NODE_CREATE", "Config public-web node create", "Create public-web node configuration")
    Permission.add("CONFIG_PUBLIC_WEB_NODE_UPDATE", "Config public-web node update", "Update public-web node configuration")
    Permission.add("CONFIG_PUBLIC_WEB_NODE_DELETE", "Config public-web node delete", "Delete public-web node configuration")

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
