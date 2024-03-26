from flask_restful import Resource
from flask import request
from flask_jwt_extended import jwt_required

from managers import auth_manager
from managers.auth_manager import auth_required
from model import word_list, product_type, publisher_preset
from model.user import User


class UserProfile(Resource):

    @jwt_required
    def get(self):
        user = auth_manager.get_user_from_jwt()
        return User.get_profile_json(user)

    @jwt_required
    def put(self):
        user = auth_manager.get_user_from_jwt()
        return User.update_profile(user, request.json)


class UserWordLists(Resource):

    @auth_required('ASSESS_ACCESS')
    def get(self):
        return word_list.WordList.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class UserProductTypes(Resource):

    @auth_required('PUBLISH_ACCESS')
    def get(self):
        return product_type.ProductType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class UserPublisherPresets(Resource):

    @auth_required('PUBLISH_ACCESS')
    def get(self):
        return publisher_preset.PublisherPreset.get_all_json(None)


def initialize(api):
    api.add_resource(UserProfile, "/api/v1/users/my-profile")
    api.add_resource(UserWordLists, "/api/v1/users/my-word-lists")
    api.add_resource(UserProductTypes, "/api/v1/users/my-product-types")
    api.add_resource(UserPublisherPresets, "/api/v1/users/my-publisher-presets")
