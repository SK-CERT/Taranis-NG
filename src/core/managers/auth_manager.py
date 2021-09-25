from functools import wraps
from auth.test_authenticator import TestAuthenticator
from auth.openid_authenticator import OpenIDAuthenticator
from flask_jwt_extended import JWTManager, get_jwt_claims, get_jwt_identity, verify_jwt_in_request, get_raw_jwt
from flask_jwt_extended.exceptions import JWTExtendedException
import jwt
from flask import request
from model.collectors_node import CollectorsNode
from model.user import User
from model.permission import Permission
from model.osint_source import OSINTSourceGroup
import os
from managers import audit_manager
from enum import Enum, auto
from model.report_item import ReportItem
from model.product_type import ProductType
from model.news_item import NewsItem
from model.remote import RemoteAccess

authenticators = [TestAuthenticator(), OpenIDAuthenticator()]
current_authenticator = 0


def get_required_credentials():
    return authenticators[current_authenticator].get_required_credentials()


def authenticate(credentials):
    return authenticators[current_authenticator].authenticate(credentials)


def logout():
    return authenticators[current_authenticator].logout()


def initialize(app):
    JWTManager(app)
    for authenticator in authenticators:
        authenticator.initialize(app)


class ACLCheck(Enum):
    OSINT_SOURCE_GROUP_ACCESS = auto()
    NEWS_ITEM_ACCESS = auto()
    NEWS_ITEM_MODIFY = auto()
    REPORT_ITEM_ACCESS = auto()
    REPORT_ITEM_MODIFY = auto()
    PRODUCT_TYPE_ACCESS = auto()
    PRODUCT_TYPE_MODIFY = auto()


def check_acl(item_id, acl_check, user):
    check_see = 'SEE' in str(acl_check)
    check_access = 'ACCESS' in str(acl_check)
    check_modify = 'MODIFY' in str(acl_check)
    allowed = False
    item_type = 'UNKNOWN'

    if acl_check == ACLCheck.OSINT_SOURCE_GROUP_ACCESS:
        item_type = "OSINT Source Group"
        allowed = OSINTSourceGroup.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check == ACLCheck.NEWS_ITEM_ACCESS or acl_check == ACLCheck.NEWS_ITEM_MODIFY:
        item_type = "News Item"
        allowed = NewsItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check == ACLCheck.REPORT_ITEM_ACCESS or acl_check == ACLCheck.REPORT_ITEM_MODIFY:
        item_type = "Report Item"
        allowed = ReportItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check == ACLCheck.PRODUCT_TYPE_ACCESS or acl_check == ACLCheck.PRODUCT_TYPE_MODIFY:
        item_type = "Product Type"
        allowed = ProductType.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if not allowed:
        if check_access:
            audit_manager.store_user_auth_error_activity(user,
                                                         "Unauthorized access attempt to " + item_type + ": " + item_id)
        else:
            audit_manager.store_user_auth_error_activity(user,
                                                         "Unauthorized modification attempt to " + item_type
                                                         + ": " + item_id)

    return allowed


def no_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        audit_manager.store_activity("API_ACCESS", None)
        return fn(*args, **kwargs)

    return wrapper


def auth_required(permissions, *acl_args):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            try:
                verify_jwt_in_request()
            except JWTExtendedException:
                audit_manager.store_auth_error_activity("Missing JWT")
                return {'error': 'authorization required'}, 401

            identity = get_jwt_identity()
            if not identity:
                audit_manager.store_auth_error_activity("Missing identity in JWT: " + get_raw_jwt())
                return {'error': 'authorization failed'}, 401

            claims = get_jwt_claims()
            if not claims or 'permissions' not in claims:
                audit_manager.store_auth_error_activity("Missing permissions in JWT for identity: " + identity)
                return {'error': 'authorization failed'}, 401

            if isinstance(permissions, list):
                permissions_set = set(permissions)
            else:
                permissions_set = {permissions}

            user = User.find(identity)

            if permissions_set.intersection(set(claims['permissions'])):
                access_allowed = True
                if len(acl_args) > 0:
                    access_allowed = check_acl(kwargs['id'], acl_args[0], user)

                if access_allowed is True:
                    audit_manager.store_user_activity(user, str(permissions), str(request.json))
                    return fn(*args, **kwargs)
                else:
                    return {'error': 'not authorized'}, 401
            else:
                audit_manager.store_user_auth_error_activity(user,
                                                             "Insufficient permissions in JWT for identity: " + identity)
                return {'error': 'not authorized'}, 401

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.headers.has_key('Authorization'):
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer'):
                if CollectorsNode.exists_by_api_key(auth_header.replace('Bearer ', '')):
                    return fn(*args, **kwargs)
                else:
                    audit_manager.store_auth_error_activity("Incorrect api key: "
                                                            + auth_header.replace('Bearer ',
                                                                                  '') + " for external access")
            else:
                audit_manager.store_auth_error_activity("Missing Authorization Bearer for external access")
        else:
            audit_manager.store_auth_error_activity("Missing Authorization header for external access")

        return {'error': 'not authorized'}, 401

    return wrapper


def access_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.headers.has_key('Authorization'):
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer'):
                if RemoteAccess.exists_by_access_key(auth_header.replace('Bearer ', '')):
                    return fn(*args, **kwargs)
                else:
                    audit_manager.store_auth_error_activity("Incorrect access key: "
                                                            + auth_header.replace('Bearer ',
                                                                                  '') + " for remote access")
            else:
                audit_manager.store_auth_error_activity("Missing Authorization Bearer for remote access")
        else:
            audit_manager.store_auth_error_activity("Missing Authorization header for remote access")

        return {'error': 'not authorized'}, 401

    return wrapper


def get_access_key():
    return request.headers['Authorization'].replace('Bearer ', '')


def get_user_from_jwt():
    try:
        verify_jwt_in_request()
    except JWTExtendedException:
        return None

    identity = get_jwt_identity()
    if not identity:
        return None

    return User.find(identity)


def decode_user_from_jwt(jwt_token):
    decoded = jwt.decode(jwt_token, os.getenv('JWT_SECRET_KEY'))
    if decoded is not None:
        return User.find(decoded['sub'])


def get_external_permissions_ids():
    return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG"]


def get_external_permissions():
    permissions = []
    for permission_id in get_external_permissions_ids():
        permissions.append(Permission.find(permission_id))

    return permissions
