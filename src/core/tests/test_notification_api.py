"""The notification settings API refuses what it cannot store and says why.

Event switches must name known events and be true or false; a channel's settings go through the
channel's own validation; a test message needs an address to go to. The handlers are called
through ``__wrapped__``, past the permission check, like the other API tests here.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from api import notifications as notifications_api
from flask import Flask

ADMIN = SimpleNamespace(id=9, name="Bob Admin", username="bob")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    """A bare app, an administrator, and no activity log."""
    monkeypatch.setattr(notifications_api, "get_user_from_jwt", lambda: ADMIN)
    monkeypatch.setattr(notifications_api.log_manager, "store_user_activity", lambda *_args: None)
    return Flask(__name__)


def _call(app: Flask, resource: object, method: str, body: dict, *args: object) -> tuple[dict, HTTPStatus]:
    with app.test_request_context("/", method=method.upper(), json=body):
        return getattr(type(resource), method).__wrapped__.__get__(resource)(*args)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"events": {"password_changed": "yes"}}, "true or false"),
        ({"events": ["password_changed"]}, "true or false"),
        ({}, "true or false"),
        ({"events": {"coffee_ready": True}}, "Unknown notification events: coffee_ready"),
    ],
)
def test_event_switches_must_name_known_events_and_be_true_or_false(app: Flask, body: dict, message: str) -> None:
    payload, status = _call(app, notifications_api.NotificationEventsResource(), "put", body)

    assert status == HTTPStatus.BAD_REQUEST
    assert message in payload["error"]


def test_event_switches_are_saved_and_every_events_state_is_returned(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list = []
    monkeypatch.setattr(notifications_api.NotificationEvent, "save", classmethod(lambda _cls, switches, user: saved.append((switches, user))))
    monkeypatch.setattr(
        notifications_api.NotificationEvent,
        "states",
        classmethod(lambda _cls, events: [{"event": event, "enabled": event != "password_removed"} for event in events]),
    )

    payload, status = _call(app, notifications_api.NotificationEventsResource(), "put", {"events": {"password_removed": False}})

    assert status == HTTPStatus.OK
    assert saved == [({"password_removed": False}, "Bob Admin")]
    assert [item["event"] for item in payload["events"]] == list(notifications_api.notification_manager.EVENTS)


def test_channel_settings_that_cannot_work_are_refused_with_the_reason(app: Flask) -> None:
    payload, status = _call(
        app,
        notifications_api.NotificationChannelResource(),
        "put",
        {"enabled": True, "config": {"host": "smtp.example.test", "from_address": "not an address"}},
        "email",
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert payload["error"] == "Sender address must be an e-mail address"


def test_an_unknown_channel_kind_is_not_found(app: Flask) -> None:
    _payload, status = _call(app, notifications_api.NotificationChannelResource(), "put", {}, "carrier-pigeon")

    assert status == HTTPStatus.NOT_FOUND


def test_a_test_message_needs_an_address_to_go_to(app: Flask) -> None:
    payload, status = _call(
        app,
        notifications_api.NotificationChannelTestResource(),
        "post",
        {"recipient": "", "config": {"host": "smtp.example.test", "from_address": "taranis@example.test"}},
        "email",
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert "e-mail address" in payload["error"]
