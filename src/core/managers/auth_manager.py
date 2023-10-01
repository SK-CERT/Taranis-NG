import os
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
import jwt
from flask import request
from flask_jwt_extended import JWTManager, get_jwt_claims, get_jwt_identity, verify_jwt_in_request, get_raw_jwt
from flask_jwt_extended.exceptions import JWTExtendedException

from managers import log_manager, time_manager
from auth.keycloak_authenticator import KeycloakAuthenticator
from auth.openid_authenticator import OpenIDAuthenticator
from auth.password_authenticator import PasswordAuthenticator
from auth.ldap_authenticator import LDAPAuthenticator
from model.collectors_node import CollectorsNode
from model.news_item import NewsItem
from model.osint_source import OSINTSourceGroup
from model.permission import Permission
from model.product_type import ProductType
from model.remote import RemoteAccess
from model.report_item import ReportItem
from model.token_blacklist import TokenBlacklist
from model.user import User
from model.apikey import ApiKey

current_authenticator = None

api_key = os.getenv('API_KEY')


def cleanup_token_blacklist(app):
    with app.app_context():
        TokenBlacklist.delete_older(datetime.today() - timedelta(days=1))


def initialize(app):
    global current_authenticator

    JWTManager(app)

    which = os.getenv('TARANIS_NG_AUTHENTICATOR')
    if which is not None:
        which = which.lower()
    if which == 'openid':
        current_authenticator = OpenIDAuthenticator()
    elif which == 'keycloak':
        current_authenticator = KeycloakAuthenticator()
    elif which == 'password':
        current_authenticator = PasswordAuthenticator()
    elif which == 'ldap':
        current_authenticator = LDAPAuthenticator()
    else:
        current_authenticator = PasswordAuthenticator()

    current_authenticator.initialize(app)

    time_manager.schedule_job_every_day("00:00", cleanup_token_blacklist, app)


def get_required_credentials():
    return current_authenticator.get_required_credentials()


def authenticate(credentials):
    return current_authenticator.authenticate(credentials)


def refresh(user):
    return current_authenticator.refresh(user)


def logout(token):
    return current_authenticator.logout(token)


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

    if acl_check in [ACLCheck.NEWS_ITEM_ACCESS, ACLCheck.NEWS_ITEM_MODIFY]:
        item_type = "News Item"
        allowed = NewsItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.REPORT_ITEM_ACCESS, ACLCheck.REPORT_ITEM_MODIFY]:
        item_type = "Report Item"
        allowed = ReportItem.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if acl_check in [ACLCheck.PRODUCT_TYPE_ACCESS, ACLCheck.PRODUCT_TYPE_MODIFY]:
        item_type = "Product Type"
        allowed = ProductType.allowed_with_acl(item_id, user, check_see, check_access, check_modify)

    if not allowed:
        if check_access:
            log_manager.store_user_auth_error_activity(user, "Unauthorized access attempt to {}: {}".format(item_type, item_id))
        else:
            log_manager.store_user_auth_error_activity(user, "Unauthorized modification attempt to {}: {}".format(item_type, item_id))

    return allowed


def no_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        log_manager.store_activity("API_ACCESS", None)
        return fn(*args, **kwargs)

    return wrapper


def get_id_name_by_acl(acl):
    if "NEWS_ITEM" in acl.name:
        return "item_id"
    elif "REPORT_ITEM" in acl.name:
        return "report_item_id"
    elif "OSINT_SOURCE_GROUP" in acl.name:
        return "group_id"
    elif "PRODUCT" in acl.name:
        return "product_id"


def get_user_from_api_key():
    """
    Try to authenticate the user by API key

    Returns:
        (user)
        user: User object or None
    """
    try:
        if 'Authorization' not in request.headers or not request.headers['Authorization'].__contains__('Bearer '):
            return None
        key_string = request.headers['Authorization'].replace('Bearer ', '')
        api_key = ApiKey.find_by_key(key_string)
        if not api_key:
            return None
        user = User.find_by_id(api_key.user_id)
        return user
    except Exception as ex:
        log_manager.store_auth_error_activity("Apikey check presence error: " + str(ex))
        return None


def get_perm_from_user(user):
    """
    Get user permmisions

    Returns:
        (all_user_perms)
        all_users_perms: set of user's Permissions or None
    """
    try:
        all_users_perms = set()
        for perm in user.permissions:
            all_users_perms.add(perm.id)
        for role in user.roles:
            role_perms = set(perm.id for perm in role.permissions)
            all_users_perms = all_users_perms.union(role_perms)
        return all_users_perms
    except Exception as ex:
        log_manager.store_auth_error_activity("Get permmision from user error: " + str(ex))
        return None


def get_user_from_jwt_token():
    """
    Try to authenticate the user by API key

    Returns:
        (user)
        user: User object or None
    """
    try:
        verify_jwt_in_request()
    except JWTExtendedException:
        log_manager.store_auth_error_activity("Missing JWT")
        return None

    # does it encode an identity?
    identity = get_jwt_identity()
    if not identity:
        log_manager.store_auth_error_activity("Missing identity in JWT: " + get_raw_jwt())
        return None

    user = User.find(identity)
    if not user:
        log_manager.store_auth_error_activity("Unknown identity in JWT: {}".format(identity))
        return None
    return user


