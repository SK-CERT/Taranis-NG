"""GCVE publication endpoints of a web (GCVE-BCP-03), on webs that publish GCVE records.

A web whose configuration names an organization (``gcve_organization_id``) answers, on its own
hostname, for that organization's GNA:

- ``GET /api/gcve/publication`` - its records, as GCVE-BCP-03 describes the query;
- ``GET /dumps/gna-<GNA>.ndjson`` - all of them, one per line;
- ``GET /.well-known/security.txt`` - declaring the endpoint, when the web has a security contact;
- ``GET /api/gcve/conformance`` - the conformance document of GCVE-BCP-06 (a draft, which does not
  say where it is published).

Its address is what the GNA registers at gcve.eu as ``gcve_pull_api``. The answers are JSON (or
text), errors included, and may be read from any origin: the records are public.
"""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, Response, jsonify, request
from lib.logger import get_logger
from lib.report import gcve
from lib.web import routes
from lib.web.site import current_site, load_site

logger = get_logger("gcve", silent=True)

gcve_bp = Blueprint("gcve", __name__)


def error(message: str, status: HTTPStatus) -> tuple[Response, HTTPStatus]:
    """A JSON error."""
    response = jsonify({"error": message})
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response, status


@gcve_bp.before_request
def _load_site() -> tuple[Response, HTTPStatus] | None:
    """Resolve the web; only an enabled web that publishes GCVE records answers."""
    site = load_site(routes.cache.get_webs())
    if not site.web:
        return error("Not found", HTTPStatus.NOT_FOUND)
    if not site.web.get("enabled", True):
        return error("This web is unavailable", HTTPStatus.SERVICE_UNAVAILABLE)
    if not site.gcve_enabled:
        return error("This web does not publish GCVE records", HTTPStatus.NOT_FOUND)
    return None


@gcve_bp.after_request
def _public(response: Response) -> Response:
    """The records are public: any origin may read them."""
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    return response


def _publication() -> dict | None:
    # _load_site let only a known web through, so it has an id.
    web_id = current_site().id
    return routes.cache.get_gcve_records(web_id) if web_id is not None else None


@gcve_bp.route("/api/gcve/publication", methods=["GET"], endpoint="publication")
def publication() -> Response | tuple[Response, HTTPStatus]:
    """The web's records (GCVE-BCP-03): filtered, sorted and paged by the query."""
    data = _publication()
    if data is None:
        return error("The GCVE records are not available right now", HTTPStatus.SERVICE_UNAVAILABLE)
    args = request.args
    try:
        chosen = gcve.select(
            data.get("items") or [],
            gna_id=data.get("gna_id"),
            since=gcve.parse_since(args.get("since")),
            date_sort=args.get("date_sort"),
            sort_order=args.get("sort_order"),
            source=args.get("source"),
            cwe=args.get("cwe"),
            product=args.get("product"),
            assigner=args.get("assigner"),
        )
        page = gcve.page_of(chosen, gcve.page_number(args.get("page")), gcve.page_size(args.get("per_page")))
    except gcve.QueryError as exc:
        return error(str(exc), HTTPStatus.BAD_REQUEST)
    if args.get("light", "").lower() in ("1", "true", "yes"):
        return jsonify(gcve.light(page))
    return jsonify(page)


@gcve_bp.route("/dumps/gna-<int:gna_id>.ndjson", methods=["GET"], endpoint="dump")
def dump(gna_id: int) -> Response | tuple[Response, HTTPStatus]:
    """Every record of the web, one per line (GCVE-BCP-03)."""
    data = _publication()
    if data is None:
        return error("The GCVE records are not available right now", HTTPStatus.SERVICE_UNAVAILABLE)
    if gna_id != data.get("gna_id"):
        return error("Not found", HTTPStatus.NOT_FOUND)
    records = gcve.select(data.get("items") or [], gna_id=gna_id, date_sort="updated", sort_order="desc")
    return Response(gcve.ndjson(records), mimetype="application/x-ndjson")


@gcve_bp.route("/.well-known/security.txt", methods=["GET"], endpoint="security_txt")
def security_txt() -> Response | tuple[Response, HTTPStatus]:
    """The web's security.txt, declaring its GCVE publication endpoint; only with a security contact."""
    site = current_site()
    if not site.security_contact:
        return error("Not found", HTTPStatus.NOT_FOUND)
    return Response(gcve.security_txt(site.hostname, site.security_contact), mimetype="text/plain")


@gcve_bp.route("/api/gcve/conformance", methods=["GET"], endpoint="conformance")
def conformance() -> Response | tuple[Response, HTTPStatus]:
    """The GNA conformance document (GCVE-BCP-06, draft)."""
    data = _publication()
    if data is None:
        return error("The GCVE records are not available right now", HTTPStatus.SERVICE_UNAVAILABLE)
    site = current_site()
    return jsonify(
        gcve.conformance(
            data.get("items") or [],
            gna_id=data.get("gna_id"),
            hostname=site.hostname,
            license_name=data.get("license"),
            details=data.get("conformance"),
        ),
    )
