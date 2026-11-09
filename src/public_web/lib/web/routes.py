"""Public view routes: homepage, report detail, RSS feed, branding images, and feedback.

All endpoints run per-request site resolution by Host header (see site.py) and
serve branded content for the resolved web and language. The report content itself
(homepage entries, report body, RSS text) comes from the report templates, see
``lib.report.renderer``.
"""

import json
import math

from feedgen.feed import FeedGenerator
from flask import (
    Blueprint,
    Response,
    abort,
    make_response,
    render_template,
    request,
    url_for,
)
from lib import send_mail
from lib.logger import get_logger
from lib.report.product import matches_keyword
from lib.web import translate, translate_ui
from lib.web.cache import WebCache
from lib.web.site import IMAGE_KINDS, current_site, load_site

feedback_logger = get_logger("feedback", silent=True)
cache = WebCache()


reports_bp = Blueprint("reports", __name__)


@reports_bp.before_request
def _load_site() -> None:
    """Resolve which web (and language) serves this request before handling it.

    Unknown host -> 404. Known host with disabled web -> 503.
    """
    site = load_site(cache.get_webs())
    if not site.web:
        abort(404)
    if not site.web.get("enabled", True):
        abort(503)


@reports_bp.url_defaults
def _keep_chosen_language(endpoint: str, values: dict) -> None:
    """Carry a language picked with ``?lang=`` into the page's links, so it lasts beyond one page.

    Branding images are the same in every language, so their URLs stay as they are.
    """
    site = current_site()
    if site.chosen and endpoint != "reports.branding":
        values.setdefault("lang", site.language)


def _remove_link_references(text: str, links: list[str | None]) -> str:
    """Removes references ([1], [2]...) from text."""
    for i, _ in enumerate(links, start=1):
        text = text.replace(f" [{i}]", "").replace(f"[{i}]", "")
    return text


def _render_options(selected_items: list[int] | None = None) -> dict:
    """What the report templates get besides the product: language, branding, ``t()``."""
    site = current_site()
    return {
        "selected_items": selected_items,
        "translate": translate,
        "lang": site.language,
        "site": {"content": site.content, "metadata": site.metadata, "hostname": site.hostname, "language": site.language},
    }


def _get_rss_description(report: dict) -> str:
    """Returns the plain-text RSS description of a report, without [n] link references."""
    text = cache.renderer(current_site().id).render_text(report, **_render_options())
    return _remove_link_references(text, report["links"])


@reports_bp.route("/", endpoint="home")
def homepage() -> str:
    """Endpoint for homepage rendering.

    The homepage consists of a list of reports. There is a limit of reports per
    page, this limit is part of the web's configuration. Reports can also be
    filtered using a keyword.
    """
    search_arg = request.args.get("search")
    try:
        page = int(request.args.get("page") or 1)
    except ValueError:
        abort(400)

    site = current_site()
    limit = site.max_reports_homepage
    reports = cache.get_all_reports(site.id, site.language)
    if search_arg:
        # Filter per keyword search from arguments.
        reports = [report for report in reports if matches_keyword(report, search_arg)]

    pages = math.ceil(len(reports) / limit)
    upper_report_index = limit * page
    lower_report_index = upper_report_index - limit
    renderer = cache.renderer(site.id)
    options = _render_options()
    entries = [(report, renderer.render(report, "summary", **options)) for report in reports[lower_report_index:upper_report_index]]
    return render_template(
        "homepage.html",
        entries=entries,
        search_arg=search_arg,
        page=page,
        pages=pages,
        warning_seen=request.cookies.get("warning-seen"),
    )


