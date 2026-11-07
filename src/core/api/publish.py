"""This module contains API endpoints for publishing products."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.product_format import ProductFormat
    from model.user import User

import base64
import json
import mimetypes
import uuid
from http import HTTPStatus
from urllib.parse import quote

from api import tag
from flask import Response, request
from flask_restful import Api, Resource
from managers import auth_manager, content_language, content_localizer, llm_manager, log_manager, publishers_manager
from managers.auth_manager import ACLCheck, auth_required
from managers.cache_manager import redis_client
from managers.db_manager import db
from managers.link_references import render_presenter_input
from managers.log_manager import logger
from model.glossary import GlossaryEntry
from model.permission import Permission
from model.product import Product
from model.product_preset import ProductPreset
from model.report_item import ReportItem
from model.translation import PRODUCT_FIELDS
from remote.presenters_api import PresentersApi
from shared.schema.presenter import PresenterInput, PresenterInputSchema

# How long a preview ticket stays valid.
PREVIEW_TICKET_TTL_SECONDS = 600
# How many times one ticket may be redeemed. Not 1: Chrome fetches the resource once to render a
# PDF and again to save it (seen 2026-09-21), so a strictly single-use ticket broke saving an
# opened preview. Still capped, so a URL that leaks (proxy logs, browser history, a shared link)
# can serve the report at most a couple more times, and only until the ticket expires.
PREVIEW_TICKET_MAX_REDEMPTIONS = 3


def _product_preset_refused(product_data: dict | None, user: User) -> tuple[dict, HTTPStatus] | None:
    """Refuse a product whose product preset does not exist, or that the user may not use."""
    product_preset_id = (product_data or {}).get("product_preset_id")
    if not isinstance(product_preset_id, int) or ProductPreset.find(product_preset_id) is None:
        return {"error": "Product preset not found"}, HTTPStatus.BAD_REQUEST
    if not ProductPreset.allowed_with_acl(product_preset_id, user, see=False, access=True, modify=False):
        err_msg = "Unauthorized access attempt to Product preset"
        log_manager.store_auth_error_activity(err_msg)
        return {"error": err_msg}, HTTPStatus.FORBIDDEN
    return None


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
            if (request.args.get("product_preset_id") or "").isdigit():
                filters["product_preset_id"] = request.args["product_preset_id"]
            if request.args.get("date_from"):
                filters["date_from"] = request.args["date_from"]
            if request.args.get("date_to"):
                filters["date_to"] = request.args["date_to"]
            filters.update(tag.list_filter(request.args))

            offset = int(request.args.get("offset", 0))
            limit = min(int(request.args.get("limit", 50)), 200)
            return Product.get_json(filters, offset, limit, auth_manager.get_user_from_jwt()), HTTPStatus.OK

        except Exception as ex:
            msg = "Get Products failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

    @auth_required("PUBLISH_CREATE")
    def post(self) -> int | tuple[dict, HTTPStatus]:
        """Create a new product.

        Returns:
            The ID of the newly created product.
        """
        user = auth_manager.get_user_from_jwt()
        refused = _product_preset_refused(request.json, user)
        if refused:
            return refused
        try:
            new_product = Product.add_product(request.json, user)
        except ValueError as ex:
            # A language code, translated title or tag that is not valid.
            db.session.rollback()
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        _reset_public_web_cache_if_published_changed(new_state_id=new_product.state_id)
        return new_product.id


class ProductResource(Resource):
    """Represent a product resource.

    Args:
        Resource -- The base class for API resources.
    """

    @auth_required("PUBLISH_ACCESS", ACLCheck.PRODUCT_PRESET_ACCESS)
    def get(self, product_id: int) -> dict:
        """Get the details of a product.

        Args:
            product_id (int): The ID of the product.

        Returns:
            dict: A JSON object containing the details of the product.
        """
        return Product.get_detail_json(product_id)

    @auth_required("PUBLISH_UPDATE", ACLCheck.PRODUCT_PRESET_MODIFY)
    def put(self, product_id: int) -> tuple[dict, HTTPStatus] | None:
        """Update a product.

        Args:
            product_id (int): The ID of the product to be updated.
        """
        user = auth_manager.get_user_from_jwt()
        refused = _product_preset_refused(request.json, user)
        if refused:
            return refused
        original_product = Product.find(product_id)
        original_state_id = original_product.state_id if original_product else None
        try:
            Product.update_product(product_id, request.json, user)
        except ValueError as ex:
            # A language code, translated title or tag that is not valid; nothing is stored.
            db.session.rollback()
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        updated_product = Product.find(product_id)
        updated_state_id = updated_product.state_id if updated_product else None
        _reset_public_web_cache_if_published_changed(old_state_id=original_state_id, new_state_id=updated_state_id)
        return None

    @auth_required("PUBLISH_DELETE", ACLCheck.PRODUCT_PRESET_MODIFY)
    def delete(self, product_id: int) -> None:
        """Delete a product.

        Args:
            product_id (int): The ID of the product to be deleted.
        """
        product = Product.find(product_id)
        was_published = _is_published_state(product.state_id) if product else False
        result = Product.delete(product_id)
        if was_published:
            _notify_public_web_nodes()
        return result


def _public_web_enabled() -> bool:
    """Whether any public-web node is configured; see public_web_manager."""
    try:
        from managers import public_web_manager

        return public_web_manager.public_web_enabled()
    except Exception as ex:
        logger.debug(f"Could not determine whether public-web is enabled: {ex}")
        return False


def _is_published_state(state_id: int | None) -> bool:
    """Return whether a product state is the public-web published state."""
    if not _public_web_enabled():
        return False
    if state_id is None:
        return False
    try:
        from model.state import StateDefinition, StateEnum

        published_state = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
    except Exception as ex:
        logger.debug(f"Could not determine the published state: {ex}")
        return False
    return bool(published_state and state_id == published_state.id)


def _notify_public_web_nodes() -> None:
    """Best-effort: tell every reachable public-web node to drop its cached feed data.

    Nodes that are not currently running are skipped rather than dialled and
    waited on; see :func:`managers.public_web_manager.notify_nodes`.
    """
    if not _public_web_enabled():
        return
    try:
        from managers import public_web_manager
        from model.public_web_node import PublicWebNode

        public_web_manager.notify_nodes(PublicWebNode.get_all())
    except Exception as ex:
        logger.debug(f"Could not notify public-web nodes about a product change: {ex}")


def _reset_public_web_cache_if_published_changed(
    old_state_id: int | None = None,
    new_state_id: int | None = None,
) -> None:
    """Reset public-web cache when a mutation touches the published state.

    This fires when a product is already published and is edited, or when a
    product transitions from or to the published state.
    """
    if not _public_web_enabled():
        return
    try:
        from model.state import StateDefinition, StateEnum

        published_state = StateDefinition.get_by_name(StateEnum.PUBLISHED.value)
        if not published_state:
            return
        published_id = published_state.id
    except Exception:
        return

    candidates = [old_state_id, new_state_id]
    if any(candidate == published_id for candidate in candidates if candidate is not None):
        _notify_public_web_nodes()


def _submitted_translations(product_data: dict) -> dict[str, dict[str, str]]:
    """Texts per language and field of a product not saved yet, from its ``translations``."""
    translations = product_data.get("translations") or {}
    if not isinstance(translations, dict):
        return {}
    texts: dict[str, dict[str, str]] = {}
    for language, entry in translations.items():
        for field, text in entry.items() if isinstance(entry, dict) else ():
            value = text.get("value") if isinstance(text, dict) else None
            if field in PRODUCT_FIELDS and isinstance(value, str) and value:
                texts.setdefault(language, {})[field] = value
    return texts


def load_product(product_data: dict, user: User, token: str) -> tuple[dict, HTTPStatus, Product | None, dict | None]:
    """The product to render: the stored one, or a temporary object for one not saved yet.

    Parameters:
        product_data (dict): Source payload describing the product.
        user (User): Authenticated user performing the operation (used for ACL checks).
        token (str): A unique token used as a temporary product id for previews.

    Returns:
        tuple[dict, HTTPStatus, Product | None, dict | None]: an error and its status, or the
            product and, for one not saved yet, its texts per language.
    """
    translations = None
    product_id = product_data.get("id", -1)
    if product_id == -1:
        product_preset = ProductPreset.find(product_data.get("product_preset_id"))
        if not product_preset:
            return {"error": "Product preset not found"}, HTTPStatus.NOT_FOUND, None, None

        report_items_list = []
        for item in product_data.get("report_items", []):
            loaded_item = ReportItem.find(item["id"])
            if loaded_item:
                report_items_list.append(loaded_item)

        # A temporary product object, never saved to the database.
        product = Product(
            id=token,
            title=product_data.get("title", ""),
            description=product_data.get("description", ""),
            product_preset_id=product_preset.id,
            state_id=product_data.get("state_id"),
            report_items=report_items_list,
            links=product_data.get("links"),
            language=product_data.get("language"),
        )
        product.product_preset = product_preset
        product.user = user
        translations = _submitted_translations(product_data)
    else:
        product = Product.find(product_id)
        if product is None:
            return {"error": "Product not found"}, HTTPStatus.NOT_FOUND, None, None

    if not ProductPreset.allowed_with_acl(product.product_preset_id, user, see=False, access=True, modify=False):
        err_msg = "Unauthorized access attempt to Product preset"
        log_manager.store_auth_error_activity(err_msg)
        return {"error": err_msg}, HTTPStatus.UNAUTHORIZED, None, None

    return {}, HTTPStatus.OK, product, translations


def render_product(
    product: Product,
    product_format: ProductFormat,
    language: str | None = None,
    translations: dict | None = None,
) -> tuple[dict, HTTPStatus, dict | None]:
    """Render a product in one product format through that format's presenter.

    Args:
        product (Product): The product.
        product_format (ProductFormat): The format.
        language (str | None): The language to render (the open tab, or the one published in);
            None renders the content as written.
        translations (dict | None): The texts per language of a product not saved yet.

    Returns:
        tuple[dict, HTTPStatus, dict | None]: an error and its status, or what the presenter generated.
    """
    presenter = product_format.presenter
    if not presenter:
        return {"error": f"Format '{product_format.title}' has no presenter configured"}, HTTPStatus.BAD_REQUEST, None

    node = presenter.node
    if not node:
        return {"error": "Presenter has no node configured"}, HTTPStatus.BAD_REQUEST, None

    input_data = PresenterInput(presenter.type, product, product_format=product_format)
    input_schema = PresenterInputSchema()
    payload = input_schema.dump(input_data)
    # In the language asked for: texts translated, constants and labels as extra fields, and the
    # format's templates for that language. Before the citations, which work on the texts.
    content_localizer.localize_presenter_input(payload, language, product, translations)
    content_localizer.localize_templates(payload, product_format, language)
    # Presenters get the citations already numbered, never the link keys.
    presenter_input = render_presenter_input(payload, product.links)

    generated_data, status_code = PresentersApi(node.api_url, node.api_key).generate(presenter_input)

    if status_code != HTTPStatus.OK:
        err_msg = f"Failed to render '{product_format.title}' (status: {status_code})"
        logger.error(f"{err_msg}, data: {generated_data}")
        return {"error": err_msg}, HTTPStatus.INTERNAL_SERVER_ERROR, None

    return {}, HTTPStatus.OK, generated_data


def preview_format(product: Product, product_format_id: int | str | None) -> ProductFormat | None:
    """The format to preview: the one asked for, which must be the product preset's, else its first."""
    formats = product.product_preset.formats if product.product_preset else []
    if product_format_id in (None, ""):
        return formats[0] if formats else None
    return next((product_format for product_format in formats if str(product_format.id) == str(product_format_id)), None)


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

        # Chrome does not process the Content-Disposition filename on POST requests -> therefore, GET is used.
        # No need to re-check JWT here — it was already validated during preview generation.
        # The token is temporary, will expire, and may be redeemed PREVIEW_TICKET_MAX_REDEMPTIONS times.

        cache_key = f"preview:{token}"
        try:
            cached_bytes = redis_client.get(cache_key)
            if not cached_bytes:
                err_msg = "Preview token not found, expired, or already processed."
                log_manager.store_auth_error_activity(err_msg)
                return Response(err_msg, HTTPStatus.NOT_FOUND, mimetype="text/plain")

            # Count the redemption before serving. INCR is atomic, so concurrent requests cannot
            # slip past the cap between the read above and the check below.
            uses_key = f"{cache_key}:uses"
            uses = redis_client.incr(uses_key)
            if uses == 1:
                redis_client.expire(uses_key, PREVIEW_TICKET_TTL_SECONDS)
            if uses >= PREVIEW_TICKET_MAX_REDEMPTIONS:
                redis_client.delete(cache_key, uses_key)
            if uses > PREVIEW_TICKET_MAX_REDEMPTIONS:
                err_msg = "Preview token not found, expired, or already processed."
                log_manager.store_auth_error_activity(err_msg)
                return Response(err_msg, HTTPStatus.NOT_FOUND, mimetype="text/plain")

            cached_data = json.loads(cached_bytes)
            preview_data = base64.b64decode(cached_data["data"])
            preview_mime = cached_data["mime"]
            preview_filename = cached_data.get("filename").replace('"', "")

            logger.info(f"Preview token processed: {token}")
            response = Response(preview_data, mimetype=preview_mime)

            # Determine if content should be displayed inline or downloaded
            inline_types = ("text/", "application/pdf", "application/json")
            disposition = "inline" if any(preview_mime.startswith(itype) for itype in inline_types) else "attachment"

            # RFC 5987 encoding for non-ASCII filenames
            encoded_filename = quote(preview_filename, safe="")
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

            try:
                language = content_language.clean_language(request.json.get("language"))
            except ValueError as ex:
                return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
            msg, status, product, translations = load_product(product_data, user, token)
            if status != HTTPStatus.OK:
                return msg, status
            product_format = preview_format(product, request.json.get("product_format_id"))
            if product_format is None:
                return {"error": "The product's product preset has no such format to preview"}, HTTPStatus.BAD_REQUEST
            msg, status, generated_data = render_product(product, product_format, language, translations)
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

            extension = mimetypes.guess_extension(preview_mime)
            file_name = generated_data.get("att_file_name")
            if file_name:
                file_name = base64.b64decode(file_name).decode("UTF-8").strip()
            if not file_name:
                file_name = product_data.get("title", "report")
            file_name = f"{file_name}{extension}"

            # Store preview in Redis with automatic expiration (works across multiple workers)
            cache_key = f"preview:{token}"
            cache_value = json.dumps(
                {"data": base64.b64encode(preview_data).decode("utf-8"), "mime": preview_mime, "filename": file_name},
            )
            redis_client.set(cache_key, cache_value, ex=PREVIEW_TICKET_TTL_SECONDS)

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

            msg, status, product, translations = load_product(product_data, user, token)
            if status != HTTPStatus.OK:
                return msg, status

            # The deliveries to run: those asked for (all by default) that have a channel; a
            # format without one is only previewed.
            delivery_ids = request_data.get("delivery_ids")
            deliveries = [
                delivery
                for delivery in product.product_preset.deliveries
                if delivery.publishing_channel_id and (delivery_ids is None or delivery.id in delivery_ids)
            ]
            if not deliveries:
                return {"error": "Nothing to publish: the product preset sends no format to any channel"}, HTTPStatus.BAD_REQUEST

            # Each language of each format is rendered once, then sent to every channel it goes
            # to. A delivery without a language renders the product in its own. One failing
            # delivery does not stop the others.
            rendered: dict[tuple[int, str | None], tuple[dict, HTTPStatus, dict | None]] = {}
            results = []
            all_success = True
            for delivery in deliveries:
                language = delivery.language or product.language
                key = (delivery.product_format_id, language)
                if key not in rendered:
                    rendered[key] = render_product(product, delivery.product_format, language, translations)
                render_error, render_status, generated_data = rendered[key]
                channel = delivery.publishing_channel
                entry = {
                    "delivery_id": delivery.id,
                    "language": language,
                    "format": delivery.product_format_title,
                    "channel_name": channel.name,
                }
                what = f"'{product.title}' as {delivery.product_format_title} ({language or 'as written'}) to {channel.name}"
                if render_status != HTTPStatus.OK:
                    all_success = False
                    results.append({**entry, "success": False, "status_code": render_status, "result": render_error})
                    continue
                try:
                    result, publish_status = publishers_manager.publish(channel, generated_data, None, None, None)
                except Exception as ex:
                    logger.exception(f"Publish {what} failed")
                    result, publish_status = {"error": str(ex)}, HTTPStatus.INTERNAL_SERVER_ERROR
                if publish_status == HTTPStatus.OK:
                    logger.info(f"Published {what}")
                else:
                    all_success = False
                    logger.error(f"Publish {what} failed: {result}")
                results.append({**entry, "success": publish_status == HTTPStatus.OK, "status_code": publish_status, "result": result})

            status = HTTPStatus.OK if all_success else HTTPStatus.INTERNAL_SERVER_ERROR
            return {"results": results, "overall_success": all_success}, status

        except Exception as ex:
            msg = f"Publish failed: {ex}"
            logger.exception(msg)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR


