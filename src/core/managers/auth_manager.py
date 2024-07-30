"""This module contains the authentication manager for the Taranis-NG application.

The authentication manager handles user authentication and authorization using different authenticators.
It provides functions for initializing the manager, authenticating users, refreshing authentication tokens,
performing access control checks, and retrieving user permissions.

Classes:
    ACLCheck: Enumeration for ACL checks.

Functions:
    cleanup_token_blacklist: Clean up the token blacklist by deleting tokens older than one day.
    initialize: Initialize the authentication manager.
    get_required_credentials: Get the required credentials for authentication.
    authenticate: Authenticate the user with the provided credentials.
    refresh: Refresh the authentication token for the specified user.
    logout: Log out a user.
    check_acl: Check the access control list (ACL) for the given item.
    no_auth: Decorator that allows access to the decorated function without authentication.
    get_id_name_by_acl: Get the corresponding ID name based on the given ACL.
    get_user_from_api_key: Try to authenticate the user by API key.
    get_perm_from_user: Get user permissions.
    get_user_from_jwt_token: Try to authenticate the user by JWT token.
    get_perm_from_jwt_token: Get user permissions from JWT token.
"""

import os
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
import jwt
from flask import request
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request, get_jwt
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

try:
    with open(os.getenv("API_KEY_FILE"), "r") as file:
        api_key = file.read()
except FileNotFoundError:
    print("API_KEY_FILE not found. Please set the API_KEY_FILE environment variable to the path of the file containing the API key.")
    api_key = os.getenv("API_KEY")


def cleanup_token_blacklist(app):
    """
    Clean up the token blacklist by deleting tokens older than one day.

    Arguments:
        app -- The Flask application object.
    """
    with app.app_context():
        TokenBlacklist.delete_older(datetime.today() - timedelta(days=1))


def initialize(app):
    """
    Initialize the authentication manager.

    This function sets up the authentication manager based on the configured authenticator.

    Arguments:
        app: The Flask application object.

    Returns:
        None
    """
    global current_authenticator

    JWTManager(app)

    which = os.getenv("TARANIS_NG_AUTHENTICATOR")
    if which is not None:
        which = which.lower()
    if which == "openid":
        current_authenticator = OpenIDAuthenticator()
    elif which == "keycloak":
        current_authenticator = KeycloakAuthenticator()
    elif which == "password":
        current_authenticator = PasswordAuthenticator()
    elif which == "ldap":
        current_authenticator = LDAPAuthenticator()
    else:
        current_authenticator = PasswordAuthenticator()

    current_authenticator.initialize(app)

    time_manager.schedule_job_every_day("00:00", cleanup_token_blacklist, app)


def get_required_credentials():
    """Get the required credentials.

    This function returns the required credentials for the current authenticator.

    Returns:
        The required credentials for the current authenticator.
    """
    return current_authenticator.get_required_credentials()


def authenticate(credentials):
    """Authenticate the user using the provided credentials.

    Arguments:
        credentials -- The user's credentials.

    Returns:
        The result of the authentication process.
    """
    return current_authenticator.authenticate(credentials)


def refresh(user):
    """Refresh the authentication token for the given user.

    Arguments:
        user -- The user object for which the authentication token needs to be refreshed.

    Returns:
        The refreshed authentication token.
    """
    return current_authenticator.refresh(user)


def logout(token):
    """Logout the user.

    This function logs out the user by calling the `logout` method of the current authenticator.

    Arguments:
        token (str): The authentication token of the user.

    Returns:
        None
    """
    return current_authenticator.logout(token)


class ACLCheck(Enum):
    """Enumeration for ACL checks.

    This enumeration defines the different types of access control checks that can be performed.

    Attributes:
        OSINT_SOURCE_GROUP_ACCESS: Access check for OSINT source group.
        NEWS_ITEM_ACCESS: Access check for news item.
        NEWS_ITEM_MODIFY: Modify check for news item.
        REPORT_ITEM_ACCESS: Access check for report item.
        REPORT_ITEM_MODIFY: Modify check for report item.
        PRODUCT_TYPE_ACCESS: Access check for product type.
        PRODUCT_TYPE_MODIFY: Modify check for product type.
    """

    OSINT_SOURCE_GROUP_ACCESS = auto()
    NEWS_ITEM_ACCESS = auto()
    NEWS_ITEM_MODIFY = auto()
    REPORT_ITEM_ACCESS = auto()
    REPORT_ITEM_MODIFY = auto()
    PRODUCT_TYPE_ACCESS = auto()
    PRODUCT_TYPE_MODIFY = auto()


