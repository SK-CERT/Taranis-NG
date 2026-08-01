"""Implement SSE functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import Flask
    from shared.time_manager import SchedulerManager

from datetime import datetime

from managers.cache_manager import redis_client
from model.remote import RemoteAccess
from shared.common import TZ
from shared.log_manager import logger
from sse.sse import SSE

# Field locks live in Redis rather than in this process. They used to be a plain dict on the
# manager, which meant every gunicorn worker kept its own copy: a client asking for the
# current locks was served by an arbitrary worker and got an arbitrary subset of them, and
# the sweeper only ever expired the locks its own worker happened to hold.
#
# A lock is one field of the hash `report_item_locks:<report_item_id>` holding
# "<user_id>:<epoch_seconds>". Freshness comes from that timestamp instead of a per-field TTL
# (Redis only offers those from 7.4), while the hash itself expires so abandoned report items
# do not pile up.
LOCK_KEY_PREFIX = "report_item_locks:"
LOCK_TTL_SECONDS = 60
LOCK_KEY_TTL_SECONDS = 300

# Take the lock unless somebody else holds a fresh one. Returns 1 when it was newly acquired,
# 2 when the caller already held it (only refreshed, nothing to announce), 0 when refused.
LOCK_ACQUIRE_SCRIPT = """
local entry = redis.call('HGET', KEYS[1], ARGV[1])
local acquired = 1
if entry then
    local owner, ts = string.match(entry, '^(-?%d+):(%d+)$')
    if owner and (tonumber(ARGV[3]) - tonumber(ts)) < tonumber(ARGV[4]) then
        if owner ~= ARGV[2] then
            return 0
        end
        acquired = 2
    end
