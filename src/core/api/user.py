"""This module defines several Flask-RESTful resources for handling user-related operations.

This includes word lists, product types, and publisher presets. It also provides
an initialization function to add these resources to a Flask API instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_restful import Api

from http import HTTPStatus

from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from managers import auth_manager, totp_manager, webauthn_manager
from managers.auth_manager import auth_required
from model.product_type import ProductType
from model.publisher_preset import PublisherPreset
from model.user import Hotkey, UserWordList
from model.webauthn_credential import WebauthnCredential
from model.word_list import WordList


class UserHotkeys(Resource):
    """UserHotkeys resource for handling user hotkeys related operations.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @jwt_required()
    def get(self) -> dict:
        """Retrieve the hotkeys of the authenticated user.

        This method extracts the user information from the JWT (JSON Web Token)
        and returns the user's hotkeys in JSON format.

        Returns:
            dict: A dictionary containing the user's hotkeys information in JSON format.
        """
        user = auth_manager.get_user_from_jwt()
        return Hotkey.get_json(user)

    @jwt_required()
    def put(self) -> dict:
        """Update the hotkeys of the authenticated user.

        This method retrieves the user from the JWT token and updates their hotkeys
        with the data provided in the JSON request body.

        Returns:
            Response: The response from the Hotkey.update method.
        """
        user = auth_manager.get_user_from_jwt()
        return Hotkey.update(user, request.json)


class UserWordLists(Resource):
    """A resource class for handling user word lists.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @jwt_required()
    def get(self) -> dict:
        """Retrieve all word lists in JSON format for the authenticated user.

        Returns:
            dict: A dictionary containing all word lists in JSON format.
        """
        user = auth_manager.get_user_from_jwt()
        return UserWordList.get_json(user)

    @jwt_required()
    def put(self) -> dict:
        """Update the word lists of the authenticated user.

        This method retrieves the user from the JWT token and updates their word lists
        with the data provided in the JSON request body.

        Returns:
            Response: The response from the WordList.update method.
        """
        user = auth_manager.get_user_from_jwt()
        return UserWordList.update(user, request.json)


class AvailableWordLists(Resource):
    """A resource class for retrieving all available word lists with ACL filtering.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @jwt_required()
    def get(self) -> dict:
        """Retrieve all available word lists with ACL filtering.

        Returns:
            dict: A dictionary containing all word lists the user can access.
        """
        search = request.args.get("search")
        user = auth_manager.get_user_from_jwt()
        return WordList.get_all_json(search, user, acl_check=True)


class UserProductTypes(Resource):
    """Flask-RESTful resource that handles HTTP GET requests for retrieving all product types associated with the authenticated user.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("PUBLISH_ACCESS")
    def get(self) -> dict:
        """Retrieve all product types in JSON format.

        Returns:
            list: A list of all product types in JSON format.
        """
        return ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), acl_check=True)


class UserPublisherPresets(Resource):
    """A resource for handling user publisher presets.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("PUBLISH_ACCESS")
    def get(self) -> dict:
        """Retrieve all publisher presets in JSON format.

        Returns:
            list: A list of all publisher presets in JSON format.
        """
        return PublisherPreset.get_all_json(None)


class UserTotp(Resource):
    """Self-service TOTP (two-factor) enrollment for the authenticated user."""

    @jwt_required()
    def get(self) -> tuple[dict, HTTPStatus]:
        """Return whether TOTP is enabled for the current user.

        Returns:
            dict: The TOTP status.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        return {"enabled": bool(user.totp_secret)}, HTTPStatus.OK

    @jwt_required()
    def post(self) -> tuple[dict, HTTPStatus]:
        """Begin (no code) or confirm (with code) TOTP enrollment.

        Returns:
            dict: The otpauth URI to render as a QR code, or the enabled status.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        data = request.json or {}
        code = data.get("code")
        if not code:
            if user.totp_secret:
                return {"error": "TOTP is already enabled"}, HTTPStatus.BAD_REQUEST
            return {"otpauth_uri": totp_manager.begin_enrollment(user.username)}, HTTPStatus.OK
        if not totp_manager.confirm_enrollment(user, code):
            return {"error": "Invalid authentication code"}, HTTPStatus.BAD_REQUEST
        return {"enabled": True}, HTTPStatus.OK

    @jwt_required()
    def delete(self) -> tuple[dict, HTTPStatus]:
        """Disable TOTP for the current user (requires a currently valid code).

        Returns:
            dict: The enabled status.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        data = request.json or {}
        if not totp_manager.disable(user, data.get("code", "")):
            return {"error": "Invalid authentication code"}, HTTPStatus.BAD_REQUEST
        return {"enabled": False}, HTTPStatus.OK


class UserPasskeys(Resource):
    """Self-service passkey management for the authenticated user."""

    @jwt_required()
    def get(self) -> tuple[dict, HTTPStatus]:
        """List the current user's passkeys.

        Returns:
            dict: The passkey items (no key material).
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        return {"items": [credential.to_json() for credential in WebauthnCredential.get_for_user(user.id)]}, HTTPStatus.OK