def check_acl(item_id, acl_check, user):
    """Check the access control list (ACL) for the given item.

    This function determines whether the user has the necessary permissions to perform the specified ACL check on the item.

    Arguments:
        item_id (str): The ID of the item.
        acl_check (str): The type of ACL check to perform.
        user (str): The user performing the ACL check.

    Returns:
        bool: True if the user is allowed to perform the ACL check, False otherwise.
    """
    check_see = "SEE" in str(acl_check)
    check_access = "ACCESS" in str(acl_check)
    check_modify = "MODIFY" in str(acl_check)
    allowed = False
    item_type = "UNKNOWN"

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
            log_manager.store_user_auth_error_activity(user, f"Unauthorized access attempt to {item_type}: {item_id}")
        else:
            log_manager.store_user_auth_error_activity(user, f"Unauthorized modification attempt to {item_type}: {item_id}")

    return allowed


def no_auth(fn):
    """Allow access to the decorated function without authentication.

    Arguments:
        fn (function): The function to be decorated.

    Returns:
        function: The decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        log_manager.store_activity("API_ACCESS", None)
        return fn(*args, **kwargs)

    return wrapper


def get_id_name_by_acl(acl):
    """Get the ID name based on the ACL.

    This function takes an ACL object and returns the corresponding ID name based on the ACL's name.

    Arguments:
        acl -- The ACL object.

    Returns:
        The ID name corresponding to the ACL's name.
    """
    if "NEWS_ITEM" in acl.name:
        return "item_id"
    elif "REPORT_ITEM" in acl.name:
        return "report_item_id"
    elif "OSINT_SOURCE_GROUP" in acl.name:
        return "group_id"
    elif "PRODUCT" in acl.name:
        return "product_id"


def get_user_from_api_key():
    """Try to authenticate the user by API key.

    Returns:
        user (User object or None): The authenticated user object, or None if authentication fails.
    """
    try:
        if "Authorization" not in request.headers or not request.headers["Authorization"].__contains__("Bearer "):
            return None
        key_string = request.headers["Authorization"].replace("Bearer ", "")
        api_key = ApiKey.find_by_key(key_string)
        if not api_key:
            return None
        user = User.find_by_id(api_key.user_id)
        return user
    except Exception as ex:
        log_manager.store_auth_error_activity(f"ApiKey check presence error: {ex}")
        return None


def get_perm_from_user(user):
    """Get user permissions.

    Args:
        user: User object representing the user.

    Returns:
        Set of user's permissions (as permission IDs) or None if an error occurs.
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
        log_manager.store_auth_error_activity(f"Get permission from user error: {ex}")
        return None


def get_user_from_jwt_token():
    """Try to authenticate the user by API key.

    This function verifies the JWT token in the request and retrieves the user object associated with the token's identity.

    Returns:
        user (User object or None): The authenticated user object if successful, otherwise None.
    """
    try:
        verify_jwt_in_request()
    except JWTExtendedException:
        log_manager.store_auth_error_activity("Missing JWT")
        return None

    # does it encode an identity?
    identity = get_jwt_identity()
    if not identity:
        log_manager.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
        return None

    user = User.find(identity)
    if not user:
        log_manager.store_auth_error_activity(f"Unknown identity in JWT: {identity}")
        return None
    return user


def get_perm_from_jwt_token(user):
    """Get user permissions from JWT token.

    Args:
        user: The user object.

    Returns:
        A set of user's permissions if available, otherwise None.
    """
    try:
        # does it include permissions?
        jwt_data = get_jwt()
        claims = jwt_data["user_claims"]
        if not claims or "permissions" not in claims:
            log_manager.store_user_auth_error_activity(user, "Missing permissions in JWT")
            return None

        all_users_perms = set(claims["permissions"])
        return all_users_perms
    except Exception as ex:
        log_manager.store_auth_error_activity(f"Get permission from JWT error: {ex}")
        return None


