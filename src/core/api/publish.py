from flask_restful import Resource
from model import product
from model import product_type
from flask import request
from managers.auth_manager import auth_required, ACLCheck
from managers import auth_manager, presenters_manager, publishers_manager, audit_manager
from flask import Response
import base64
from model.permission import Permission
from model import publisher_preset


class Products(Resource):

    @auth_required('PUBLISH_ACCESS')
    def post(self):
        return product.Product.get_json(request.json['filter'], request.json['offset'], request.json['limit'],
                                        auth_manager.get_user_from_jwt())


class ProductNew(Resource):

    @auth_required('PUBLISH_CREATE')
    def post(self):
        user = auth_manager.get_user_from_jwt()
        new_product = product.Product.add_product(request.json, user.id)
        return new_product.id


class Product(Resource):

    @auth_required('PUBLISH_UPDATE', ACLCheck.PRODUCT_TYPE_ACCESS)
    def get(self, id):
        return product.Product.get_detail_json(id)

    @auth_required('PUBLISH_UPDATE', ACLCheck.PRODUCT_TYPE_MODIFY)
    def put(self, id):
        pass

    @auth_required('PUBLISH_DELETE', ACLCheck.PRODUCT_TYPE_MODIFY)
    def delete(self, id):
        return product.Product.delete(id)


class PublishProduct(Resource):

    @auth_required('PUBLISH_PRODUCT')
    def post(self):
        product_id = request.json['product_id']
        publisher_id = request.json['publisher_id']
        product_data, status_code = presenters_manager.generate_product(product_id)
        if status_code == 200:
            return publishers_manager.publish(publisher_preset.PublisherPreset.find(publisher_id), product_data, None,
                                              None, None)
        else:
            return "Failed to generate product", status_code


class ProductsOverview(Resource):

    def get(self, id):
        if 'jwt' in request.args:
            user = auth_manager.decode_user_from_jwt(request.args['jwt'])
            if user is not None:
                permissions = user.get_permissions()
                if 'PUBLISH_ACCESS' in permissions:
                    prod = product.Product.find(id)
                    if product_type.ProductType.allowed_with_acl(prod.product_type_id, user, False, True, False):
                        product_data, status_code = presenters_manager.generate_product(id)
                        if status_code == 200:
                            return Response(base64.b64decode(product_data['data']), mimetype=product_data['mime_type'])
                        else:
                            return "Failed to generate product", status_code
                    else:
                        audit_manager.store_auth_error_activity("Unauthorized access attempt to Product Type")
                else:
                    audit_manager.store_auth_error_activity("Insufficient permissions")
            else:
                audit_manager.store_auth_error_activity("Invalid JWT")
        else:
            audit_manager.store_auth_error_activity("Missing JWT")


def initialize(api):
    api.add_resource(Products, "/api/publish/products")
    api.add_resource(PublishProduct, "/api/publish/product")
    api.add_resource(ProductNew, "/api/publish/product/new")
    api.add_resource(Product, "/api/publish/product/<id>")
    api.add_resource(ProductsOverview, "/api/publish/product/overview/<id>")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")
