"""Configuration of notification channels and the log of their deliveries.

Configuration > Application Settings > Notifications: the channels users are notified through
(e-mail for now), a test message to check them, and the outbox of notifications with the
retries of those that could not be delivered.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from flask import request
from flask_restful import Resource
from managers import log_manager, notification_manager
from managers.auth_manager import auth_required, get_user_from_jwt
from managers.notifications.channels import CHANNELS, ChannelError, is_email_address
from model.notification import NotificationChannel, NotificationEvent, NotificationOutbox
from model.user import User
from sqlalchemy import func, or_

if TYPE_CHECKING:
    from flask_restful import Api


def _channel_json(kind: str) -> dict:
    """A channel's settings, or the defaults of one never configured."""
    channel = NotificationChannel.find(kind)
    if channel is not None:
        return channel.to_json()
    return {"kind": kind, "enabled": False, "config": {}, "has_secret": False, "updated_by": None, "updated_at": None}


def users_without_email() -> int:
    """How many active users have no e-mail address, so e-mail cannot reach them."""
    return User.query.filter(User.status == "active", or_(User.email.is_(None), func.trim(User.email) == "")).count()


class NotificationSettingsResource(Resource):
    """The notification channels."""

    @auth_required("CONFIG_NOTIFICATIONS_ACCESS")
    def get(self) -> tuple[dict, HTTPStatus]:
        """Get every channel kind's settings (never their secrets) and which events are reported.

        Returns:
            (dict, HTTPStatus): ``{"channels": [...], "events": [...], "users_without_email": n}``
        """
        return {
            "channels": [_channel_json(kind) for kind in CHANNELS],
            "events": NotificationEvent.states(notification_manager.EVENTS),
            "users_without_email": users_without_email(),
        }, HTTPStatus.OK


class NotificationEventsResource(Resource):
    """Which events users are notified of."""

    @auth_required("CONFIG_NOTIFICATIONS_UPDATE")
    def put(self) -> tuple[dict, HTTPStatus]:
        """Turn events on or off.

        The body is ``{"events": {"password_changed": true, ...}}``; events left out keep their switch.

        Returns:
            (dict, HTTPStatus): ``{"events": [...]}``, every event's switch, or why it was rejected.
        """
        switches = (request.json or {}).get("events")
        if not isinstance(switches, dict) or not all(isinstance(value, bool) for value in switches.values()):
            return {"error": "Expected the events as a map of event to true or false"}, HTTPStatus.BAD_REQUEST
        unknown = sorted(set(switches) - set(notification_manager.EVENTS))
        if unknown:
            return {"error": f"Unknown notification events: {', '.join(unknown)}"}, HTTPStatus.BAD_REQUEST
        user = get_user_from_jwt()
        NotificationEvent.save(switches, user.name)
        log_manager.store_user_activity(
            user,
            "NOTIFICATION_EVENTS_UPDATE",
            ", ".join(f"{event}: {'on' if enabled else 'off'}" for event, enabled in switches.items()),
        )
        return {"events": NotificationEvent.states(notification_manager.EVENTS)}, HTTPStatus.OK


class NotificationChannelResource(Resource):
    """One channel's settings."""

    @auth_required("CONFIG_NOTIFICATIONS_UPDATE")
    def put(self, kind: str) -> tuple[dict, HTTPStatus]:
        """Save a channel.

        The body is ``{"enabled", "config", "secret"?, "clear_secret"?}``; an empty secret keeps
        the stored one.

        Returns:
            (dict, HTTPStatus): The saved channel, or why it was rejected.
        """
        channel_class = CHANNELS.get(kind)
        if channel_class is None:
            return {"error": f"Unknown notification channel: {kind}"}, HTTPStatus.NOT_FOUND
        data = request.json or {}
        try:
            config = channel_class.validate(data.get("config") or {})
        except ValueError as error:
            return {"error": str(error)}, HTTPStatus.BAD_REQUEST
        user = get_user_from_jwt()
        try:
            channel = NotificationChannel.save(kind, bool(data.get("enabled")), config, data.get("secret") or None, user.name)
            if data.get("clear_secret") and not data.get("secret"):
                channel.clear_secret(user.name)
        except Exception as ex:
            msg = "Could not save the notification channel"
            log_manager.store_data_error_activity(user, msg, ex)
            return {"error": msg}, HTTPStatus.BAD_REQUEST
        log_manager.store_user_activity(
            user,
            "NOTIFICATION_CHANNEL_UPDATE",
            f"Notification channel {kind} saved (enabled: {channel.enabled})",
        )
        return channel.to_json(), HTTPStatus.OK


