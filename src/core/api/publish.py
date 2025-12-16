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
from http import HTTPStatus
from typing import Any

from flask import Response, request
from flask_restful import Api, Resource
from managers import auth_manager, log_manager, presenters_manager, publishers_manager
from managers.auth_manager import ACLCheck, auth_required
from managers.log_manager import logger
from model import product, product_type, publisher_preset
from model.permission import Permission


class Products(Resource):
    """A class representing the API endpoint for products.

    This class provides methods for retrieving and creating products.

    Attributes:
        Resource: A base class for implementing API resources.
    """

    @auth_required("PUBLISH_ACCESS")
    def get(self) -> tuple[dict, HTTPStatus]:
        """Retrieve a list of products based on the provided filters.

        Returns:
            A JSON response containing the list of products.
        """
        try:
            filters = {}
            if request.args.get("search"):
                filters["search"] = request.args["search"]
            if request.args.get("range"):
                filters["range"] = request.args["range"]
            if request.args.get("sort"):
                filters["sort"] = request.args["sort"]
            if request.args.get("date_from"):
                filters["date_from"] = request.args["date_from"]
            if request.args.get("date_to"):
                filters["date_to"] = request.args["date_to"]

            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 200)
            return product.Product.get_json(filters, offset, limit, auth_manager.get_user_from_jwt()), HTTPStatus.OK

        except Exception as ex:
            msg = "Get Products failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

    @auth_required("PUBLISH_CREATE")
    def post(self) -> product.Product:
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
    def get(self, product_id: int) -> dict:
        """Get the details of a product.

        Args:
            product_id (int): The ID of the product.

        Returns:
            dict: A JSON object containing the details of the product.
        """
        return product.Product.get_detail_json(product_id)

    @auth_required("PUBLISH_UPDATE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def put(self, product_id: int) -> None:
        """Update a product.

        Args:
            product_id (int): The ID of the product to be updated.
        """
        product.Product.update_product(product_id, request.json)

    @auth_required("PUBLISH_DELETE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def delete(self, product_id: int) -> None:
        """Delete a product.

        Args:
            product_id (int): The ID of the product to be deleted.
        """
        return product.Product.delete(product_id)


class PublishProduct(Resource):
    """A class representing the API resource for publishing a product.

    This class provides methods for publishing a product and handling the publish operation.

    Args:
        Resource: The base class for API resources.

    Returns:
        The result of the publish operation or an error message and status code if the operation fails.
    """

    @auth_required("PUBLISH_PRODUCT")
    def post(self, product_id: int, publisher_id: str) -> tuple[Any, HTTPStatus]:
        """Publish a product.

        Args:
            product_id (int): The ID of the product to be published.
            publisher_id (str): The ID of the publisher.

        Returns:
            If the product is successfully generated, returns the result of the publish operation.
            Otherwise, returns a tuple containing the error message and the status code.
        """
        product_data, status_code = presenters_manager.generate_product(product_id)
        if status_code == HTTPStatus.OK:
            return publishers_manager.publish(publisher_preset.PublisherPreset.find(publisher_id), product_data, None, None, None)
        return {"error": "Failed to generate product"}, status_code


class ProductsOverview(Resource):
    """A resource class for retrieving product overview.

    This class handles the GET request for retrieving product overview based on the provided product ID.
    It requires a valid JWT (JSON Web Token) in the request arguments for authentication and authorization.

    Attributes:
        Resource (class): The base class for creating API resources.
    """

    def get(self, product_id: int) -> Response:
        """Get the product data for the given product ID.

        Args:
            product_id (int): The ID of the product.

        Returns:
            Response: The product data as a response object.
        """
        if "jwt" not in request.args:
            err_msg = "Missing JWT"
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.UNAUTHORIZED, mimetype="text/plain")

        user = auth_manager.decode_user_from_jwt(request.args["jwt"])
        if user is None:
            err_msg = "Invalid JWT"
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.UNAUTHORIZED, mimetype="text/plain")

        permissions = user.get_permissions()
        if "PUBLISH_ACCESS" not in permissions:
            err_msg = "Insufficient permissions"
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.UNAUTHORIZED, mimetype="text/plain")

        if not product_type.ProductType.allowed_with_acl(product_id, user, see=False, access=True, modify=False):
            err_msg = "Unauthorized access attempt to Product Type"
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.UNAUTHORIZED, mimetype="text/plain")

        product_data, status_code = presenters_manager.generate_product(product_id)
        # logger.debug(f"=== GENERATED PRODUCT ({status_code}) ===\n{product_data}")
        if status_code != HTTPStatus.OK:
            err_msg = "Failed to generate product"
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.INTERNAL_SERVER_ERROR, mimetype="text/plain")

        if ("message_body" in product_data) and (request.args.get("ctrl", "0") == "0"):
            # it's always text response, mime_type is used for data content
            return Response(base64.b64decode(product_data["message_body"]), mimetype="text/plain")

        if product_data["data"] is None:
            err_msg = "No data available for preview!"
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.INTERNAL_SERVER_ERROR, mimetype="text/plain")

        return Response(base64.b64decode(product_data["data"]), mimetype=product_data["mime_type"])


def initialize(api: Api) -> None:
    """Initialize the publish module.

    Args:
        api (Api): The API instance to add resources to.
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