@reports_bp.route("/rss", endpoint="rss")
@reports_bp.route("/feed", endpoint="feed")
def rss() -> Response:
    """Endpoint for rendering an RSS feed (per web + language)."""
    site = current_site()
    fg = FeedGenerator()
    fg.title(site.metadata.get("rss_title", ""))
    fg.description(site.metadata.get("rss_description", ""))
    fg.link(href=site.hostname)

    # Every published report: a feed reader can then catch up on all of them.
    reports = cache.get_all_reports(site.id, site.language)

    # add_entry() adds items in a reverse order (the first added item will be
    # the last in the feed), that's why reversed() is needed.
    for report in reversed(reports):
        report_link = site.hostname + url_for("reports.show", report_id=report["id"])
        fe = fg.add_entry()
        fe.title(report["title"])
        fe.link(href=report_link)
        fe.description(_get_rss_description(report))
        fe.guid(report_link, permalink=True)

    response = make_response(fg.rss_str())
    response.headers.set("Content-Type", "application/xml")
    return response


@reports_bp.route("/branding/<kind>", endpoint="branding")
def branding(kind: str) -> Response:
    """Serve one of the current web's uploaded images (logo/favicon/preview).

    Proxied (and cached) from core. 404 if this web has no such image.
    """
    site = current_site()
    if kind not in IMAGE_KINDS or site.id is None:
        abort(404)
    result = cache.get_web_image(site.id, kind)
    if result is None:
        abort(404)
    data, mime_type = result
    response = make_response(data)
    response.headers.set("Content-Type", mime_type)
    return response


@reports_bp.route("/reports/<report_id>", endpoint="show")
def report_view(report_id: str) -> str:
    """Endpoint for displaying a report."""
    # Report ids are Taranis product ids (integers).
    if not report_id.isdigit():
        abort(400)
    site = current_site()
    report = cache.get_report(report_id, site.id, site.language)
    if report is None:
        abort(404)
    try:
        items_arg = request.args.get("items")
        items = list(map(int, items_arg.split(","))) if items_arg else []
    except ValueError:
        abort(400)
    return render_template(
        "report.html",
        report=report,
        detail=cache.renderer(site.id).render(report, "detail", **_render_options(items)),
        items=items,
        feedback_q=current_site().feedback_questions,
        warning_seen=request.cookies.get("warning-seen"),
    )


@reports_bp.route("/reports/<report_id>/feedback", endpoint="feedback", methods=["POST"])
def feedback_view(report_id: str) -> tuple[str, int, dict[str, str]]:
    """Endpoint for sending a feedback about a report based on the form data."""
    accepted_answers = {
        "yes",
        "no",
        translate_ui("form_yes").lower(),
        translate_ui("form_no").lower(),
    }

    # Basic validation of form values.
    for question, is_mandatory in [
        ("feedback-question1", True),
        ("feedback-question2", True),
        ("feedback-question3", False),
    ]:
        if is_mandatory and question not in request.form:
            abort(400)
        if question in request.form and request.form.get(question, "").lower() not in accepted_answers:
            abort(400)

    site = current_site()
    questions = site.feedback_questions

    # Report ids are Taranis product ids (integers).
    if not report_id.isdigit():
        abort(400)
    report = cache.get_report(report_id, site.id, site.language)
    if report is None:
        abort(404)

    body = f'''Byl odeslán feedback k reportu {report["title"]}
({site.hostname}{url_for("reports.show", report_id=report_id)}).

{questions["question1"]} "{request.form.get("feedback-question1", "---")}"
{questions["question2"]} "{request.form.get("feedback-question2", "---")}"
{questions["question3"]} "{request.form.get("feedback-question3", "---")}"
{questions["comment"]} "{request.form.get("feedback-comment", "-")}"'''

    feedback_logger.info(
        "Feedback for report with ID %s will be sent through e-mail:\n%s.",
        report_id,
        body,
    )
    subject = site.feedback_subject or f"[public-web] Feedback k reportu (report ID {report_id})"
    send_mail(
        body,
        subject,
        recipients=site.feedback_recipients,
        logger=feedback_logger,
        sender=site.feedback_sender,
        smtp=site.feedback_smtp,
    )

    return (json.dumps({"success": True}), 200, {"ContentType": "application/json"})