class ProductTranslate(Resource):
    """Translate a product's title and description with AI; nothing is stored until the product is saved."""

    @auth_required(["PUBLISH_CREATE", "PUBLISH_UPDATE"])
    def post(self) -> tuple[dict, HTTPStatus]:
        """Translate ``texts`` (``title``, ``description``) into ``languages``.

        The body holds ``texts``, ``source_language``, ``languages`` and ``report_item_ids``. The
        provider is the translation provider of the first included report's type, and the
        reports' TLP must be within its limit, as the texts describe them.

        Returns:
            (dict, HTTPStatus): ``translations`` (language -> field -> text) and ``failed``
                (language -> field -> reason).
        """
        body = request.json or {}
        submitted = body.get("texts")
        texts = {field: text for field, text in (submitted.items() if isinstance(submitted, dict) else ()) if field in PRODUCT_FIELDS}
        texts = {field: text for field, text in texts.items() if isinstance(text, str) and text.strip()}
        languages = body.get("languages")
        if not texts:
            return {"error": "The product has no text to translate"}, HTTPStatus.BAD_REQUEST
        try:
            source = content_language.clean_language(body.get("source_language"))
            targets = content_language.clean_languages(languages if isinstance(languages, list) else [])
        except ValueError as ex:
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        if not targets:
            return {"error": "languages is required"}, HTTPStatus.BAD_REQUEST

        report_items = [item for item in (ReportItem.find(item_id) for item_id in body.get("report_item_ids") or []) if item]
        providers = (item.report_item_type.translation_ai_provider for item in report_items if item.report_item_type)
        provider = next((candidate for candidate in providers if candidate is not None), None)
        if provider is None:
            return {"error": "None of the product's report types has an AI provider for translation"}, HTTPStatus.BAD_REQUEST
        levels = [level for item in report_items for level in (llm_manager.report_tlp_levels(item) or [])]
        has_tlp_field = any(llm_manager.report_tlp_levels(item) is not None for item in report_items)
        refusal = llm_manager.tlp_refusal(provider, levels if has_tlp_field else None, "The product's reports")
        if refusal is not None:
            return {"error": refusal}, HTTPStatus.BAD_REQUEST
        glossary = GlossaryEntry.for_report_types(item.report_item_type.id for item in report_items if item.report_item_type)

        translations: dict[str, dict[str, str]] = {}
        failed: dict[str, dict[str, str]] = {}
        for target in targets:
            if target == source:
                continue
            try:
                done, problems = llm_manager.translate_texts(provider, texts, source, target, glossary=glossary)
            except llm_manager.LlmError as ex:
                return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
            if done:
                translations[target] = done
            missing = {field: problems.get(field, "not translated") for field in texts if field not in done}
            if missing:
                failed[target] = missing
        return {"translations": translations, "failed": failed}, HTTPStatus.OK