def auth_required(required_permissions, *acl_args):
    """Check if the user has the required permissions and ACL access.

    Arguments:
        required_permissions (str or list): The required permissions for the user.
        *acl_args: Additional arguments for ACL access.

    Returns:
        The decorated function.
    """

    def auth_required_wrap(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            error = ({"error": "not authorized"}, 401)

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
                log_manager.store_user_auth_error_activity(user, f"Insufficient permissions for user: {user.username}")
                return error

            # if the object does have an ACL, do we match it?
            if len(acl_args) > 0 and not check_acl(kwargs[get_id_name_by_acl(acl_args[0])], acl_args[0], user):
                log_manager.store_user_auth_error_activity(user, f"Access denied by ACL for user: {user.username}")
                return error

            # allow
            log_manager.store_user_activity(user, str(required_permissions_set), str(request.json))
            return fn(*args, **kwargs)

        return wrapper

    return auth_required_wrap


def api_key_required(fn):
    """Check for the presence of an API key in the Authorization header.

    Arguments:
        fn: The function to be decorated.

    Returns:
        The decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)

        # do we have the authorization header?
        if "Authorization" not in request.headers:
            log_manager.store_auth_error_activity("Missing Authorization header for external access")
            return error

        # is it properly encoded?
        auth_header = request.headers["Authorization"]
        if not auth_header.startswith("Bearer"):
            log_manager.store_auth_error_activity("Missing Authorization Bearer for external access")
            return error

        # does it match some of our collector's keys?
        api_key = auth_header.replace("Bearer ", "")
        if not CollectorsNode.exists_by_api_key(api_key):
            api_key = log_manager.sensitive_value(api_key)
            log_manager.store_auth_error_activity(f"Incorrect api key: {api_key} for external access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def access_key_required(fn):
    """Check for access key authorization.

    This decorator can be used to protect routes or functions that require access key authorization.
    It checks if the request has a valid access key in the Authorization header.

    Arguments:
        fn (function): The function to be decorated.

    Returns:
        function: The decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        error = ({"error": "not authorized"}, 401)

        # do we have the authorization header?
        if "Authorization" not in request.headers:
            log_manager.store_auth_error_activity("Missing Authorization header for remote access")
            return error

        # is it properly encoded?
        auth_header = request.headers["Authorization"]
        if not auth_header.startswith("Bearer"):
            log_manager.store_auth_error_activity("Missing Authorization Bearer for remote access")
            return error

        # does it match some of our remote peer's access keys?
        if not RemoteAccess.exists_by_access_key(auth_header.replace("Bearer ", "")):
            log_manager.store_auth_error_activity(f"Incorrect access key: {auth_header.replace('Bearer ', '')} for remote access")
            return error

        # allow
        return fn(*args, **kwargs)

    return wrapper


def jwt_required(fn):
    """Check if a valid JWT is present in the request headers.

    Arguments:
        fn -- The function to be decorated.

    Returns:
        The decorated function.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except JWTExtendedException:
            log_manager.store_auth_error_activity("Missing JWT")
            return {"error": "authorization required"}, 401

        identity = get_jwt_identity()
        if not identity:
            log_manager.store_auth_error_activity(f"Missing identity in JWT: {get_jwt()}")
            return {"error": "authorization failed"}, 401

        user = User.find(identity)
        if user is None:
            log_manager.store_auth_error_activity(f"Unknown identity: {identity}")
            return {"error": "authorization failed"}, 401

        log_manager.store_user_activity(user, "API_ACCESS", "Access permitted")
        return fn(*args, **kwargs)

    return wrapper


def get_access_key():
    """Get the access key from the request headers.

    This function retrieves the access key from the "Authorization" header of the request.
    The access key is expected to be in the format "Bearer <access_key>".

    Returns:
        The access key extracted from the request headers.
    """
    return request.headers["Authorization"].replace("Bearer ", "")


def get_user_from_jwt():
    """Obtain the identity and current permissions.

    This function first tries to obtain the user from the API key.
    If the user is not found, it then tries to obtain the user from the JWT token.

    Returns:
        The user object if found, None otherwise.
    """
    user = get_user_from_api_key()
    if user is None:
        user = get_user_from_jwt_token()
    return user


def decode_user_from_jwt(jwt_token):
    """Decode the user from a JWT token.

    Arguments:
        jwt_token (str): The JWT token to decode.

    Returns:
        User: The user object decoded from the JWT token.
    """
    decoded = None
    jwt_secret_key = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret_key:
        with open(os.getenv("JWT_SECRET_KEY_FILE"), "r") as file:
            jwt_secret_key = file.read()
    try:
        decoded = jwt.decode(jwt_token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
    except Exception as ex:  # e.g. "Signature has expired"
        log_manager.store_auth_error_activity(f"Invalid JWT: {str(ex)}")
    if decoded is None:
        return None
    return User.find(decoded["sub"])


def get_external_permissions_ids():
    """Return a list of external permissions IDs.

    This function returns a list of permission IDs that are related to accessing, creating, and configuring assets.

    Returns:
        list: A list of external permission IDs.
    """
    return ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG"]


def get_external_permissions():
    """Get the external permissions.

    Returns:
        A list of external permissions.
    """
    permissions = []
    for permission_id in get_external_permissions_ids():
        permissions.append(Permission.find(permission_id))

    return permissions
