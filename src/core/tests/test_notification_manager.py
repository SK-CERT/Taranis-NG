"""Changes to a user's password and second factors are reported to them, and reporting never breaks the change.

``notify_user`` queues one message per channel that reaches the user, rendered in their
language; a user without an e-mail address gets nothing, and a failure while queueing is logged
rather than raised into the request that changed the account. Delivery retries with growing
delays and gives up after ``MAX_ATTEMPTS``.

Every place that changes a password or a second factor raises the matching event: an
administrator's edit of a user, self-service TOTP and passkeys, enrolment during login, and an
administrator's reset. Administrators choose which events are reported.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from api import config as config_api
from api import user as user_api
from flask import Flask
from managers import auth_manager, notification_manager
from managers.notifications.channels import ChannelError

if TYPE_CHECKING:
    from collections.abc import Callable

ALICE = SimpleNamespace(id=1, name="Alice", username="alice", email="alice@example.test", totp_secret=None, webauthn_credentials=[])
NO_MAIL = SimpleNamespace(id=2, name="Nomad", username="nomad", email=None, totp_secret=None, webauthn_credentials=[])
ADMIN = SimpleNamespace(id=9, name="Bob Admin", username="bob", email="bob@example.test")


class FakeSession:
    """Collects what notify_user writes."""

    def __init__(self) -> None:
        """Start empty."""
        self.added: list = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = False

    def add_all(self, rows: list) -> None:
        """Stage rows."""
        self.added.extend(rows)

    def commit(self) -> None:
        """Commit, or fail like a broken database."""
        if self.fail_commit:
            msg = "database is down"
            raise RuntimeError(msg)
        self.commits += 1

    def rollback(self) -> None:
        """Roll back."""
        self.rollbacks += 1


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """An e-mail channel that is enabled, every event on, users who read Czech, and no real delivery."""
    session = FakeSession()
    state = SimpleNamespace(session=session, channels=[SimpleNamespace(kind="email")], kicks=0, switched_off=set())
    monkeypatch.setattr(notification_manager.db, "session", session)
    monkeypatch.setattr(
        notification_manager.NotificationEvent,
        "is_enabled",
        classmethod(lambda _cls, event: event not in state.switched_off),
    )
    monkeypatch.setattr(notification_manager.NotificationChannel, "enabled_channels", classmethod(lambda _cls: state.channels))
    monkeypatch.setattr(notification_manager.catalog, "locale_for", lambda _user: "cs")

    def kick() -> None:
        state.kicks += 1

    monkeypatch.setattr(notification_manager, "deliver_soon", kick)
    return state


def test_a_change_is_queued_in_the_users_language_and_delivery_starts_at_once(outbox: SimpleNamespace) -> None:
    queued = notification_manager.notify_user(ALICE, notification_manager.TOTP_ENABLED)

    assert queued == 1
    [row] = outbox.session.added
    assert (row.channel_kind, row.recipient, row.event, row.user_id, row.status) == (
        "email",
        "alice@example.test",
        "totp_enabled",
        1,
        "pending",
    )
    assert row.subject == "[Taranis NG] Dvoufaktorové ověření zapnuto"
    assert "Účet: alice" in row.body
    assert "Změnil(a): Vy" in row.body
    assert outbox.kicks == 1


def test_a_user_without_an_email_address_is_skipped(outbox: SimpleNamespace) -> None:
    assert notification_manager.notify_user(NO_MAIL, notification_manager.TOTP_ENABLED) == 0
    assert outbox.session.added == []
    assert outbox.kicks == 0


def test_an_event_switched_off_by_an_administrator_is_not_reported(outbox: SimpleNamespace) -> None:
    outbox.switched_off = {notification_manager.PASSWORD_CHANGED}

    assert notification_manager.notify_user(ALICE, notification_manager.PASSWORD_CHANGED) == 0
    assert notification_manager.notify_user(ALICE, notification_manager.TOTP_ENABLED) == 1
    assert [row.event for row in outbox.session.added] == ["totp_enabled"]


@pytest.mark.parametrize(
    ("before", "after", "event"),
    [
        ("hash-1", "hash-2", "password_changed"),
        (None, "hash-1", "password_changed"),
        ("hash-1", None, "password_removed"),
        ("hash-1", "hash-1", None),
        (None, None, None),
    ],
)
def test_an_edit_is_a_password_event_only_when_the_stored_password_changed(before: str | None, after: str | None, event: str | None) -> None:
    assert notification_manager.password_event(before, after) == event


def test_every_event_has_its_texts_in_the_catalog() -> None:
    for event in notification_manager.EVENTS:
        assert notification_manager.catalog.text("en", "events", event, "subject"), event
        assert notification_manager.catalog.text("en", "events", event, "text"), event


def test_nothing_is_queued_while_no_channel_is_enabled(outbox: SimpleNamespace) -> None:
    outbox.channels = []

    assert notification_manager.notify_user(ALICE, notification_manager.TOTP_DISABLED) == 0
    assert outbox.session.added == []


def test_an_administrator_is_named_as_the_one_who_made_the_change(outbox: SimpleNamespace) -> None:
    notification_manager.notify_user(ALICE, notification_manager.MFA_RESET, actor=ADMIN, factors=["totp"])

    [row] = outbox.session.added
    assert "Změnil(a): Administrátor Bob Admin" in row.body
    assert "Resetováno: Aplikace authenticator (TOTP)" in row.body


def test_the_ip_address_is_reported_from_the_request_that_made_the_change(outbox: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notification_manager.log_manager, "resolve_ip_address", lambda: "192.0.2.10")

    with Flask(__name__).test_request_context("/"):
        notification_manager.notify_user(ALICE, notification_manager.PASSKEY_ADDED, passkey_name="Work key")

    [row] = outbox.session.added
    assert "IP adresa: 192.0.2.10" in row.body
    assert "Passkey: Work key" in row.body


def test_a_failure_while_queueing_never_reaches_the_users_request(outbox: SimpleNamespace) -> None:
    outbox.session.fail_commit = True

    assert notification_manager.notify_user(ALICE, notification_manager.TOTP_ENABLED) == 0
    assert outbox.session.rollbacks == 1
    assert outbox.kicks == 0


@pytest.mark.parametrize(("attempts", "minutes"), [(1, 1), (2, 5), (3, 15), (4, 60), (5, 180), (6, 360), (9, 360)])
def test_retries_wait_longer_and_longer(attempts: int, minutes: int) -> None:
    assert notification_manager.retry_delay_minutes(attempts) == minutes


class Delivery:
    """A delivery round over claimed rows, with the database outcome recorded."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, rows: list, channel: object) -> None:
        """Serve the rows once, then nothing."""
        self.batches = [rows, []]
        self.sent: list[int] = []
        self.failed: list[tuple[int, int, str]] = []
        self.calls: list = []
        monkeypatch.setattr(notification_manager, "claim_due", lambda: self.batches.pop(0))
        monkeypatch.setattr(notification_manager.NotificationChannel, "find", classmethod(lambda _cls, _kind: channel))
        monkeypatch.setattr(notification_manager, "_mark_sent", self.sent.append)
        monkeypatch.setattr(
            notification_manager,
            "_mark_failed",
            lambda nid, attempts, error: self.failed.append((nid, attempts, error)) or False,
        )


