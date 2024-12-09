"""This module defines several Flask-RESTful resources for handling user-related operations.

This includes user profiles, word lists, product types, and publisher presets. It also provides
an initialization function to add these resources to a Flask API instance.
"""

from flask_restful import Resource
from flask import request
from flask_jwt_extended import jwt_required

from managers import auth_manager
from managers.auth_manager import auth_required
from model import word_list, product_type, publisher_preset
from model.user import User


class UserProfile(Resource):
    """UserProfile resource for handling user profile related operations.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @jwt_required()
    def get(self):
        """Retrieve the profile information of the authenticated user.

        This method extracts the user information from the JWT (JSON Web Token)
        and returns the user's profile in JSON format.
        Returns:
            dict: A dictionary containing the user's profile information in JSON format.
        """
        user = auth_manager.get_user_from_jwt()
        return User.get_profile_json(user)

    @jwt_required()
    def put(self):
        """Update the profile of the authenticated user.

        This method retrieves the user from the JWT token and updates their profile
        with the data provided in the JSON request body.
        Returns:
            Response: The response from the User.update_profile method.
        """
        user = auth_manager.get_user_from_jwt()
        return User.update_profile(user, request.json)


class UserWordLists(Resource):
    """A resource class for handling user word lists.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("ASSESS_ACCESS")
    def get(self):
        """Retrieve all word lists in JSON format for the authenticated user.

        Returns:
            dict: A dictionary containing all word lists in JSON format.
        """
        return word_list.WordList.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class UserProductTypes(Resource):
    """Flask-RESTful resource that handles HTTP GET requests for retrieving all product types associated with the authenticated user.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("PUBLISH_ACCESS")
    def get(self):
        """Retrieve all product types in JSON format.

        Returns:
            list: A list of all product types in JSON format.
        """
        return product_type.ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class UserPublisherPresets(Resource):
    """A resource for handling user publisher presets.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("PUBLISH_ACCESS")
    def get(self):
        """Retrieve all publisher presets in JSON format.

        Returns:
            list: A list of all publisher presets in JSON format.
        """
        return publisher_preset.PublisherPreset.get_all_json(None)


def initialize(api):
    """Initialize the API with user-related resources.

    This function adds several user-related resources to the provided API instance.
    The resources include user profile, word lists, product types, and publisher presets.
    Args:
        api (Api): The API instance to which the resources will be added.
    Resources:
        - UserProfile: Endpoint for user profile at "/api/v1/users/my-profile".
        - UserWordLists: Endpoint for user word lists at "/api/v1/users/my-word-lists".
        - UserProductTypes: Endpoint for user product types at "/api/v1/users/my-product-types".
        - UserPublisherPresets: Endpoint for user publisher presets at "/api/v1/users/my-publisher-presets".
    """
    api.add_resource(UserProfile, "/api/v1/users/my-profile")
    api.add_resource(UserWordLists, "/api/v1/users/my-word-lists")
    api.add_resource(UserProductTypes, "/api/v1/users/my-product-types")
    api.add_resource(UserPublisherPresets, "/api/v1/users/my-publisher-presets")