def get_perm_from_jwt_token(user):
    """
    Get user permmisions

    Returns:
        (all_user_perms)
        all_users_perms: set of user's Permissions or None
    """
    try:
        # does it include permissions?
        claims = get_jwt_claims()
        if not claims or 'permissions' not in claims:
            log_manager.store_user_auth_error_activity(user, "Missing permissions in JWT")
            return None

        all_users_perms = set(claims['permissions'])
        return all_users_perms
    except Exception as ex:
        log_manager.store_auth_error_activity("Get permmision from JWT error: " + str(ex))
        return None


def auth_required(required_permissions, *acl_args):
    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = ({'error': 'not authorized'}, 401)

            if isinstance(required_permissions, list):
                required_permissions_set = set(required_permissions)
            else:
                required_permissions_set = {required_permissions}

            # obtain the identity and current permissions of that identity
            user = get_user_from_api_key()
            if user is None:
                user = get_user_from_jwt_token()
                active_permissions_set = get_perm_from_jwt_token(user)
            else:
                active_permissions_set = get_perm_from_user(user)
            if user is None:
                log_manager.store_auth_error_activity("Unauthorized API call access (invalid user)")
                return error

            # is there at least one match with the permissions required by the call?
            if not required_permissions_set.intersection(active_permissions_set):
                log_manager.store_user_auth_error_activity(user, "Insufficient permissions for user: {}".format(user.username))
                return error

            # if the object does have an ACL, do we match it?
            if len(acl_args) > 0 and not check_acl(kwargs[get_id_name_by_acl(acl_args[0])], acl_args[0], user):
                log_manager.store_user_auth_error_activity(user, "Access denied by ACL for user: {}".format(user.username))
                return error

            # allow
            log_manager.store_user_activity(user, str(required_permissions_set), str(request.json))
            return fn(*args, **kwargs)

        return wrapper
    return auth_required_wrap


def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({'error': 'not authorized'}, 401)

        # do we have the authorization header?
        if 'Authorization' not in request.headers:
            log_manager.store_auth_error_activity("Missing Authorization header for external access")
            return error

        # is it properly encoded?
        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer'):
            log_manager.store_auth_error_activity("Missing Authorization Bearer for external access")
            return error

        # does it match some of our collector's keys?
        api_key = auth_header.replace('Bearer ', '')
        if not CollectorsNode.exists_by_api_key(api_key):
            api_key = log_manager.sensitive_value(api_key)
            log_manager.store_auth_error_activity("Incorrect api key: " + api_key + " for external access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def access_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({'error': 'not authorized'}, 401)

        # do we have the authorization header?
        if 'Authorization' not in request.headers:
            log_manager.store_auth_error_activity("Missing Authorization header for remote access")
            return error

        # is it properly encoded?
        auth_header = request.headers['Authorization']
        if not auth_header.startswith('Bearer'):
            log_manager.store_auth_error_activity("Missing Authorization Bearer for remote access")
            return error

        # does it match some of our remote peer's access keys?
        if not RemoteAccess.exists_by_access_key(auth_header.replace('Bearer ', '')):
            log_manager.store_auth_error_activity("Incorrect access key: "
                                                  + auth_header.replace('Bearer ',
                                                                        '') + " for remote access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):

        try:
            verify_jwt_in_request()
        except JWTExtendedException:
            log_manager.store_auth_error_activity("Missing JWT")
            return {'error': 'authorization required'}, 401

        identity = get_jwt_identity()
        if not identity:
            log_manager.store_auth_error_activity("Missing identity in JWT: {}".format(get_raw_jwt()))
            return {'error': 'authorization failed'}, 401

        user = User.find(identity)
        if user is None:
            log_manager.store_auth_error_activity("Unknown identity: ".format(identity))
            return {'error': 'authorization failed'}, 401

        log_manager.store_user_activity(user, "API_ACCESS", "Access permitted")
        return fn(*args, **kwargs)

    return wrapper


def get_access_key():
    return request.headers['Authorization'].replace('Bearer ', '')


def get_user_from_jwt():
    # obtain the identity and current permissions
    user = get_user_from_api_key()
    if user is None:
        user = get_user_from_jwt_token()
    return user


def decode_user_from_jwt(jwt_token):
    decoded = None
    try:
        decoded = jwt.decode(jwt_token, os.getenv('JWT_SECRET_KEY'))
    except Exception as ex:  # e.g. "Signature has expired"
        log_manager.store_auth_error_activity("Invalid JWT: " + str(ex))
    if decoded is None:
        return None
    return User.find(decoded['sub'])


def get_external_permissions_ids():
    return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG"]


def get_external_permissions():
    permissions = []
    for permission_id in get_external_permissions_ids():
        permissions.append(Permission.find(permission_id))

    return permissions
