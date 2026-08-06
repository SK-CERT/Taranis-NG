"""Dashboard API."""

from __future__ import annotations

import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from managers.log_manager import logger
from model.news_item import NewsItemData
from model.product import Product
from model.report_item import ReportItem
from model.tag_cloud import TagCloud
from shared.common import TZ

LEGACY_TAG_CLOUD_DAY_CAP: Final = 7

# Compatibility contract: existing API consumers use ``tag_cloud_day``. Keep
# accepting it with its historical look-back and upper-cap semantics even when
# adding new interval forms. Removing or silently reinterpreting it would break
# deployed clients that cannot migrate in lockstep with Core.
LEGACY_DAY_ARGUMENT: Final = "tag_cloud_day"
RANGE_ARGUMENT: Final = "tag_cloud_range"
DATE_FROM_ARGUMENT: Final = "tag_cloud_date_from"
DATE_TO_ARGUMENT: Final = "tag_cloud_date_to"

TAG_CLOUD_QUERY_ARGUMENTS: Final = (
    LEGACY_DAY_ARGUMENT,
    RANGE_ARGUMENT,
    DATE_FROM_ARGUMENT,
    DATE_TO_ARGUMENT,
)


class TagCloudQueryError(ValueError):
    """Indicate invalid or conflicting tag-cloud query arguments."""


def _single_value(arguments: Mapping[str, Sequence[str]], name: str) -> str | None:
    """Return one argument value and reject duplicate query parameters."""
    values = arguments.get(name)
    if values is None:
        return None
    if len(values) != 1:
        msg = f"Query argument '{name}' must be specified exactly once"
        raise TagCloudQueryError(msg)
    if values[0] == "":
        msg = f"Query argument '{name}' must not be empty"
        raise TagCloudQueryError(msg)
    return values[0]


def _validate_interval(date_from: datetime.date, date_to: datetime.date) -> tuple[datetime.date, datetime.date]:
    """Validate the ordering of an inclusive interval."""
    if date_from > date_to:
        msg = f"'{DATE_FROM_ARGUMENT}' must not be after '{DATE_TO_ARGUMENT}'"
        raise TagCloudQueryError(msg)
    return date_from, date_to


def _parse_legacy_day(value: str, today: datetime.date) -> tuple[datetime.date, datetime.date]:
    """Parse the backward-compatible relative-day argument."""
    try:
        number_of_days = int(value)
    except ValueError as ex:
        msg = f"'{LEGACY_DAY_ARGUMENT}' must be an integer"
        raise TagCloudQueryError(msg) from ex

    if number_of_days < 0:
        msg = f"'{LEGACY_DAY_ARGUMENT}' must not be negative"
        raise TagCloudQueryError(msg)

    # Preserve the legacy API contract: values above seven are capped, not
    # rejected. Some existing clients rely on Core applying this bound.
    number_of_days = min(number_of_days, LEGACY_TAG_CLOUD_DAY_CAP)
    return today - datetime.timedelta(days=number_of_days), today


def _parse_named_range(value: str, today: datetime.date) -> tuple[datetime.date, datetime.date]:
    """Parse a named range using the vocabulary of other Core list APIs."""
    if value == "TODAY":
        return today, today
    if value == "WEEK":
        return today - datetime.timedelta(days=today.weekday()), today
    if value == "MONTH":
        return today.replace(day=1), today
    if value == "LAST_7_DAYS":
        return today - datetime.timedelta(days=7), today
    if value == "LAST_31_DAYS":
        return today - datetime.timedelta(days=31), today

    allowed = "TODAY, WEEK, MONTH, LAST_7_DAYS, LAST_31_DAYS"
    msg = f"Unsupported '{RANGE_ARGUMENT}' value; expected one of: {allowed}"
    raise TagCloudQueryError(msg)


