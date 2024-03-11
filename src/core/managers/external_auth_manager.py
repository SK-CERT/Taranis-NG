"""This module provides functions for managing users in an external authentication system.

The module includes functions for checking if Keycloak user management is enabled,
retrieving the Keycloak admin password, creating a KeycloakAdmin instance,
creating a user in the external authentication system, updating user information,
and deleting a user from the external authentication system.

Functions:
- keycloak_user_management_enabled(): Check if Keycloak user management is enabled.
- get_keycloak_password(): Get the Keycloak admin password.
- get_keycloak_admin(): Return an instance of KeycloakAdmin.
- create_user(user_data): Create a user in the external authentication system.
- update_user(user_data, original_username): Update user information in the external authentication system.
- delete_user(username): Delete a user from the external authentication system.
"""

import os
from keycloak import KeycloakAdmin


def keycloak_user_management_enabled():
    """Check if Keycloak user management is enabled.

    Returns:
        bool: True if Keycloak user management is enabled, False otherwise.
    """
    if "KEYCLOAK_USER_MANAGEMENT" in os.environ:
        return os.getenv("KEYCLOAK_USER_MANAGEMENT").lower() == "true"
    else:
        return False


def get_keycloak_password():
    """Get the Keycloak admin password.

    This function retrieves the Keycloak admin password from the environment variable
    KEYCLOAK_ADMIN_PASSWORD. If the environment variable is not set, it reads the password
    from the file specified by the environment variable KEYCLOAK_ADMIN_PASSWORD_FILE.

    Returns:
        str: The Keycloak admin password.
    """
    keycloak_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    if not keycloak_password:
        with open(os.getenv("KEYCLOAK_ADMIN_PASSWORD_FILE"), "r") as file:
            keycloak_password = file.read()
    return keycloak_password


def get_keycloak_admin():
    """Return an instance of KeycloakAdmin.

    This function retrieves the necessary environment variables and uses them to create
    and configure a KeycloakAdmin object. The KeycloakAdmin object is then returned.

    Returns:
        KeycloakAdmin: An instance of the KeycloakAdmin class.
    """
    return KeycloakAdmin(
        server_url=os.getenv("KEYCLOAK_SERVER_URL"),
        username=os.getenv("KEYCLOAK_ADMIN_USERNAME"),
        password=get_keycloak_password(),
        realm_name=os.getenv("KEYCLOAK_REALM_NAME"),
        client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET_KEY"),
        verify=(os.getenv("KEYCLOAK_VERIFY").lower() == "true"),
    )


def create_user(user_data):
    """Create a user in the external authentication system.

    Arguments:
        user_data (dict): A dictionary containing user data.
            - username (str): The username of the user.
            - password (str): The password of the user.
    """
    if keycloak_user_management_enabled():
        keycloak_admin = get_keycloak_admin()
        keycloak_admin.create_user(
            {"username": user_data["username"], "credentials": [{"value": user_data["password"], "type": "password"}], "enabled": True}
        )


def update_user(user_data, original_username):
    """Update user information in the external authentication system.

    This function updates the user information in the external authentication system, such as Keycloak.

    Arguments:
        user_data (dict): A dictionary containing the updated user data.
        original_username (str): The original username of the user.
    """
    if keycloak_user_management_enabled():
        if "password" in user_data and user_data["password"] or original_username != user_data["username"]:
            keycloak_admin = get_keycloak_admin()
            keycloak_user_id = keycloak_admin.get_user_id(original_username)
            if keycloak_user_id is not None:
                if original_username != user_data["username"]:
                    keycloak_admin.update_user(user_id=keycloak_user_id, payload={"username": user_data["username"]})

                if "password" in user_data and user_data["password"]:
                    keycloak_admin.set_user_password(user_id=keycloak_user_id, password=user_data["password"], temporary=False)


def delete_user(username):
    """Delete a user from the external authentication system.

    This function deletes a user from the external authentication system, such as Keycloak.

    Arguments:
        username (str): The username of the user to be deleted.
    """
    if keycloak_user_management_enabled():
        keycloak_admin = get_keycloak_admin()
        keycloak_user_id = keycloak_admin.get_user_id(username)
        if keycloak_user_id is not None:
            keycloak_admin.delete_user(user_id=keycloak_user_id)
