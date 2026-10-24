"""Public-web node API endpoints.

Read-only access to published report products for a public-web feed node. The
node authenticates with the shared node ApiKey (``Authorization: ApiKey ...``)
exactly like the other nodes, via ``api_key_required("public_web")``.

The product detail is serialized directly from the database models into a small,
purpose-built structure (product info + report items with their attributes); no
presenter is involved. Link citations are rendered here, so a node only ever sees
numbered ``[n]`` references and the merged ``links`` list they index.

With ``?lang=`` the product is shown in that language (see ``managers/content_localizer.py``):
names and translatable texts are translated, outdated translations are passed over, and
labels arrive as extra fields. What a node compares - attribute keys, the report type's title,
the raw value of a choice constant (``source_value``) - stays as written.
"""

import io
from dataclasses import dataclass
from http import HTTPStatus

from flask import request, send_file
from flask_restful import Api, Resource
from managers import content_language, content_localizer
from managers.auth_manager import api_key_required
from managers.db_manager import db
from managers.link_references import CITING_TYPES, ReferenceIndex, build_index
from managers.log_manager import logger
from model.product import Product, ProductPublicWeb
from model.public_web import PublicWeb
from model.state import StateDefinition, StateEnum
from shared.schema.attribute import AttributeType


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


def _attribute_type(attribute) -> AttributeType | None:  # noqa: ANN001
    """Return the type of a report item attribute, if its definition is known."""
    return getattr(getattr(attribute.attribute_group_item, "attribute", None), "type", None)


@dataclass(frozen=True)
class _Rendering:
    """A report rendered in a language: the language and what its lookups need."""

    language: str
    report_item: object
    # Group item id -> {constant value -> its translations}, for choice attributes.
    constants: dict
    # The language the report type's labels and constants are written in.
    label_language: str | None


def _serialize_attribute(attribute, index: ReferenceIndex, local_numbers: dict, rendering: _Rendering | None = None) -> list[dict]:  # noqa: ANN001
    """Serialize one report item attribute into zero or more entries.

    The key is derived from the attribute group item title ("Affected systems"
    -> "affected_systems"). Repeated keys mean multiple values of the same
    attribute; consumers group them as needed. A multiple choice attribute keeps
    its ticked values newline-joined in a single row, so it fans out into one
    entry per ticked value rather than exposing the joined string.

    Citing text has its link references rendered to ``[n]``. A link is reported by
    its URL alone (its citation key stays internal), and a link without URL is left out.

    Rendered in a language, an entry gains ``label`` (the attribute's name in it), a translatable
    text is translated, and a choice constant gives its translation as ``value`` and itself as
    ``source_value``.
    """
    group_item = attribute.attribute_group_item
    key = group_item.title.lower().replace(" ", "_") if group_item and group_item.title else ""
    attribute_type = _attribute_type(attribute)
    type_name = attribute_type.name if attribute_type else None
    localized = {}
    constants = None
    if rendering is not None and group_item is not None:
        localized["label"] = content_localizer.label(
            group_item.translations,
            "title",
            group_item.title,
            rendering.language,
            rendering.label_language,
        )
        constants = rendering.constants.get(attribute.attribute_group_item_id)

    def choice(value: str | None) -> dict:
        if constants is None:
            return {"value": value}
        label = content_localizer.constant_label(value, constants, rendering.language, rendering.label_language)
        return {"value": label, "source_value": value}

    if attribute_type == AttributeType.MULTI_CHOICE:
        return [
            {"key": key, "type": type_name, **choice(selected), "description": attribute.value_description, **localized}
            for selected in (attribute.value or "").split("\n")
            if selected
        ]

    if attribute_type == AttributeType.LINK:
        url = (attribute.value or "").strip()
        return [{"key": key, "type": type_name, "value": url, "description": None, **localized}] if url else []

    value = attribute.value
    if rendering is not None:
        value = content_localizer.attribute_value(rendering.report_item, attribute, rendering.language, skip_outdated=True)
    if type_name in CITING_TYPES:
        value = index.render(value, local_numbers)
    entry = {"key": key, "type": type_name, "value": value, "description": attribute.value_description, **localized}
    if constants is not None:
        entry.update(choice(attribute.value))
    return [entry]


