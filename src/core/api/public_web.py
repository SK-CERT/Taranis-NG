"""Public-web node API endpoints.

Read-only access to published report products for a public-web feed node. The
node authenticates with the shared node ApiKey (``Authorization: ApiKey ...``)
exactly like the other nodes, via ``api_key_required("public_web")``.

The product detail is serialized directly from the database models into a small,
purpose-built structure (product info + report items with their attributes); no
presenter is involved.
"""

import io
from http import HTTPStatus

from flask import request, send_file
from flask_restful import Api, Resource
from managers.auth_manager import api_key_required
from managers.db_manager import db
from managers.log_manager import logger
from model.product import Product, ProductPublicWeb
from model.public_web import PublicWeb
from model.state import StateDefinition, StateEnum


def _serialize_web(web: PublicWeb) -> dict:
    """Serialize a web for the public-web app: hostname, config, and image kinds present."""
    return {
        "id": web.id,
        "name": web.name,
        "hostname": web.hostname,
        "enabled": bool(web.enabled),
        "config": web.config or {},
        "images": [image.kind for image in web.images],
    }


def _serialize_attribute(attribute) -> dict:  # noqa: ANN001
    """Serialize one report item attribute.

    The key is derived from the attribute group item title ("Affected systems"
    -> "affected_systems"). Repeated keys mean multiple values of the same
    attribute; consumers group them as needed.
    """
    group_item = attribute.attribute_group_item
    key = group_item.title.lower().replace(" ", "_") if group_item and group_item.title else ""
    return {
        "key": key,
        "value": attribute.value,
        "description": attribute.value_description,
    }


def _serialize_product(product: Product) -> dict:
    """Serialize a product with its report items and attributes for the public web feed."""
    report_items = []
    for report_item in product.report_items:
        report_type = report_item.report_item_type
        report_items.append(
            {
                "title": report_item.title,
                "title_prefix": report_item.title_prefix,
                "uuid": report_item.uuid,
                "created": report_item.created.isoformat() if report_item.created else None,
                "last_updated": report_item.last_updated.isoformat() if report_item.last_updated else None,
                "type": report_type.title if report_type else None,
                "type_description": report_type.description if report_type else None,
                "attributes": [_serialize_attribute(attribute) for attribute in report_item.attributes],
            },
        )

    user = product.user
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "created": product.created.isoformat() if product.created else None,
        "user": {"name": user.name, "username": user.username} if user else None,
        "report_items": report_items,
    }


def _find_published(product_id: int, web_id: int | None = None) -> Product | None:
    """Return a product only if it exists, is published, and is visible for the web."""
    product = Product.find(product_id)
    if not product:
        return None
    published = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
    if not published or product.state_id != published.id:
        return None
    if web_id is not None:
        has_any_target = db.session.query(ProductPublicWeb).filter_by(product_id=product_id).first() is not None
        if has_any_target:
            is_visible = db.session.query(ProductPublicWeb).filter_by(product_id=product_id, public_web_id=web_id).first() is not None
            if not is_visible:
                return None
    return product


class PublicWebProducts(Resource):
    """List published products for the public-web feed."""

    @api_key_required("public_web")
    def get(self, public_web_node=None):  # noqa: ANN001, ANN201
        """Return the most recent published products (newest first).

        Query params:
            limit (int): Max number of products (default 50, capped at 200).

        Returns:
            dict: ``{"total_count": int, "items": [{"id", "title", "created"}]}``
        """
        public_web_node.touch()
        try:
            limit = min(int(request.args.get("limit", 50)), 200)
        except (TypeError, ValueError):
            limit = 50
        try:
            web_id_arg = request.args.get("web_id")
            web_id = int(web_id_arg) if web_id_arg else None
        except (TypeError, ValueError):
            web_id = None

        products = Product.get_published(limit, web_id=web_id)
        items = [{"id": p.id, "title": p.title, "created": p.created.isoformat() if p.created else None} for p in products]
        logger.debug(f"Public-web '{public_web_node.name}': listed {len(items)} published products")
        return {"total_count": len(items), "items": items}, HTTPStatus.OK


class PublicWebProduct(Resource):
    """Serve a single published product for the public-web feed."""

    @api_key_required("public_web")
    def get(self, product_id, public_web_node=None):  # noqa: ANN001, ANN201
        """Return a published product with its report items and attributes.

        Args:
            product_id (int): The product id.
            public_web_node: The authenticated public-web node.

        Returns:
            dict: The serialized product, or 404 if it does not exist or is
            not published.
        """
        public_web_node.touch()
        try:
            web_id_arg = request.args.get("web_id")
            web_id = int(web_id_arg) if web_id_arg else None
        except (TypeError, ValueError):
            web_id = None

        product = _find_published(product_id, web_id=web_id)
        if product is None:
            logger.debug(f"Public-web '{public_web_node.name}': product {product_id} not found or not published")
            return {"error": "Product not found or not published"}, HTTPStatus.NOT_FOUND
        logger.info(f"Public-web '{public_web_node.name}': serving product {product.id} '{product.title}'")
        return _serialize_product(product), HTTPStatus.OK


class PublicWebWebs(Resource):
    """List the webs (branded feeds + their config) belonging to the authenticated node."""

    @api_key_required("public_web")
    def get(self, public_web_node=None):  # noqa: ANN001, ANN201
        """Return the node's webs, each with hostname, config and image kinds present.

        Returns:
            dict: ``{"total_count": int, "items": [ ...serialized webs... ]}``
        """
        public_web_node.touch()
        # Include disabled webs so the public-web app can return 503 for known
        # but disabled hostnames instead of serving a different web.
        items = [_serialize_web(web) for web in public_web_node.webs]
        logger.debug(f"Public-web '{public_web_node.name}': served config for {len(items)} web(s)")
        return {"total_count": len(items), "items": items}, HTTPStatus.OK


class PublicWebWebImage(Resource):
    """Serve one image (logo/favicon/preview) of a web to the public-web app."""

    @api_key_required("public_web")
    def get(self, web_id, kind, public_web_node=None):  # noqa: ANN001, ANN201
        """Return the binary image, or 404 if the web isn't this node's or has no such image."""
        public_web_node.touch()
        web = PublicWeb.find(web_id)
        if web is None or web.node_id != public_web_node.id:
            return {"error": "Web not found"}, HTTPStatus.NOT_FOUND
        image = web.get_image(kind)
        if image is None or image.data is None:
            return {"error": "Image not found"}, HTTPStatus.NOT_FOUND
        return send_file(io.BytesIO(image.data), mimetype=image.mime_type, download_name=image.filename or kind)


def initialize(api: Api) -> None:
    """Register the public-web node endpoints."""
    api.add_resource(PublicWebProducts, "/api/v1/public-web/products")
    api.add_resource(PublicWebProduct, "/api/v1/public-web/products/<int:product_id>")
    api.add_resource(PublicWebWebs, "/api/v1/public-web/webs")
    api.add_resource(PublicWebWebImage, "/api/v1/public-web/webs/<int:web_id>/images/<string:kind>")
