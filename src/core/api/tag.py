"""Tags API: the tags reports and products use, for lists, pickers and filters."""

from collections.abc import Mapping
from http import HTTPStatus

from flask_restful import Api, Resource
from managers import content_language
from managers.auth_manager import auth_required
from model.tag import ENTITY_TYPES, Tag

TRANSLATION_FILTERS = ("needs", "unreviewed", "not_set")


def list_filter(args: Mapping[str, str]) -> dict:
    """The tag and translation filters of a list request (Analyze, Publish).

    Args:
        args (Mapping[str, str]): The query parameters: ``tags`` (comma-separated tag ids),
            ``translation`` (``needs``, ``unreviewed`` or ``not_set``) and ``translation_language``.

    Returns:
        dict: What the models' ``get`` filters take; a translation filter without a valid
            language is left out.
    """
    result: dict = {}
    tag_ids = [int(part) for part in (args.get("tags") or "").split(",") if part.strip().isdigit()]
    if tag_ids:
        result["tags"] = tag_ids
    kind = args.get("translation")
    language = args.get("translation_language")
    if kind == "not_set":
        result["translation"] = kind
    elif kind in TRANSLATION_FILTERS and content_language.is_language(language):
        result["translation"] = kind
        result["translation_language"] = language
    return result


class EntityTypeTagsResource(Resource):
    """The tags active for an entity type."""

    @auth_required(["ANALYZE_ACCESS", "PUBLISH_ACCESS"])
    def get(self, entity_type: str) -> tuple[dict, HTTPStatus]:
        """Get the active tags of reports or products, in their Tag Workflow order.

        Args:
            entity_type (str): ``report_item`` or ``product``.

        Returns:
            (dict, int): ``{"entity_type", "tags"}``; each tag has its ``system_key`` (None for
                admin tags) and ``sort_order``.
        """
        if entity_type not in ENTITY_TYPES:
            return {"error": f"Tags are for: {', '.join(ENTITY_TYPES)}"}, HTTPStatus.NOT_FOUND
        return {"entity_type": entity_type, "tags": Tag.offered(entity_type)}, HTTPStatus.OK


def initialize(api: Api) -> None:
    """Register the tag endpoints."""
    api.add_resource(EntityTypeTagsResource, "/api/v1/tags/entity-types/<string:entity_type>")