def _serialize_report_item(report_item, index: ReferenceIndex, local_numbers: dict, language: str | None, constants: dict) -> dict:  # noqa: ANN001
    """Serialize a report item with its attributes, in ``language`` when given."""
    report_type = report_item.report_item_type
    rendering = None
    if language:
        rendering = _Rendering(language, report_item, constants, report_type.label_language if report_type else None)
    entry = {
        "title": report_item.title,
        "title_prefix": report_item.title_prefix,
        "uuid": report_item.uuid,
        "created": report_item.created.isoformat() if report_item.created else None,
        "last_updated": report_item.last_updated.isoformat() if report_item.last_updated else None,
        "type": report_type.title if report_type else None,
        "type_description": report_type.description if report_type else None,
        "attributes": [
            entry for attribute in report_item.attributes for entry in _serialize_attribute(attribute, index, local_numbers, rendering)
        ],
    }
    if rendering is None:
        return entry
    for field in ("title", "title_prefix"):
        entry[field] = content_localizer.report_title(report_item, field, language, skip_outdated=True)
    if report_type is not None:
        source = report_type.label_language
        entry["type_label"] = content_localizer.label(report_type.translations, "title", report_type.title, language, source)
        entry["type_description_label"] = content_localizer.label(
            report_type.translations,
            "description",
            report_type.description,
            language,
            source,
        )
    return entry


def _serialize_product(product: Product, language: str | None = None) -> dict:
    """Serialize a product with its report items and attributes for the public web feed.

    Args:
        product (Product): A published product.
        language (str | None): The language to show it in; None shows it as written.

    Returns:
        dict: The product. In a language, it also says which language it is shown in
            (``language``, None when no language of the content is known) and which it can be read
            in (``available_languages``).
    """
    index, local_numbers = build_index(
        product.links,
        [[(link["key"], link["url"]) for link in report_item.links] for report_item in product.report_items],
    )
    constants = {}
    if language:
        report_types = {
            report_item.report_item_type.id: report_item.report_item_type
            for report_item in product.report_items
            if report_item.report_item_type
        }
        constants = content_localizer.constants_of(report_types.values())
    report_items = [
        _serialize_report_item(report_item, index, local, language, constants)
        for report_item, local in zip(product.report_items, local_numbers, strict=True)
    ]

    user = product.user
    result = {
        "id": product.id,
        "title": product.title,
        "description": index.render(product.description),
        "links": list(index.urls),
        "created": product.created.isoformat() if product.created else None,
        "user": {"name": user.name, "username": user.username} if user else None,
        "report_items": report_items,
    }
    if language:
        available = content_localizer.available_languages(product)
        result["title"] = content_localizer.product_text(product, "title", language, skip_outdated=True)[0]
        result["description"] = index.render(content_localizer.product_text(product, "description", language, skip_outdated=True)[0])
        result["language"] = content_localizer.shown_language(language, product.language, available)
        result["available_languages"] = available
    return result


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

        Query params:
            web_id (int): The web asking; a product published to other webs only is not found.
            lang (str): The language to show the product in (ISO 639-1); any other value is ignored.

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
        language = request.args.get("lang")
        if not content_language.is_language(language):
            language = None

        product = _find_published(product_id, web_id=web_id)
        if product is None:
            logger.debug(f"Public-web '{public_web_node.name}': product {product_id} not found or not published")
            return {"error": "Product not found or not published"}, HTTPStatus.NOT_FOUND
        logger.info(f"Public-web '{public_web_node.name}': serving product {product.id} '{product.title}'")
        return _serialize_product(product, language), HTTPStatus.OK


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