def _row(notification_id: int, attempts: int = 1) -> SimpleNamespace:
    return SimpleNamespace(id=notification_id, channel_kind="email", recipient="alice@example.test", subject="S", body="B", attempts=attempts)


def _channel(*, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(enabled=enabled, config={"host": "smtp"}, get_secret_plaintext=lambda: "pw")


def test_delivered_notifications_are_marked_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    delivery = Delivery(monkeypatch, [_row(1), _row(2)], _channel())
    monkeypatch.setattr(notification_manager.CHANNELS["email"], "send", classmethod(lambda _cls, *args: delivery.calls.append(args)))

    assert notification_manager.deliver_due() == 2
    assert delivery.sent == [1, 2]
    assert delivery.calls[0] == ({"host": "smtp"}, "pw", "alice@example.test", "S", "B")


def test_a_failed_delivery_is_rescheduled_with_its_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    delivery = Delivery(monkeypatch, [_row(3, attempts=2)], _channel())

    def refuse(_cls: type, *_args: object) -> None:
        msg = "SMTP login failed: 535"
        raise ChannelError(msg)

    monkeypatch.setattr(notification_manager.CHANNELS["email"], "send", classmethod(refuse))

    assert notification_manager.deliver_due() == 0
    assert delivery.failed == [(3, 2, "SMTP login failed: 535")]


def test_a_channel_switched_off_after_queueing_holds_its_notifications_back(monkeypatch: pytest.MonkeyPatch) -> None:
    delivery = Delivery(monkeypatch, [_row(4)], _channel(enabled=False))

    notification_manager.deliver_due()

    assert delivery.failed == [(4, 1, "The email channel is not enabled")]


def test_giving_up_works_outside_a_request_like_the_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notification_manager, "_mark_failed", lambda *_args: True)

    # No request context here, as in the scheduler: this must not need one.
    notification_manager._report_failure(_row(6, attempts=notification_manager.MAX_ATTEMPTS), "refused")


