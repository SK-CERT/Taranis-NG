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
import json
import uuid
from http import HTTPStatus
from typing import Any

from flask import Response, request
from flask_restful import Api, Resource
from managers import auth_manager, log_manager, presenters_manager, publishers_manager
from managers.auth_manager import ACLCheck, auth_required
from managers.cache_manager import redis_client
from managers.db_manager import db
from managers.log_manager import logger
from model import product, product_type, publisher_preset, report_item
from model.permission import Permission
from remote.presenters_api import PresentersApi

from shared.schema.presenter import PresenterInput, PresenterInputSchema

# Cache expiration time (60 seconds)
PREVIEW_CACHE_TTL = 60


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
            if request.args.get("published"):
                filters["published"] = request.args["published"]
            if request.args.get("unpublished"):
                filters["unpublished"] = request.args["unpublished"]
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
        new_product = product.Product.add_product(request.json, user)
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
        user = auth_manager.get_user_from_jwt()
        product.Product.update_product(product_id, request.json, user)

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


class ProductsPreviewView(Resource):
    """A resource class for serving cached preview data.

    This class handles the GET request for retrieving a cached preview by token.

    Attributes:
        Resource (class): The base class for creating API resources.
    """

    def get(self, token: str) -> Response:
        """Retrieve and serve cached preview data.

        Args:
            token (str): The preview token.

        Returns:
            Response: The cached preview data as a response object.
        """
        err_msg = None

        if "jwt" not in request.args:
            err_msg = "Missing JWT"
        else:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is None:
                err_msg = "Invalid JWT"

        if err_msg:
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.UNAUTHORIZED, mimetype="text/plain")

        # Retrieve and immediately delete cached data from Redis (one-time use)
        cache_key = f"preview:{token}"
        try:
            cached_bytes = redis_client.getdel(cache_key)
            if not cached_bytes:
                err_msg = "Preview token not found or expired"
                log_manager.store_auth_error_activity(err_msg)
                return Response(err_msg, HTTPStatus.NOT_FOUND, mimetype="text/plain")

            cached_data = json.loads(cached_bytes)
            preview_data = base64.b64decode(cached_data["data"])
            preview_mime = cached_data["mime_type"]

            logger.debug(f"Served and deleted preview token: {token}")
            return Response(preview_data, mimetype=preview_mime)

        except Exception as ex:
            logger.exception(f"Failed to retrieve preview from Redis: {ex}")
            return Response("Failed to retrieve preview", HTTPStatus.INTERNAL_SERVER_ERROR, mimetype="text/plain")


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
        err_msg = None
        user = None

        if "jwt" not in request.args:
            err_msg = "Missing JWT"
        else:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is None:
                err_msg = "Invalid JWT"
            elif "PUBLISH_ACCESS" not in user.get_permissions():
                err_msg = "Insufficient permissions"
            elif not product_type.ProductType.allowed_with_acl(product_id, user, see=False, access=True, modify=False):
                err_msg = "Unauthorized access attempt to Product Type"

        if err_msg:
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, HTTPStatus.UNAUTHORIZED, mimetype="text/plain")

        product_data, status_code = presenters_manager.generate_product(product_id)

        response_data = None
        response_mime = None
        response_status = HTTPStatus.OK

        if status_code != HTTPStatus.OK:
            err_msg = "Failed to generate product"
            response_status = HTTPStatus.INTERNAL_SERVER_ERROR
        elif ("message_body" in product_data) and (request.args.get("ctrl", "0") == "0"):
            # it's always text response, mime_type is used for data content
            response_data = base64.b64decode(product_data["message_body"])
            response_mime = "text/plain"
        elif product_data.get("data") is None:
            err_msg = "No data available for preview!"
            response_status = HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            response_data = base64.b64decode(product_data["data"])
            response_mime = product_data["mime_type"]

        if err_msg:
            log_manager.store_auth_error_activity(err_msg)
            return Response(err_msg, response_status, mimetype="text/plain")

        return Response(response_data, mimetype=response_mime)