def _parse_explicit_interval(
    date_from_value: str | None,
    date_to_value: str | None,
) -> tuple[datetime.date, datetime.date]:
    """Parse a complete pair of inclusive ISO calendar dates."""
    if date_from_value is None or date_to_value is None:
        msg = f"'{DATE_FROM_ARGUMENT}' and '{DATE_TO_ARGUMENT}' must be specified together"
        raise TagCloudQueryError(msg)

    try:
        date_from = datetime.date.fromisoformat(date_from_value)
        date_to = datetime.date.fromisoformat(date_to_value)
    except ValueError as ex:
        msg = f"'{DATE_FROM_ARGUMENT}' and '{DATE_TO_ARGUMENT}' must use YYYY-MM-DD"
        raise TagCloudQueryError(msg) from ex

    return _validate_interval(date_from, date_to)


def parse_tag_cloud_interval(
    arguments: Mapping[str, Sequence[str]],
    today: datetime.date,
) -> tuple[datetime.date, datetime.date]:
    """Resolve one mutually exclusive tag-cloud interval mode.

    Supported modes are the legacy relative ``tag_cloud_day`` argument, one
    named ``tag_cloud_range``, or the explicit ``tag_cloud_date_from`` and
    ``tag_cloud_date_to`` pair. With no arguments, the historical today-only
    behavior is retained.
    """
    legacy_day = _single_value(arguments, LEGACY_DAY_ARGUMENT)
    named_range = _single_value(arguments, RANGE_ARGUMENT)
    date_from = _single_value(arguments, DATE_FROM_ARGUMENT)
    date_to = _single_value(arguments, DATE_TO_ARGUMENT)

    explicit_interval_requested = date_from is not None or date_to is not None
    selected_mode_count = sum((legacy_day is not None, named_range is not None, explicit_interval_requested))
    if selected_mode_count > 1:
        msg = "Use only one tag-cloud interval mode: day, range, or date_from/date_to"
        raise TagCloudQueryError(msg)

    if legacy_day is not None:
        return _parse_legacy_day(legacy_day, today)
    if named_range is not None:
        return _parse_named_range(named_range, today)
    if explicit_interval_requested:
        return _parse_explicit_interval(date_from, date_to)

    return today, today


class Dashboard(Resource):
    """Dashboard API class."""

    @jwt_required()
    def get(self) -> dict | tuple[dict, HTTPStatus]:
        """Get the dashboard data.

        The tag cloud accepts one interval mode at a time: the legacy
        ``tag_cloud_day`` look-back, a named ``tag_cloud_range``, or an
        inclusive ``tag_cloud_date_from``/``tag_cloud_date_to`` ISO date pair.

        Returns:
            (dict): The dashboard data.
        """
        try:
            tag_cloud_arguments = {name: request.args.getlist(name) for name in TAG_CLOUD_QUERY_ARGUMENTS if name in request.args}
            date_from, date_to = parse_tag_cloud_interval(tag_cloud_arguments, datetime.datetime.now(TZ).date())
        except TagCloudQueryError as ex:
            logger.warning(f"Invalid dashboard tag-cloud interval: {ex}")
            return {"error": str(ex)}, HTTPStatus.BAD_REQUEST

        total_news_items = NewsItemData.count_all()
        # counts for report items
        report_item_states = ReportItem.count_by_states()
        total_report_items = sum(state["count"] for state in report_item_states.values())
        # counts for products
        product_states = Product.count_by_states()
        total_products = sum(state["count"] for state in product_states.values())

        total_database_items = total_news_items + total_products + total_report_items
        latest_collected = NewsItemData.latest_collected()
        news_items_by_day = NewsItemData.count_collected_by_day(7)
        grouped_words = TagCloud.get_grouped_words_between(date_from, date_to)

        return {
            "total_news_items": total_news_items,
            "total_products": total_products,
            "total_report_items": total_report_items,
            "report_item_states": report_item_states,
            "product_states": product_states,
            "total_database_items": total_database_items,
            "latest_collected": latest_collected,
            "news_items_by_day": news_items_by_day,
            "tag_cloud": grouped_words,
        }


def initialize(api: object) -> None:
    """Initialize the dashboard API.

    Args:
        api (Flask): The Flask app.
    """
    api.add_resource(Dashboard, "/api/v1/dashboard-data")
