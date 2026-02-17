"""This module contains API endpoints for publishing products."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.user import User

import base64
import json
import mimetypes
import uuid
from http import HTTPStatus
from urllib.parse import quote

from flask import Response, request
from flask_restful import Api, Resource
from managers import auth_manager, log_manager, publishers_manager
from managers.auth_manager import ACLCheck, auth_required
from managers.cache_manager import redis_client
from managers.db_manager import db
from managers.log_manager import logger
from model.permission import Permission
from model.product import Product
from model.product_type import ProductType
from model.publisher_preset import PublisherPreset
from model.report_item import ReportItem
from remote.presenters_api import PresentersApi
from shared.schema.presenter import PresenterInput, PresenterInputSchema


class ProductsResource(Resource):
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
            return Product.get_json(filters, offset, limit, auth_manager.get_user_from_jwt()), HTTPStatus.OK

        except Exception as ex:
            msg = "Get Products failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

    @auth_required("PUBLISH_CREATE")
    def post(self) -> Product:
        """Create a new product.

        Returns:
            The ID of the newly created product.
        """
        user = auth_manager.get_user_from_jwt()
        new_product = Product.add_product(request.json, user)
        return new_product.id


class ProductResource(Resource):
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
        return Product.get_detail_json(product_id)

    @auth_required("PUBLISH_UPDATE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def put(self, product_id: int) -> None:
        """Update a product.

        Args:
            product_id (int): The ID of the product to be updated.
        """
        user = auth_manager.get_user_from_jwt()
        Product.update_product(product_id, request.json, user)

    @auth_required("PUBLISH_DELETE", ACLCheck.PRODUCT_TYPE_MODIFY)
    def delete(self, product_id: int) -> None:
        """Delete a product.

        Args:
            product_id (int): The ID of the product to be deleted.
        """
        return Product.delete(product_id)


def prepare_product(product_data: dict, user: User, token: str) -> tuple[dict, HTTPStatus, dict]:
    """Prepare a Product object and invoke the configured presenter to generate preview/publish data.

    Parameters:
        product_data (dict): Source payload describing the product.
        user (User): Authenticated user performing the operation (used for ACL checks).
        token (str): A unique token used as a temporary product id for previews.

    Returns:
        tuple[dict, HTTPStatus, dict]
    """
    product_id = product_data.get("id", -1)
    if product_id == -1:
        # Load product type
        product_type_id = product_data.get("product_type_id")
        prod_type = db.session.get(ProductType, product_type_id)

        if not prod_type:
            return {"error": "Product type not found"}, HTTPStatus.NOT_FOUND, None

        # Load report items from database
        report_items_list = []
        for item in product_data.get("report_items", []):
            loaded_item = ReportItem.find(item["id"])
            if loaded_item:
                report_items_list.append(loaded_item)

        # Create temporary product object (not saved to database)
        product = Product(
            id=token,
            title=product_data.get("title", ""),
            description=product_data.get("description", ""),
            product_type_id=product_type_id,
            state_id=product_data.get("state_id"),
            report_items=report_items_list,
        )

        product.product_type = prod_type
        product.user = user
    else:
        product = Product.find(product_id)

    if not ProductType.allowed_with_acl(product.product_type_id, user, see=False, access=True, modify=False):
        err_msg = "Unauthorized access attempt to Product Type"
        log_manager.store_auth_error_activity(err_msg)
        return {"error": err_msg}, HTTPStatus.UNAUTHORIZED

    presenter = product.product_type.presenter
    if not presenter:
        return {"error": "Product type has no presenter configured"}, HTTPStatus.BAD_REQUEST, None

    node = presenter.node
    if not node:
        return {"error": "Presenter has no node configured"}, HTTPStatus.BAD_REQUEST, None

    input_data = PresenterInput(presenter.type, product)
    input_schema = PresenterInputSchema()

    generated_data, status_code = PresentersApi(node.api_url, node.api_key).generate(input_schema.dump(input_data))

    if status_code != HTTPStatus.OK:
        err_msg = f"Failed to generate preview (status: {status_code})"
        logger.error(f"{err_msg}, data: {generated_data}")
        return {"error": err_msg}, HTTPStatus.INTERNAL_SERVER_ERROR, None

    return {}, HTTPStatus.OK, generated_data


class ProductGetPreview(Resource):
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
            cached_bytes = redis_client.get(cache_key)
            if not cached_bytes:
                err_msg = "Preview token not found, expired, or already processed."
                log_manager.store_auth_error_activity(err_msg)
                return Response(err_msg, HTTPStatus.NOT_FOUND, mimetype="text/plain")

            cached_data = json.loads(cached_bytes)
            preview_data = base64.b64decode(cached_data["data"])
            preview_mime = cached_data["mime"]
            preview_filename = cached_data.get("filename")

            logger.info(f"Preview token processed: {token}")
            response = Response(preview_data, mimetype=preview_mime)

            # Determine if content should be displayed inline or downloaded
            inline_types = ("text/", "application/pdf", "application/json")
            disposition = "inline" if any(preview_mime.startswith(itype) for itype in inline_types) else "attachment"

            # RFC 5987 encoding for non-ASCII filenames
            encoded_filename = quote(preview_filename)
            response.headers["Content-Disposition"] = f"{disposition}; filename*=UTF-8''{encoded_filename}"
            return response

        except Exception as ex:
            err_msg = "Preview failed to retrieve from Redis"
            logger.exception(f"{err_msg}: {ex}")
            return Response(err_msg, HTTPStatus.INTERNAL_SERVER_ERROR, mimetype="text/plain")


class ProductSetPreview(Resource):
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
        cache_ttl = 3600  # 1 hour, Expiration time in seconds (time-to-live)

        jwt = request.json.get("jwt")
        if not jwt:
            err_msg = "Missing JWT"
        else:
            user = auth_manager.decode_user_from_jwt(jwt)
            if user is None:
                err_msg = "Invalid JWT"
            elif "PUBLISH_ACCESS" not in user.get_permissions():
                err_msg = "Insufficient permissions"

        if err_msg:
            log_manager.store_auth_error_activity(err_msg)
            return {"error": err_msg}, HTTPStatus.UNAUTHORIZED

        try:
            product_data = request.json.get("product")
            token = str(uuid.uuid4())

            msg, status, generated_data = prepare_product(product_data, user, token)
            if status != HTTPStatus.OK:
                return msg, status

            # Determine which data to cache
            if ("message_body" in generated_data) and not (request.json.get("ctrl", False)):
                preview_data = base64.b64decode(generated_data["message_body"])
                # it's always text response, mime_type is used for data content in this case
                preview_mime = "text/plain"
            elif generated_data.get("data"):
                preview_data = base64.b64decode(generated_data["data"])
                preview_mime = generated_data["mime_type"]
            else:
                return {"error": "No data available for preview!"}, HTTPStatus.INTERNAL_SERVER_ERROR

            filename = product_data.get("title", "report")
            extension = mimetypes.guess_extension(preview_mime)
            # Store preview in Redis with automatic expiration (works across multiple workers)
            cache_key = f"preview:{token}"
            cache_value = json.dumps(
                {"data": base64.b64encode(preview_data).decode("utf-8"), "mime": preview_mime, "filename": filename + extension},
            )
            redis_client.setex(cache_key, cache_ttl, cache_value)

            logger.debug(f"Preview token generated: {token}")
            return {"token": token}, HTTPStatus.OK

        except Exception as ex:
            msg = f"Preview generation failed: {ex}"
            logger.exception(msg)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


class PublishProduct(Resource):
    """A resource class for publishing a product.

    This class handles the POST request for generating and publishing a product.

    Attributes:
        Resource (class): The base class for creating API resources.
    """

    @auth_required("PUBLISH_PRODUCT")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Generate and publish product.

        Returns:
            tuple: A JSON response with publishing results and HTTPStatus.
        """
        user = auth_manager.get_user_from_jwt()

        try:
            request_data = request.json
            product_data = request_data.get("product")
            token = str(uuid.uuid4())

            publisher_ids = request_data.get("publisher_ids", [])
            if not publisher_ids:
                return {"error": "No publishers specified"}, HTTPStatus.BAD_REQUEST

            msg, status, generated_data = prepare_product(product_data, user, token)
            if status != HTTPStatus.OK:
                return msg, status

            # Publish to all selected publishers
            results = []
            all_success = True
            for publisher_id in publisher_ids:
                preset = PublisherPreset.find(publisher_id)
                if not preset:
                    results.append({"publisher_id": publisher_id, "success": False, "error": "Publisher preset not found"})
                    continue

                result, status = publishers_manager.publish(preset, generated_data, None, None, None)
                if status == HTTPStatus.OK:
                    logger.info(f"Published '{product_data.get('title')}' to {preset.name}")
                else:
                    all_success = False
                    logger.error(f"Publish '{product_data.get('title')}' to {preset.name} failed: {result}")

                results.append(
                    {
                        "publisher_id": publisher_id,
                        "preset_name": preset.name,
                        "success": status == HTTPStatus.OK,
                        "status_code": status,
                        "result": result,
                    },
                )

            status = HTTPStatus.OK if all_success else HTTPStatus.INTERNAL_SERVER_ERROR
            return {"results": results, "overall_success": all_success}, status

        except Exception as ex:
            msg = f"Publish failed: {ex}"
            logger.exception(msg)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


def initialize(api: Api) -> None:
    """Initialize the publish module.

    Args:
        api (Api): The API instance to add resources to.
    """
    api.add_resource(ProductsResource, "/api/v1/publish/products")
    api.add_resource(ProductResource, "/api/v1/publish/products/<int:product_id>")
    api.add_resource(ProductSetPreview, "/api/v1/publish/products/preview")
    api.add_resource(ProductGetPreview, "/api/v1/publish/products/preview/<string:token>")
    api.add_resource(PublishProduct, "/api/v1/publish/products/publish")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")