class ProductsPreview(Resource):
    """A resource class for generating product preview without saving to database.

    This class handles the POST request for generating product preview, caching it, and returning a token.
    The product is created in-memory only and not persisted to the database.
    Always generates fresh preview on every request.

    Attributes:
        Resource (class): The base class for creating API resources.
    """

    def post(self) -> tuple[dict, HTTPStatus]:
        """Generate fresh preview for product data without saving to database, return token.

        Returns:
            tuple: A JSON response with the token and HTTPStatus.
        """
        err_msg = None
        user = None

        if "jwt" not in request.args:
            err_msg = "Missing JWT"
        else:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is None:
                err_msg = "Invalid JWT"
            elif "PUBLISH_ACCESS" not in user.get_permissions():
                err_msg = "Insufficient permissions"

        if err_msg:
            log_manager.store_auth_error_activity(err_msg)
            return {"error": err_msg}, HTTPStatus.UNAUTHORIZED

        try:
            product_data = request.json

            # Load product type
            product_type_id = product_data.get("product_type_id")
            prod_type = db.session.get(product_type.ProductType, product_type_id)

            if not prod_type:
                return {"error": "Product type not found"}, HTTPStatus.NOT_FOUND

            # Load report items from database
            report_items_list = []
            for item in product_data.get("report_items", []):
                loaded_item = report_item.ReportItem.find(item["id"])
                if loaded_item:
                    report_items_list.append(loaded_item)

            # Generate unique token
            token = str(uuid.uuid4())

            # Create temporary product object (not saved to database)
            temp_product = product.Product(
                id=-1,
                title=product_data.get("title", ""),
                description=product_data.get("description", ""),
                product_type_id=product_type_id,
                state_id=product_data.get("state_id"),
                report_items=report_items_list,
            )

            # Use the token as temporary ID for the presenter
            temp_product.id = token
            temp_product.product_type = prod_type
            temp_product.user = user

            # Validate presenter configuration
            if not prod_type.presenter:
                return {"error": "Product type has no presenter configured"}, HTTPStatus.BAD_REQUEST
            if not prod_type.presenter.node:
                return {"error": "Presenter has no node configured"}, HTTPStatus.BAD_REQUEST

            presenter = prod_type.presenter
            node = presenter.node

            input_data = PresenterInput(presenter.type, temp_product)
            input_schema = PresenterInputSchema()

            # Always generate fresh preview
            generated_data, status_code = PresentersApi(node.api_url, node.api_key).generate(input_schema.dump(input_data))

            if status_code != HTTPStatus.OK:
                err_msg = f"Failed to generate preview (status: {status_code})"
                logger.error(f"{err_msg}, data: {generated_data}")
                return {"error": err_msg}, HTTPStatus.INTERNAL_SERVER_ERROR

            # Determine which data to cache
            if ("message_body" in generated_data) and (request.args.get("ctrl", "0") == "0"):
                preview_data = base64.b64decode(generated_data["message_body"])
                preview_mime = "text/plain"
            elif generated_data.get("data"):
                preview_data = base64.b64decode(generated_data["data"])
                preview_mime = generated_data["mime_type"]
            else:
                return {"error": "No data available for preview!"}, HTTPStatus.INTERNAL_SERVER_ERROR

            # Store preview in Redis with automatic expiration (works across multiple workers)
            cache_key = f"preview:{token}"
            cache_value = json.dumps(
                {
                    "data": base64.b64encode(preview_data).decode("utf-8"),
                    "mime_type": preview_mime,
                },
            )
            redis_client.setex(cache_key, PREVIEW_CACHE_TTL, cache_value)

            logger.info(f"Generated and cached fresh preview with token: {token}")
            return {"token": token}, HTTPStatus.OK

        except Exception as ex:
            msg = f"Preview generation failed: {ex}"
            logger.exception(msg)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


def initialize(api: Api) -> None:
    """Initialize the publish module.

    Args:
        api (Api): The API instance to add resources to.
    """
    api.add_resource(Products, "/api/v1/publish/products")
    api.add_resource(Product, "/api/v1/publish/products/<int:product_id>")
    api.add_resource(ProductsOverview, "/api/v1/publish/products/<int:product_id>/overview")
    api.add_resource(ProductsPreview, "/api/v1/publish/products/preview")
    api.add_resource(ProductsPreviewView, "/api/v1/publish/products/preview/<string:token>")
    api.add_resource(PublishProduct, "/api/v1/publish/products/<int:product_id>/publishers/<string:publisher_id>")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")
