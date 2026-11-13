"""Public-web node API endpoints.

Read-only access to published report products for a public-web feed node. The
node authenticates with the shared node ApiKey (``Authorization: ApiKey ...``)
exactly like the other nodes, via ``api_key_required("public_web")``.

The product detail is serialized directly from the database models into a small,
purpose-built structure (product info + report items with their attributes); no
presenter is involved. Link citations are rendered here, so a node only ever sees
numbered ``[n]`` references and the merged ``links`` list they index.

With ``?lang=`` the product is shown in that language where it has been translated into it (see
``managers/content_localizer.py``): names and translatable texts are translated, outdated
translations are passed over, and labels arrive as extra fields. ``lang`` is the language of the
visitor's page, so what is not translated into it stays as written - not English, as elsewhere.
Each report says which language it is shown in, and its labels follow it, so a node can put its
own words around a report in that language too. What a node compares - attribute keys, the report
type's title, the raw value of a choice constant (``source_value``) - stays as written.
"""

import io
from dataclasses import dataclass
from http import HTTPStatus

from flask import request, send_file
from flask_restful import Api, Resource
from managers import content_language, content_localizer
from managers.auth_manager import api_key_required
from managers.link_references import CITING_TYPES, ReferenceIndex, build_index
from managers.log_manager import logger
from model.product import Product
from model.public_web import PublicWeb
from model.public_web_template import PublicWebBuiltinTemplate, PublicWebTemplate
from model.state import StateDefinition, StateEnum
from shared.schema.attribute import AttributeType


def _node_disabled() -> tuple[dict, HTTPStatus]:
    """What a disabled node is told when it asks for anything but its webs."""
    return {"error": "This public-web node is disabled in Taranis"}, HTTPStatus.FORBIDDEN


