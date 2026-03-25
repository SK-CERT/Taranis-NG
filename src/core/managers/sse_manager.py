"""Implement SSE functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import Flask
    from shared.time_manager import SchedulerManager

from datetime import datetime

from model.remote import RemoteAccess
from shared.common import TZ
from sse.sse import SSE


class SSEManager:
    """Manages Server-Sent Events (SSE) for various application events.

    Attributes:
        report_item_locks (dict): A dictionary to track locks on report items.
        sse (SSE): An instance of the SSE class for publishing events.
        report_item_locks_last_check_time (datetime): Timestamp of the last lock check.
    """

    def __init__(self) -> None:
        """Initialize the SSEManager with default values."""
        self.report_item_locks: dict = {}
        self.sse = SSE()
        self.report_item_locks_last_check_time = datetime.now(TZ)

    def news_items_updated(self) -> None:
        """Publish an event indicating that news items have been updated."""
        self.sse.publish({}, event="news-items-updated")

    def report_items_updated(self) -> None:
        """Publish an event indicating that report items have been updated."""
        self.sse.publish({}, event="report-items-updated")

    def report_item_updated(self, data: dict) -> None:
        """Publish an event for a specific report item update.

        Args:
            data (dict): Data related to the updated report item.
        """
        self.sse.publish(data, event="report-item-updated")

    def remote_access_disconnect(self, data: dict) -> None:
        """Publish an event for remote access disconnection.

        Args:
            data (dict): Data related to the remote access disconnection.
        """
        self.sse.publish(data, event="remote_access_disconnect", channel="remote")

    def remote_access_news_items_updated(self, osint_source_ids: list) -> None:
        """Publish an event for updated news items in remote access.

        Args:
            osint_source_ids (list): List of OSINT source IDs.
        """
        remote_access_event_ids = RemoteAccess.get_relevant_for_news_items(osint_source_ids)
        self.sse.publish(remote_access_event_ids, event="remote_access_news_items_updated", channel="remote")

    def remote_access_report_items_updated(self, report_item_type_id: int) -> None:
        """Publish an event for updated report items in remote access.

        Args:
            report_item_type_id (int): ID of the report item type.
        """
        remote_access_event_ids = RemoteAccess.get_relevant_for_report_item(report_item_type_id)
        self.sse.publish(remote_access_event_ids, event="remote_access_report_items_updated", channel="remote")

    def report_item_lock(self, report_item_id: int, field_id: int, user_id: int) -> None:
        """Lock a specific field of a report item for a user.

        Args:
            report_item_id (int): ID of the report item.
            field_id (int): ID of the field to lock.
            user_id (int): ID of the user requesting the lock.
        """
        if report_item_id in self.report_item_locks:
            report_item = self.report_item_locks[report_item_id]
        else:
            report_item = {}
            self.report_item_locks[report_item_id] = report_item

        if field_id not in report_item or report_item[field_id] is None:
            report_item[field_id] = {"user_id": user_id, "lock_time": datetime.now(TZ)}
            self.sse.publish({"report_item_id": int(report_item_id), "field_id": field_id, "user_id": user_id}, event="report-item-locked")

    def report_item_unlock(self, report_item_id: int, field_id: int, user_id: int) -> None:
        """Unlock a specific field of a report item.

        Args:
            report_item_id (int): ID of the report item.
            field_id (int): ID of the field to unlock.
            user_id (int): ID of the user requesting the unlock.
        """
        if report_item_id in self.report_item_locks:
            report_item = self.report_item_locks[report_item_id]

            if field_id in report_item:
                report_item[field_id] = None

        self.sse.publish({"report_item_id": int(report_item_id), "field_id": field_id, "user_id": user_id}, event="report-item-unlocked")

    def report_item_hold_lock(self, report_item_id: int, field_id: int, user_id: int) -> None:
        """Extend the lock time for a specific field of a report item.

        Args:
            report_item_id (int): ID of the report item.
            field_id (int): ID of the field to hold the lock.
            user_id (int): ID of the user holding the lock.
        """
        if report_item_id in self.report_item_locks:
            report_item = self.report_item_locks[report_item_id]
            if field_id in report_item and report_item[field_id] is not None and report_item[field_id]["user_id"] == user_id:
                report_item[field_id]["lock_time"] = datetime.now(TZ)

    def check_report_item_locks(self, app: Flask) -> None:
        """Check and releases expired locks on report items.

        Args:
            app: The application context for publishing events.
        """
        for key in self.report_item_locks:
            for field_key in self.report_item_locks[key]:
                if (
                    self.report_item_locks[key][field_key] is not None
                    and self.report_item_locks[key][field_key]["lock_time"] < self.report_item_locks_last_check_time
                ):
                    self.report_item_locks[key][field_key] = None
                    with app.app_context():
                        self.sse.publish({"report_item_id": int(key), "field_id": field_key, "user_id": -1}, event="report-item-unlocked")

        self.report_item_locks_last_check_time = datetime.now(TZ)


sse_manager = SSEManager()


def initialize(app: Flask) -> None:
    """Initialize the SSEManager and schedules periodic lock checks.

    Args:
        app: The application instance.
    """


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Schedule check report item locks.

    Params:
        manager: time manager class.
        app: The Flask application instance.
    """
    manager.schedule_job_minutes(1, sse_manager.check_report_item_locks, "Check report item locks", app)