class UserPasskeyRegisterBegin(Resource):
    """Start a passkey registration ceremony for the authenticated user."""

    @jwt_required()
    def post(self) -> tuple[dict, HTTPStatus]:
        """Return WebAuthn creation options and a challenge handle.

        Returns:
            dict: The options and challenge_id.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        try:
            return webauthn_manager.begin_registration(user), HTTPStatus.OK
        except ValueError as ex:
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST


class UserPasskeyRegisterFinish(Resource):
    """Finish a passkey registration ceremony for the authenticated user."""

    @jwt_required()
    def post(self) -> tuple[dict, HTTPStatus]:
        """Verify the authenticator response and store the new passkey.

        Returns:
            dict: The stored passkey.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        data = request.json or {}
        try:
            record = webauthn_manager.finish_registration(
                user,
                data.get("challenge_id", ""),
                data.get("credential") or {},
                data.get("name", ""),
            )
        except Exception as ex:
            return {"error": f"Passkey registration failed: {ex}"}, HTTPStatus.BAD_REQUEST
        return record.to_json(), HTTPStatus.OK


class UserPasskey(Resource):
    """Rename or remove one of the authenticated user's passkeys."""

    @jwt_required()
    def put(self, credential_id: int) -> tuple[dict, HTTPStatus]:
        """Rename a passkey.

        Args:
            credential_id (int): The passkey record ID.

        Returns:
            dict: Empty on success.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        data = request.json or {}
        if not WebauthnCredential.rename(credential_id, user.id, data.get("name", "")):
            return {"error": "Passkey not found"}, HTTPStatus.NOT_FOUND
        return {}, HTTPStatus.OK

    @jwt_required()
    def delete(self, credential_id: int) -> tuple[dict, HTTPStatus]:
        """Remove a passkey.

        Args:
            credential_id (int): The passkey record ID.

        Returns:
            dict: Empty on success.
        """
        user = auth_manager.get_user_from_jwt()
        if not user:
            return {"error": "not authorized"}, HTTPStatus.UNAUTHORIZED
        if not WebauthnCredential.remove(credential_id, user.id):
            return {"error": "Passkey not found"}, HTTPStatus.NOT_FOUND
        return {}, HTTPStatus.OK


def initialize(api: Api) -> None:
    """Initialize the API with user-related resources.

    This function adds several user-related resources to the provided API instance.
    The resources include word lists, product types, publisher presets and
    self-service security (TOTP, passkeys).

    Args:
        api (Api): The API instance to which the resources will be added.
    Resources:
        - UserHotkeys: Endpoint for user hotkeys at "/api/v1/users/my-hotkeys".
        - UserWordLists: Endpoint for user word lists at "/api/v1/users/my-word-lists".
        - AvailableWordLists: Endpoint for available word lists at "/api/v1/users/available-word-lists".
        - UserProductTypes: Endpoint for user product types at "/api/v1/users/my-product-types".
        - UserPublisherPresets: Endpoint for user publisher presets at "/api/v1/users/my-publisher-presets".
        - UserTotp: Self-service TOTP enrollment at "/api/v1/users/my-totp".
        - UserPasskeys/UserPasskey*: Self-service passkey management at "/api/v1/users/my-passkeys...".
    """
    api.add_resource(UserHotkeys, "/api/v1/users/my-hotkeys")
    api.add_resource(UserWordLists, "/api/v1/users/my-word-lists")
    api.add_resource(AvailableWordLists, "/api/v1/users/available-word-lists")
    api.add_resource(UserProductTypes, "/api/v1/users/my-product-types")
    api.add_resource(UserPublisherPresets, "/api/v1/users/my-publisher-presets")
    api.add_resource(UserTotp, "/api/v1/users/my-totp")
    api.add_resource(UserPasskeys, "/api/v1/users/my-passkeys")
    api.add_resource(UserPasskeyRegisterBegin, "/api/v1/users/my-passkeys/register-begin")
    api.add_resource(UserPasskeyRegisterFinish, "/api/v1/users/my-passkeys/register-finish")
    api.add_resource(UserPasskey, "/api/v1/users/my-passkeys/<int:credential_id>")