class Statements:
    """Records the SQL a status change runs."""

    def __init__(self) -> None:
        """Start empty."""
        self.executed: list[tuple[str, dict]] = []

    def execute(self, statement: object, params: dict) -> None:
        """Record a statement."""
        self.executed.append((str(statement), params))

    def commit(self) -> None:
        """Commit."""


@pytest.mark.parametrize(
    ("attempts", "gives_up"),
    [(1, False), (notification_manager.MAX_ATTEMPTS - 1, False), (notification_manager.MAX_ATTEMPTS, True)],
)
def test_delivery_gives_up_after_the_last_attempt(monkeypatch: pytest.MonkeyPatch, attempts: int, *, gives_up: bool) -> None:
    statements = Statements()
    monkeypatch.setattr(notification_manager.db, "session", statements)

    assert notification_manager._mark_failed(5, attempts, "x" * 900) is gives_up

    [(sql, params)] = statements.executed
    assert ("status = 'failed'" in sql) is gives_up
    assert len(params["error"]) == notification_manager.MAX_ERROR_LENGTH


# --- Every change of a second factor raises its event -------------------------------------


@pytest.fixture
def raised(monkeypatch: pytest.MonkeyPatch) -> list:
    """The notifications raised, instead of queueing them."""
    events: list = []
    monkeypatch.setattr(notification_manager, "notify_user", lambda user, event, **kwargs: events.append((user, event, kwargs)) or 1)
    monkeypatch.setattr(notification_manager, "passkey_details", lambda record: {"passkey_name": record.name})
    return events


@pytest.fixture
def app() -> Flask:
    """A bare app for request contexts."""
    return Flask(__name__)


def _handler(resource: object, method: str) -> Callable[..., Any]:
    return getattr(type(resource), method).__wrapped__.__get__(resource)


def test_turning_totp_on_and_off_is_reported(monkeypatch: pytest.MonkeyPatch, raised: list, app: Flask) -> None:
    monkeypatch.setattr(user_api.auth_manager, "get_user_from_jwt", lambda: ALICE)
    monkeypatch.setattr(user_api.totp_manager, "confirm_enrollment", lambda _user, _code: True)
    monkeypatch.setattr(user_api.totp_manager, "disable", lambda _user, _code: True)

    with app.test_request_context("/", method="POST", json={"code": "123456"}):
        _handler(user_api.UserTotp(), "post")()
        _handler(user_api.UserTotp(), "delete")()

    assert [(user, event) for user, event, _ in raised] == [(ALICE, "totp_enabled"), (ALICE, "totp_disabled")]


def test_a_wrong_code_changes_nothing_and_reports_nothing(monkeypatch: pytest.MonkeyPatch, raised: list, app: Flask) -> None:
    monkeypatch.setattr(user_api.auth_manager, "get_user_from_jwt", lambda: ALICE)
    monkeypatch.setattr(user_api.totp_manager, "confirm_enrollment", lambda _user, _code: False)

    with app.test_request_context("/", method="POST", json={"code": "000000"}):
        _handler(user_api.UserTotp(), "post")()

    assert raised == []


def test_adding_and_removing_a_passkey_is_reported_with_its_name(monkeypatch: pytest.MonkeyPatch, raised: list, app: Flask) -> None:
    record = SimpleNamespace(id=7, user_id=ALICE.id, name="Work key", to_json=dict)
    monkeypatch.setattr(user_api.auth_manager, "get_user_from_jwt", lambda: ALICE)
    monkeypatch.setattr(user_api.webauthn_manager, "finish_registration", lambda *_args: record)
    monkeypatch.setattr(user_api.WebauthnCredential, "find", classmethod(lambda _cls, _id: record))
    monkeypatch.setattr(user_api.WebauthnCredential, "remove", classmethod(lambda _cls, _id, _user_id: True))

    with app.test_request_context("/", method="POST", json={"challenge_id": "c", "credential": {"id": "x"}, "name": "Work key"}):
        _handler(user_api.UserPasskeyRegisterFinish(), "post")()
        _handler(user_api.UserPasskey(), "delete")(7)

    assert raised == [
        (ALICE, "passkey_added", {"passkey_name": "Work key"}),
        (ALICE, "passkey_removed", {"passkey_name": "Work key"}),
    ]


