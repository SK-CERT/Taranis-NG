"""This module contains API endpoints for publishing products.

The module includes the following classes:
- Products: Represents the API endpoint for retrieving and creating products.
- Product: Represents a single product resource.
- PublishProduct: Represents the API resource for publishing a product.
- ProductsOverview: Represents the resource for retrieving product overview.

Each class has its own methods for handling different HTTP requests.

The module also includes an initialization function to add the resources to the API instance.
"""

import base64
from flask import Response
from flask import request
from flask_restful import Resource

from managers import auth_manager, presenters_manager, publishers_manager, log_manager
from managers.log_manager import logger
from managers.auth_manager import auth_required, ACLCheck
from model import product, product_type, publisher_preset
from model.permission import Permission


class Products(Resource):
    """A class representing the API endpoint for products.

    This class provides methods for retrieving and creating products.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("PUBLISH_ACCESS")
    def get(self):
        """Retrieve a list of products based on the provided filters.

        Returns:
            A JSON response containing the list of products.
        """
        try:
            filter = {}
            if "search" in request.args and request.args["search"]:
                filter["search"] = request.args["search"]
            if "range" in request.args and request.args["range"]:
                filter["range"] = request.args["range"]
            if "sort" in request.args and request.args["sort"]:
                filter["sort"] = request.args["sort"]

            offset = None
            if "offset" in request.args and request.args["offset"]:
                offset = int(request.args["offset"])

            limit = 50
            if "limit" in request.args and request.args["limit"]:
                limit = min(int(request.args["limit"]), 200)
        except Exception as ex:
            msg = "Get Products failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400

        return product.Product.get_json(filter, offset, limit, auth_manager.get_user_from_jwt())

    @auth_required("PUBLISH_CREATE")
    def post(self):
        """Create a new product.

        Returns:
            The ID of the newly created product.
        """
        user = auth_manager.get_user_from_jwt()
        new_product = product.Product.add_product(request.json, user.id)
        return new_product.id


class Product(Resource):
    """Represent a product resource.

    Args:
        Resource -- The base class for API resources.
    """

    @auth_required("PUBLISH_ACCESS", ACLCheck.PRODUCT_TYPE_ACCESS)
    def get(self, product_id):
        """Get the details of a product.

        Args:
            product_id (int): The ID of the product.

        Returns:
            dict: A JSON object containing the details of the product.
        """
        return product.Product.get_detail_json(product_id)

    @auth_required("PUBLISH_UPDATE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def put(self, product_id):
        """Update a product.

        Args:
            product_id (int): The ID of the product to be updated.
        """
        product.Product.update_product(product_id, request.json)

    @auth_required("PUBLISH_DELETE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def delete(self, product_id):
        """Delete a product.

        Args:
            product_id (int): The ID of the product to be deleted.
        """
        return product.Product.delete(product_id)


class PublishProduct(Resource):
    """A class representing the API resource for publishing a product.

    This class provides methods for publishing a product and handling the publish operation.

    Args:
        Resource -- The base class for API resources.

    Returns:
        The result of the publish operation or an error message and status code if the operation fails.
    """

    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id, publisher_id):
        """Publish a product.

        Args:
            product_id -- The ID of the product to be published.
            publisher_id -- The ID of the publisher.

        Returns:
            If the product is successfully generated, returns the result of the publish operation.
            Otherwise, returns a tuple containing the error message and the status code.
        """
        product_data, status_code = presenters_manager.generate_product(product_id)
        if status_code == 200:
            return publishers_manager.publish(publisher_preset.PublisherPreset.find(publisher_id), product_data, None, None, None)
        else:
            return "Failed to generate product", status_code


class ProductsOverview(Resource):
    """A resource class for retrieving product overview.

    This class handles the GET request for retrieving product overview based on the provided product ID.
    It requires a valid JWT (JSON Web Token) in the request arguments for authentication and authorization.

    Attributes:
        Resource (class): The base class for creating API resources.
    """

    def get(self, product_id):
        """Get the product data for the given product ID.

        Args:
            product_id (str): The ID of the product.

        Returns:
            Response: The product data as a response object.
        """
        if "jwt" in request.args:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is not None:
                permissions = user.get_permissions()
                if "PUBLISH_ACCESS" in permissions:
                    if product_type.ProductType.allowed_with_acl(product_id, user, False, True, False):
                        product_data, status_code = presenters_manager.generate_product(product_id)
                        if status_code == 200:
                            if ("message_body" in product_data) and (request.args.get("ctrl", "0") == "0"):
                                # it's always text response, mime_type is used for data content
                                return Response(base64.b64decode(product_data["message_body"]), mimetype="text/plain")
                            elif product_data["data"] is None:
                                return Response("No data available for preview!", mimetype="text/plain")
                            else:
                                return Response(base64.b64decode(product_data["data"]), mimetype=product_data["mime_type"])
                        else:
                            return "Failed to generate product", status_code
                    else:
                        log_manager.store_auth_error_activity("Unauthorized access attempt to Product Type")
                else:
                    log_manager.store_auth_error_activity("Insufficient permissions")
            else:
                log_manager.store_auth_error_activity("Invalid JWT")
        else:
            log_manager.store_auth_error_activity("Missing JWT")


def initialize(api):
    """Initialize the publish module.

    Args:
        api -- The API instance to add resources to.
    """
    api.add_resource(Products, "/api/v1/publish/products")
    api.add_resource(Product, "/api/v1/publish/products/<int:product_id>")
    api.add_resource(ProductsOverview, "/api/v1/publish/products/<int:product_id>/overview")
    api.add_resource(PublishProduct, "/api/v1/publish/products/<int:product_id>/publishers/<string:publisher_id>")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")