def _serialize_web(web: PublicWeb) -> dict:
    """Serialize a web for the public-web app: hostname, config, and image kinds present.

    A disabled node's webs are all disabled, whatever their own switch says.
    """
    return {
        "id": web.id,
        "name": web.name,
        "hostname": web.hostname,
        "enabled": bool(web.enabled) and bool(web.node is None or web.node.enabled),
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


def _serialize_attribute(attribute, index: ReferenceIndex, local_links: dict, rendering: _Rendering | None = None) -> list[dict]:  # noqa: ANN001
    """Serialize one report item attribute into zero or more entries.

    The key is derived from the attribute group item title ("Affected systems"
    -> "affected_systems"). Repeated keys mean multiple values of the same
    attribute; consumers group them as needed. A multiple choice attribute keeps
    its ticked values newline-joined in a single row, so it fans out into one
    entry per ticked value rather than exposing the joined string.

    Citing text has its link references rendered to ``[n]``. A link is reported by
    its URL alone (its citation key stays internal), and a link without URL is left out.

    Rendered in a language, ``label`` and ``group`` name the attribute and its group in it, a
    translatable text is translated, and a choice constant gives its translation as ``value`` and
    itself as ``source_value``.
    """
    group_item = attribute.attribute_group_item
    key = group_item.title.lower().replace(" ", "_") if group_item and group_item.title else ""
    attribute_type = _attribute_type(attribute)
    group = getattr(group_item, "attribute_group", None)
    # Where the attribute sits in its report item type, and how it is labelled there:
    # report templates show attributes as the analyst saw them.
    entry = {
        "key": key,
        "attribute_type": attribute_type.name if attribute_type else None,
        "label": group_item.title if group_item else None,
        "group": group.title if group else None,
        "multiple": group_item.max_occurrence != 1 if group_item else None,
        "order": [getattr(group, "index", None) or 0, getattr(group_item, "index", None) or 0],
    }
    constants = None
    if rendering is not None and group_item is not None:
        language, source = rendering.language, rendering.label_language
        entry["label"] = content_localizer.label(group_item.translations, "title", group_item.title, language, source, via_english=False)
        if group is not None:
            entry["group"] = content_localizer.label(group.translations, "title", group.title, language, source, via_english=False)
        constants = rendering.constants.get(attribute.attribute_group_item_id)

    def choice(value: str | None) -> dict:
        if constants is None:
            return {"value": value}
        label = content_localizer.constant_label(value, constants, rendering.language, rendering.label_language, via_english=False)
        return {"value": label, "source_value": value}

    if attribute_type == AttributeType.MULTI_CHOICE:
        selected_values = [selected for selected in (attribute.value or "").split("\n") if selected]
        return [{**entry, **choice(selected), "description": attribute.value_description} for selected in selected_values]

    if attribute_type == AttributeType.LINK:
        url = (attribute.value or "").strip()
        return [{**entry, "value": url, "description": None}] if url else []

    value = attribute.value
    if rendering is not None:
        value = content_localizer.attribute_value(
            rendering.report_item,
            attribute,
            rendering.language,
            skip_outdated=True,
            via_english=False,
        )
    if entry["attribute_type"] in CITING_TYPES:
        value = index.render(value, local_links)
    serialized = {**entry, "value": value, "description": attribute.value_description}
    if constants is not None:
        serialized.update(choice(attribute.value))
    return [serialized]


def _form_position(attribute) -> tuple:  # noqa: ANN001
    """Where an attribute value sits in its report's form: by group, group item and id."""
    group_item = attribute.attribute_group_item
    group = getattr(group_item, "attribute_group", None)
    return (
        getattr(group, "index", None) or 0,
        getattr(group_item, "index", None) or 0,
        getattr(attribute, "id", None) is None,
        getattr(attribute, "id", None) or 0,
    )


def _serialize_report_item(report_item, index: ReferenceIndex, local_links: dict, language: str | None, constants: dict) -> dict:  # noqa: ANN001
    """Serialize a report item with its attributes, in ``language`` when given.

    The attributes come in form order, the order they are read in: rendering their citations in
    it numbers the links in the order the text cites them.

    In a language, the report says which it is shown in (``language``, None when its own is not
    known): ``language``, else English, else the one it was written in, whichever it has first. Its
    labels and constants are in that one too, and a text not translated into it is shown as
    written, so that the report reads in a single language.
    """
    report_type = report_item.report_item_type
    rendering = None
    shown = None
    if language:
        available = content_localizer.report_languages(report_item)
        shown = content_localizer.shown_language(language, report_item.language, available)
        language = shown or language
        rendering = _Rendering(language, report_item, constants, report_type.label_language if report_type else None)
    entry = {
        "title": report_item.title,
        "title_prefix": report_item.title_prefix,
        "uuid": report_item.uuid,
        "created": report_item.created.isoformat() if report_item.created else None,
        "last_updated": report_item.last_updated.isoformat() if report_item.last_updated else None,
        "type": report_type.title if report_type else None,
        "type_id": report_type.id if report_type else None,
        "type_description": report_type.description if report_type else None,
        "attributes": [
            entry
            for attribute in sorted(report_item.attributes, key=_form_position)
            for entry in _serialize_attribute(attribute, index, local_links, rendering)
        ],
    }
    if rendering is None:
        return entry
    entry["language"] = shown
    # Read, in part, from AI translations (reviewed or not); then readers learn what it was written in.
    entry["ai_translation"] = content_localizer.report_ai_translation(report_item, shown)
    entry["original_language"] = report_item.language
    for field in ("title", "title_prefix"):
        entry[field] = content_localizer.report_title(report_item, field, language, skip_outdated=True, via_english=False)
    if report_type is not None:
        source = report_type.label_language
        entry["type_label"] = content_localizer.label(
            report_type.translations,
            "title",
            report_type.title,
            language,
            source,
            via_english=False,
        )
        entry["type_description_label"] = content_localizer.label(
            report_type.translations,
            "description",
            report_type.description,
            language,
            source,
            via_english=False,
        )
    return entry


def _serialize_product(product: Product, language: str | None = None) -> dict:
    """Serialize a product with its report items and attributes for the public web feed.

    Args:
        product (Product): A published product.
        language (str | None): The language to show it in; None shows it as written.

    Returns:
        dict: The product. In a language, it also says which language it is shown in
            (``language``, None when no language of the content is known), which it can be read
            in (``available_languages``), whether any of it is read from an AI translation and if a
            person reviewed them all (``ai_translation``: "unreviewed", "reviewed" or None), and what
            it was written in (``original_language``).
    """
    index, local_links = build_index(
        product.links,
        [[(link["key"], link["url"]) for link in report_item.links] for report_item in product.report_items],
    )
    title, title_language = product.title, None
    description, description_language = product.description, None
    constants = {}
    if language:
        # Like a report: in ``language``, else English, else as written.
        title, title_language = content_localizer.product_text(product, "title", language, skip_outdated=True)
        description, description_language = content_localizer.product_text(product, "description", language, skip_outdated=True)
        report_types = {
            report_item.report_item_type.id: report_item.report_item_type
            for report_item in product.report_items
            if report_item.report_item_type
        }
        constants = content_localizer.constants_of(report_types.values())
    # Rendered in reading order, which numbers the links: the description shown, then the reports.
    description = index.render(description)
    report_items = [
        _serialize_report_item(report_item, index, local, language, constants)
        for report_item, local in zip(product.report_items, local_links, strict=True)
    ]

    user = product.user
    preset = product.product_preset
    result = {
        "id": product.id,
        "title": title,
        # What the product is published as; public-web picks the product template by it.
        "product_preset": {"id": preset.id, "title": preset.name} if preset else None,
        "description": description,
        "links": index.urls,
        "created": product.created.isoformat() if product.created else None,
        "user": {"name": user.name, "username": user.username} if user else None,
        "report_items": report_items,
    }
    if language:
        available = content_localizer.available_languages(product)
        result["language"] = content_localizer.shown_language(language, product.language, available)
        result["available_languages"] = available
        # Read, in part, from AI translations: the page says so, whether a person reviewed them,
        # and what it was written in.
        result["ai_translation"] = content_localizer.ai_translation(
            [
                content_localizer.product_text_ai_translation(product, "title", title_language),
                content_localizer.product_text_ai_translation(product, "description", description_language),
                *(item.get("ai_translation") for item in report_items),
            ],
        )
        result["original_language"] = product.language or next(
            (item["original_language"] for item in report_items if item.get("ai_translation")),
            None,
        )
    return result


def _find_published(product_id: int, web_id: int | None = None) -> Product | None:
    """Return a product only if it exists, is published, and is visible for the web."""
    product = Product.find(product_id)
    if not product:
        return None
    published = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
    if not published or product.state_id != published.id:
        return None
    if not product.shown_on_web(web_id):
        return None
    return product


class PublicWebProducts(Resource):
    """List published products for the public-web feed."""

    @api_key_required("public_web")
    def get(self, public_web_node=None):  # noqa: ANN001, ANN201
        """Return published products, newest first, a page at a time.

        Query params:
            limit (int): Max number of products (default 50, capped at 200).
            offset (int): How many of the newest to skip (default 0).
            web_id (int): The web asking; products published to other webs only are left out.
            full (bool): Each product whole, as ``products/<id>`` serves it, so that a node can
                load every product in a few requests.
            lang (str): With ``full``, the language to show the products in (ISO 639-1).

        Returns:
            dict: ``{"total_count": int, "items": [...]}``: how many products are published in
                all, and this page of them, ``{"id", "title", "created"}`` each unless ``full``.
                403 for a disabled node.
        """
        public_web_node.touch()
        if not public_web_node.enabled:
            return _node_disabled()
        try:
            limit = min(int(request.args.get("limit", 50)), 200)
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = max(int(request.args.get("offset", 0)), 0)
        except (TypeError, ValueError):
            offset = 0
        try:
            web_id_arg = request.args.get("web_id")
            web_id = int(web_id_arg) if web_id_arg else None
        except (TypeError, ValueError):
            web_id = None
        full = request.args.get("full", "").lower() in ("1", "true")
        language = request.args.get("lang")
        if not content_language.is_language(language):
            language = None

        products, total = Product.get_published(limit, web_id=web_id, offset=offset, with_content=full)
        if full:
            items = [_serialize_product(product, language) for product in products]
        else:
            items = [{"id": p.id, "title": p.title, "created": p.created.isoformat() if p.created else None} for p in products]
        logger.debug(f"Public-web '{public_web_node.name}': listed {len(items)} of {total} published products from {offset}")
        return {"total_count": total, "items": items}, HTTPStatus.OK


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
            not published; 403 for a disabled node.
        """
        public_web_node.touch()
        if not public_web_node.enabled:
            return _node_disabled()
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


class PublicWebTemplates(Resource):
    """The report templates, for public-web to render products with: the custom ones and the built-ins switched off."""

    @api_key_required("public_web")
    def get(self, public_web_node=None):  # noqa: ANN001, ANN201
        """Return every report template, and the built-in ones switched off.

        Returns:
            dict: ``{"total_count": int, "items": [{"id", "name", "product_preset_id",
            "report_item_type_id", "source", "require_tlp_clear"}], "disabled_builtins": [name]}``;
            403 for a disabled node.
        """
        public_web_node.touch()
        if not public_web_node.enabled:
            return _node_disabled()
        items = [PublicWebTemplate.node_json(template) for template in PublicWebTemplate.get_all()]
        return {"total_count": len(items), "items": items, "disabled_builtins": PublicWebBuiltinTemplate.disabled()}, HTTPStatus.OK


class PublicWebWebs(Resource):
    """List the webs (branded feeds + their config) belonging to the authenticated node."""

    @api_key_required("public_web")
    def get(self, public_web_node=None):  # noqa: ANN001, ANN201
        """Return the node's webs, each with hostname, config and image kinds present.

        Returns:
            dict: ``{"total_count": int, "items": [ ...serialized webs... ]}``; every web
            disabled while the node is.
        """
        public_web_node.touch()
        # Include disabled webs so the public-web app can return 503 for known
        # but disabled hostnames instead of serving a different web. A disabled
        # node still gets its webs, all disabled, so it answers 503 for each.
        items = [_serialize_web(web) for web in public_web_node.webs]
        logger.debug(f"Public-web '{public_web_node.name}': served config for {len(items)} web(s)")
        return {"total_count": len(items), "items": items}, HTTPStatus.OK


class PublicWebWebImage(Resource):
    """Serve one image (logo/favicon/preview) of a web to the public-web app."""

    @api_key_required("public_web")
    def get(self, web_id, kind, public_web_node=None):  # noqa: ANN001, ANN201
        """Return the binary image, or 404 if the web isn't this node's or has no such image; 403 for a disabled node."""
        public_web_node.touch()
        if not public_web_node.enabled:
            return _node_disabled()
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
    api.add_resource(PublicWebTemplates, "/api/v1/public-web/templates")
    api.add_resource(PublicWebWebs, "/api/v1/public-web/webs")
    api.add_resource(PublicWebWebImage, "/api/v1/public-web/webs/<int:web_id>/images/<string:kind>")