end
redis.call('HSET', KEYS[1], ARGV[1], ARGV[2] .. ':' .. ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return acquired
"""

# Release the lock only if the caller still owns it, so a late unlock cannot drop somebody
# else's lock that was granted after this one expired.
LOCK_RELEASE_SCRIPT = """
local entry = redis.call('HGET', KEYS[1], ARGV[1])
if entry then
    local owner = string.match(entry, '^(-?%d+):')
    if owner == ARGV[2] then
        redis.call('HDEL', KEYS[1], ARGV[1])
        return 1
    end
end
return 0
"""

# Push the expiry of a lock the caller owns further out while they keep typing.
LOCK_HOLD_SCRIPT = """
local entry = redis.call('HGET', KEYS[1], ARGV[1])
if entry then
    local owner = string.match(entry, '^(-?%d+):')
    if owner == ARGV[2] then
        redis.call('HSET', KEYS[1], ARGV[1], ARGV[2] .. ':' .. ARGV[3])
        redis.call('EXPIRE', KEYS[1], ARGV[4])
        return 1
    end
end
return 0
"""


class SSEManager:
    """Manages Server-Sent Events (SSE) for various application events.

    Attributes:
        sse (SSE): An instance of the SSE class for publishing events.
    """

    def __init__(self) -> None:
        """Initialize the SSEManager with default values."""
        self.sse = SSE()
        self._lock_acquire = redis_client.register_script(LOCK_ACQUIRE_SCRIPT)
        self._lock_release = redis_client.register_script(LOCK_RELEASE_SCRIPT)
        self._lock_hold = redis_client.register_script(LOCK_HOLD_SCRIPT)

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

    @staticmethod
    def _lock_key(report_item_id: int | str) -> str:
        """Build the Redis key holding the locks of one report item.

        Args:
            report_item_id (int | str): ID of the report item.

        Returns:
            str: The Redis key.
        """
        return f"{LOCK_KEY_PREFIX}{report_item_id}"

    @staticmethod
    def _parse_lock(entry: bytes | str) -> tuple[int, int] | None:
        """Parse a stored lock into its owner and timestamp.

        Args:
            entry (bytes | str): The stored "<user_id>:<epoch_seconds>" value.

        Returns:
            tuple[int, int] | None: The user ID and lock time, or None if unparsable.
        """
        text = entry.decode("utf-8") if isinstance(entry, bytes) else entry
        user_id, separator, lock_time = text.partition(":")
        if not separator:
            return None

        try:
            return int(user_id), int(lock_time)
        except ValueError:
            return None

    def get_report_item_locks(self, report_item_id: int) -> dict:
        """Get the currently held locks of a report item.

        Args:
            report_item_id (int): ID of the report item.

        Returns:
            dict: Field ID to lock owner and time, containing only locks that are still valid.
        """
        try:
            entries = redis_client.hgetall(self._lock_key(report_item_id))
        except Exception as error:
            logger.exception(f"SSE: Error reading report item locks: {error}")
            return {}

        now = int(datetime.now(TZ).timestamp())
        locks = {}
        for field, entry in entries.items():
            parsed = self._parse_lock(entry)
            if parsed is None:
                continue

            user_id, lock_time = parsed
            if now - lock_time >= LOCK_TTL_SECONDS:
                continue

            field_id = field.decode("utf-8") if isinstance(field, bytes) else field
            locks[field_id] = {"user_id": user_id, "lock_time": lock_time}

        return locks

    def report_item_lock(self, report_item_id: int, field_id: int, user_id: int) -> None:
        """Lock a specific field of a report item for a user.

        Args:
            report_item_id (int): ID of the report item.
            field_id (int): ID of the field to lock.
            user_id (int): ID of the user requesting the lock.
        """
        now = int(datetime.now(TZ).timestamp())
        try:
            acquired = self._lock_acquire(
                keys=[self._lock_key(report_item_id)],
                args=[str(field_id), str(user_id), now, LOCK_TTL_SECONDS, LOCK_KEY_TTL_SECONDS],
            )
        except Exception as error:
            logger.exception(f"SSE: Error locking report item field: {error}")
            return

        # 2 means the caller already held it and only refreshed it, so there is nothing new
        # to tell the other clients about.
        if int(acquired) == 1:
            self.sse.publish({"report_item_id": int(report_item_id), "field_id": field_id, "user_id": user_id}, event="report-item-locked")

    def report_item_unlock(self, report_item_id: int, field_id: int, user_id: int) -> None:
        """Unlock a specific field of a report item.

        Args:
            report_item_id (int): ID of the report item.
            field_id (int): ID of the field to unlock.
            user_id (int): ID of the user requesting the unlock.
        """
        try:
            self._lock_release(keys=[self._lock_key(report_item_id)], args=[str(field_id), str(user_id)])
        except Exception as error:
            logger.exception(f"SSE: Error unlocking report item field: {error}")

        self.sse.publish({"report_item_id": int(report_item_id), "field_id": field_id, "user_id": user_id}, event="report-item-unlocked")

    def report_item_hold_lock(self, report_item_id: int, field_id: int, user_id: int) -> None:
        """Extend the lock time for a specific field of a report item.

        Args:
            report_item_id (int): ID of the report item.
            field_id (int): ID of the field to hold the lock.
            user_id (int): ID of the user holding the lock.
        """
        now = int(datetime.now(TZ).timestamp())
        try:
            self._lock_hold(
                keys=[self._lock_key(report_item_id)],
                args=[str(field_id), str(user_id), now, LOCK_KEY_TTL_SECONDS],
            )
        except Exception as error:
            logger.exception(f"SSE: Error holding report item lock: {error}")

    def check_report_item_locks(self, app: Flask) -> None:
        """Check and release expired locks on report items.

        Args:
            app: The application context for publishing events.
        """
        now = int(datetime.now(TZ).timestamp())
        try:
            keys = list(redis_client.scan_iter(match=f"{LOCK_KEY_PREFIX}*"))
        except Exception as error:
            logger.exception(f"SSE: Error scanning report item locks: {error}")
            return

        for key in keys:
            try:
                entries = redis_client.hgetall(key)
            except Exception as error:
                logger.exception(f"SSE: Error reading report item locks: {error}")
                continue

            key_text = key.decode("utf-8") if isinstance(key, bytes) else key
            try:
                report_item_id = int(key_text[len(LOCK_KEY_PREFIX) :])
            except ValueError:
                # One unexpected key must not abort the sweep for every other report item.
                logger.warning(f"SSE: Skipping report item lock key with unexpected name: {key_text}")
                continue

            for field, entry in entries.items():
                parsed = self._parse_lock(entry)
                if parsed is not None and now - parsed[1] < LOCK_TTL_SECONDS:
                    continue

                field_id = field.decode("utf-8") if isinstance(field, bytes) else field
                try:
                    removed = redis_client.hdel(key, field)
                except Exception as error:
                    logger.exception(f"SSE: Error releasing expired report item lock: {error}")
                    continue

                # Every worker runs this sweep, so only the one that actually removed the
                # entry announces it - otherwise clients get the same release several times.
                if not removed:
                    continue

                with app.app_context():
                    self.sse.publish(
                        {"report_item_id": report_item_id, "field_id": field_id, "user_id": -1},
                        event="report-item-unlocked",
                    )


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