class ProductLanguageCheck(Resource):
    """What rendering a product in a language falls back on, for the notices before preview and publish."""

    @auth_required("PUBLISH_ACCESS")
    def post(self) -> tuple[dict, HTTPStatus]:
        """Check the product (saved or from the form) against ``language``.

        Returns:
            (dict, HTTPStatus): missing, outdated and formats (each format's template language)
        """
        body = request.json or {}
        try:
            language = content_language.clean_language(body.get("language"))
        except ValueError as ex:
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST
        user = auth_manager.get_user_from_jwt()
        # It names the product's reports: load_product asks for the same access to the
        # product preset as a preview does.
        msg, status, product, _texts = load_product(body.get("product") or {}, user, "language-check")
        if status != HTTPStatus.OK:
            return msg, status
        return content_localizer.language_check(product, language), HTTPStatus.OK


def initialize(api: Api) -> None:
    """Initialize the publish module.

    Args:
        api (Api): The API instance to add resources to.
    """
    api.add_resource(ProductsResource, "/api/v1/publish/products")
    api.add_resource(ProductResource, "/api/v1/publish/products/<int:product_id>")
    api.add_resource(ProductSetPreview, "/api/v1/publish/products/preview-ticket")
    api.add_resource(ProductGetPreview, "/api/v1/publish/products/preview/<string:token>")
    api.add_resource(PublishProduct, "/api/v1/publish/products/publish")
    api.add_resource(ProductTranslate, "/api/v1/publish/products/translate")
    api.add_resource(ProductLanguageCheck, "/api/v1/publish/products/language-check")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")