class NotificationChannelTestResource(Resource):
    """Send a test message through a channel."""

    @auth_required("CONFIG_NOTIFICATIONS_UPDATE")
    def post(self, kind: str) -> tuple[dict, HTTPStatus]:
        """Send a test message right away with the settings in the form, saved or not.

        The body is ``{"recipient", "config", "secret"?}``; an empty secret uses the stored one.

        Returns:
            (dict, HTTPStatus): ``{"ok": true}``, or the reason it was not delivered.
        """
        channel_class = CHANNELS.get(kind)
        if channel_class is None:
            return {"error": f"Unknown notification channel: {kind}"}, HTTPStatus.NOT_FOUND
        data = request.json or {}
        recipient = (data.get("recipient") or "").strip()
        if kind == "email" and not is_email_address(recipient):
            return {"error": "Enter the e-mail address to send the test to"}, HTTPStatus.BAD_REQUEST
        try:
            config = channel_class.validate(data.get("config") or {})
        except ValueError as error:
            return {"error": str(error)}, HTTPStatus.BAD_REQUEST
        secret = data.get("secret") or None
        if secret is None:
            stored = NotificationChannel.find(kind)
            secret = stored.get_secret_plaintext() if stored else None
        user = get_user_from_jwt()
        try:
            notification_manager.send_test(kind, config, secret, recipient, user)
        except ChannelError as error:
            return {"error": str(error)}, HTTPStatus.BAD_REQUEST
        log_manager.store_user_activity(user, "NOTIFICATION_TEST", f"Test {kind} notification sent to {recipient}")
        return {"ok": True}, HTTPStatus.OK


class NotificationOutboxResource(Resource):
    """The delivery log."""

    @auth_required("CONFIG_NOTIFICATIONS_ACCESS")
    def get(self) -> tuple[dict, HTTPStatus]:
        """Get the newest notifications, optionally of one status (``?status=&limit=``).

        Returns:
            (dict, HTTPStatus): ``{"items": [...]}``, without the message bodies.
        """
        try:
            limit = int(request.args.get("limit", 100))
        except ValueError:
            limit = 100
        items = NotificationOutbox.recent(request.args.get("status") or None, limit)
        return {"items": [item.to_json() for item in items]}, HTTPStatus.OK


class NotificationOutboxRetryResource(Resource):
    """Retry a notification that could not be delivered."""

    @auth_required("CONFIG_NOTIFICATIONS_UPDATE")
    def post(self, notification_id: int) -> tuple[dict, HTTPStatus]:
        """Put a failed notification back in the queue and deliver it.

        Returns:
            (dict, HTTPStatus): Empty, or why it could not be retried.
        """
        if not NotificationOutbox.retry(notification_id):
            return {"error": "Only a failed notification can be retried"}, HTTPStatus.BAD_REQUEST
        notification_manager.deliver_soon()
        return {}, HTTPStatus.OK


def initialize(api: Api) -> None:
    """Register the notification endpoints."""
    api.add_resource(NotificationSettingsResource, "/api/v1/config/notifications")
    api.add_resource(NotificationEventsResource, "/api/v1/config/notifications/events")
    api.add_resource(NotificationChannelResource, "/api/v1/config/notifications/channels/<string:kind>")
    api.add_resource(NotificationChannelTestResource, "/api/v1/config/notifications/channels/<string:kind>/test")
    api.add_resource(NotificationOutboxResource, "/api/v1/config/notifications/outbox")
    api.add_resource(NotificationOutboxRetryResource, "/api/v1/config/notifications/outbox/<int:notification_id>/retry")