def test_enrolling_a_second_factor_during_login_is_reported(monkeypatch: pytest.MonkeyPatch, raised: list) -> None:
    record = SimpleNamespace(name="Laptop")
    monkeypatch.setattr(auth_manager, "decode_scoped_token", lambda _token, _scope: {"sub": "alice"})
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: ALICE))
    monkeypatch.setattr(auth_manager.totp_manager, "confirm_enrollment", lambda _user, _code: True)
    monkeypatch.setattr(auth_manager.webauthn_manager, "passkey_second_factor_enabled", lambda: True)
    monkeypatch.setattr(auth_manager.webauthn_manager, "finish_registration", lambda *_args: record)
    monkeypatch.setattr(auth_manager.BaseAuthenticator, "generate_jwt", staticmethod(lambda _user: ({"access_token": "jwt"}, 200)))

    auth_manager.complete_totp_enrollment("token", "123456")
    auth_manager.complete_passkey_enrollment("token", "challenge", {"id": "x"}, "Laptop")

    assert [(event, kwargs) for _user, event, kwargs in raised] == [("totp_enabled", {}), ("passkey_added", {"passkey_name": "Laptop"})]


class EditedUser(SimpleNamespace):
    """A user whose stored password an edit replaces, as User.update does."""


def _edit(monkeypatch: pytest.MonkeyPatch, target: EditedUser, new_password: str | None, method: str) -> None:
    def update(*_args: object) -> None:
        target.password = new_password

    monkeypatch.setattr(config_api.user.User, "find_by_id", classmethod(lambda _cls, _id: target))
    monkeypatch.setattr(config_api.user.User, method, classmethod(lambda _cls, *args: update(*args)))
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: ADMIN)
    monkeypatch.setattr(config_api.auth_manager, "get_user_from_jwt", lambda: ADMIN)
    monkeypatch.setattr(config_api.auth_manager, "get_external_permissions_ids", list)


@pytest.mark.parametrize(
    ("new_password", "expected"),
    [("new-hash", [("password_changed", ADMIN)]), (None, [("password_removed", ADMIN)]), ("old-hash", [])],
)
def test_an_administrators_edit_reports_a_changed_or_removed_password(
    monkeypatch: pytest.MonkeyPatch,
    raised: list,
    app: Flask,
    new_password: str | None,
    expected: list,
) -> None:
    target = EditedUser(id=3, name="Carol", username="carol", email="carol@example.test", password="old-hash")
    _edit(monkeypatch, target, new_password, "update")

    with app.test_request_context("/", method="PUT", json={}):
        _handler(config_api.UserResource(), "put")(3)

    assert [(event, kwargs["actor"]) for user, event, kwargs in raised if user is target] == expected


def test_an_organisation_admins_edit_of_an_external_user_reports_a_new_password(
    monkeypatch: pytest.MonkeyPatch,
    raised: list,
    app: Flask,
) -> None:
    target = EditedUser(id=4, name="Dave", username="dave", email="dave@example.test", password="old-hash")
    _edit(monkeypatch, target, "new-hash", "update_external")

    with app.test_request_context("/", method="PUT", json={}):
        _handler(config_api.ExternalUserResource(), "put")(4)

    assert [event for _user, event, _kwargs in raised] == ["password_changed"]


def test_an_administrators_reset_reports_only_the_factors_the_user_had(monkeypatch: pytest.MonkeyPatch, raised: list, app: Flask) -> None:
    target = SimpleNamespace(id=3, name="Carol", username="carol", email="carol@example.test", totp_secret="secret", webauthn_credentials=[])
    monkeypatch.setattr(config_api.user.User, "find_by_id", classmethod(lambda _cls, _id: target))
    monkeypatch.setattr(config_api.user.User, "reset_mfa", classmethod(lambda _cls, _id, **_kwargs: None))
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: ADMIN)
    monkeypatch.setattr(config_api.log_manager, "store_user_activity", lambda *_args: None)

    with app.test_request_context("/", method="POST", json={"reset_totp": True, "reset_passkeys": True}):
        _handler(config_api.UserMfaResetResource(), "post")(3)
        target.totp_secret = None  # nothing left to lose
        _handler(config_api.UserMfaResetResource(), "post")(3)

    assert raised == [(target, "mfa_reset", {"actor": ADMIN, "factors": ["totp"]})]
