"""The API key endpoints: who may act on which key, what comes back, what is logged and reported.

The ``auth_required`` decorator is covered by ``test_api_key_auth``; here the handlers run
through ``__wrapped__`` with the caller injected, and the model's storage is stubbed.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from api import config as config_api
from api import user as user_api
from flask import Flask
from managers import api_key_manager

if TYPE_CHECKING:
    from collections.abc import Callable

    Handler = Callable[..., tuple[dict, HTTPStatus]]

ADMIN = SimpleNamespace(id=1, username="admin", name="Admin")
OWNER = SimpleNamespace(id=3, username="soar", name="SOAR", status="active", get_permissions=lambda: ["ASSESS_ACCESS"])
PLAINTEXT = "tnk_the-plaintext-key"


class _Key:
    def __init__(self, user_id: int = 3) -> None:
        self.id = 7
        self.name = "SOAR sync"
        self.key_prefix = "tnk_abcdefgh"
        self.user = OWNER if user_id == OWNER.id else SimpleNamespace(id=user_id, username="other")
        self.user_id = user_id
        self.expires_at = None
        self.updates: list[dict] = []

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "key_prefix": self.key_prefix}

    def apply_update(self, data: dict, *, policy: dict) -> None:  # noqa: ARG002
        self.updates.append(data)


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Record the activity log, the notifications and the deletes."""
    recorded = SimpleNamespace(activity=[], notified=[], deleted=[], rollbacks=0)
    monkeypatch.setattr(
        api_key_manager.log_manager,
        "store_user_activity",
        lambda user, kind, detail, **_k: recorded.activity.append((user, kind, detail)),
    )
    monkeypatch.setattr(
        api_key_manager.notification_manager,
        "notify_user",
        lambda user, event, *, actor=None, **details: recorded.notified.append((user, event, actor, details)),
    )
    monkeypatch.setattr(api_key_manager.ApiKey, "delete", classmethod(lambda _cls, api_key_id: recorded.deleted.append(api_key_id)))
    monkeypatch.setattr(
        api_key_manager.SecuritySettings,
        "get_api_key_policy",
        classmethod(lambda _cls: {"require_expiry": False, "max_days": 30, "require_allowlist": False, "allowed_ips": "10.0.0.0/8"}),
    )

    def rollback() -> None:
        recorded.rollbacks += 1

    monkeypatch.setattr(user_api.db, "session", SimpleNamespace(rollback=rollback))
    return recorded


def _created(_cls: type, owner: object, data: dict, *, created_by: str, policy: dict) -> tuple[_Key, str]:  # noqa: ARG001
    if not data.get("name"):
        msg = "The API key needs a name"
        raise ValueError(msg)
    return _Key(owner.id), PLAINTEXT


def _handler(resource_class: type, method: str) -> Handler:
    resource = resource_class()
    return getattr(resource, method).__wrapped__.__get__(resource)


def _call(handler: Handler, body: dict | None = None, *args: object) -> tuple[dict, HTTPStatus]:
    app = Flask(__name__)
    with app.test_request_context("/", method="POST", json=body or {}, environ_base={"REMOTE_ADDR": "198.51.100.7"}):
        return handler(*args)


def test_a_new_key_is_returned_once_and_its_owner_is_told(monkeypatch: pytest.MonkeyPatch, recorded: SimpleNamespace) -> None:
    monkeypatch.setattr(config_api.user.User, "find_by_id", classmethod(lambda _cls, user_id: OWNER if user_id == OWNER.id else None))
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: ADMIN)
    monkeypatch.setattr(api_key_manager.ApiKey, "create", classmethod(_created))

    body, status = _call(_handler(config_api.ApiKeysResource, "post"), {"user_id": 3, "name": "SOAR sync"})

    assert status == HTTPStatus.CREATED
    assert body == {"item": {"id": 7, "name": "SOAR sync", "key_prefix": "tnk_abcdefgh"}, "key": PLAINTEXT}
    assert recorded.activity == [(ADMIN, "API_KEY_CREATE", "API key 'SOAR sync' (tnk_abcdefgh…) of soar created")]
    assert PLAINTEXT not in repr(recorded.activity)
    ((user, event, actor, details),) = recorded.notified
    assert (user, event, actor) == (OWNER, "api_key_created", ADMIN)
    assert details["api_key_name"] == "SOAR sync"
    assert details["api_key_prefix"] == "tnk_abcdefgh…"


@pytest.mark.parametrize("body", [{}, {"user_id": "3"}, {"user_id": 99}])
def test_an_admin_must_name_an_existing_owner(monkeypatch: pytest.MonkeyPatch, recorded: SimpleNamespace, body: dict) -> None:
    monkeypatch.setattr(config_api.user.User, "find_by_id", classmethod(lambda _cls, user_id: OWNER if user_id == OWNER.id else None))
    response, status = _call(_handler(config_api.ApiKeysResource, "post"), {**body, "name": "x"})
    assert status == HTTPStatus.BAD_REQUEST
    assert response == {"error": "Choose the user the API key acts as"}
    assert recorded.notified == []


def test_a_broken_rule_is_answered_with_what_to_fix(monkeypatch: pytest.MonkeyPatch, recorded: SimpleNamespace) -> None:
    monkeypatch.setattr(user_api.auth_manager, "get_user_from_jwt", lambda: OWNER)
    monkeypatch.setattr(api_key_manager.ApiKey, "create", classmethod(_created))

    body, status = _call(_handler(user_api.UserApiKeys, "post"), {"name": ""})

    assert (body, status) == ({"error": "The API key needs a name"}, HTTPStatus.BAD_REQUEST)
    assert recorded.rollbacks == 1
    assert recorded.notified == []


def test_users_see_and_change_only_their_own_keys(monkeypatch: pytest.MonkeyPatch, recorded: SimpleNamespace) -> None:
    keys = {7: _Key(user_id=3), 8: _Key(user_id=4)}
    monkeypatch.setattr(user_api.auth_manager, "get_user_from_jwt", lambda: OWNER)
    monkeypatch.setattr(
        user_api.ApiKey,
        "find_for_user",
        classmethod(
            lambda _cls, api_key_id, user_id: keys[api_key_id] if keys.get(api_key_id) and keys[api_key_id].user_id == user_id else None,
        ),
    )

    assert _call(_handler(user_api.UserApiKey, "put"), {"enabled": False}, 8)[1] == HTTPStatus.NOT_FOUND
    assert _call(_handler(user_api.UserApiKey, "delete"), None, 8)[1] == HTTPStatus.NOT_FOUND
    assert keys[8].updates == []
    assert recorded.deleted == []

    assert _call(_handler(user_api.UserApiKey, "put"), {"enabled": False}, 7)[1] == HTTPStatus.OK
    assert keys[7].updates == [{"enabled": False}]
    assert recorded.activity[-1][1:] == ("API_KEY_UPDATE", "API key 'SOAR sync' (tnk_abcdefgh…) of soar updated (enabled)")

    assert _call(_handler(user_api.UserApiKey, "delete"), None, 7)[1] == HTTPStatus.OK
    assert recorded.deleted == [7]
    assert recorded.notified[-1][:3] == (OWNER, "api_key_deleted", OWNER)


@pytest.mark.usefixtures("recorded")
def test_the_list_carries_the_policy_the_callers_address_and_the_picker_options(monkeypatch: pytest.MonkeyPatch) -> None:
    permission = SimpleNamespace(id="ASSESS_ACCESS", name="Assess access", description="Access to Assess")
    monkeypatch.setattr(
        api_key_manager.Permission,
        "find",
        classmethod(lambda _cls, permission_id: permission if permission_id == "ASSESS_ACCESS" else None),
    )
    app = Flask(__name__)
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "198.51.100.7"}):
        payload = api_key_manager.list_payload([_Key()], permissions_of=OWNER)

    assert payload["total_count"] == 1
    assert payload["client_ip"] == "198.51.100.7"
    assert payload["client_ip_public"] is False  # a documentation address cannot be listed
    # the site-wide list is only said to exist; a cap implies that an expiry is required
    assert payload["policy"] == {"require_expiry": True, "max_days": 30, "require_allowlist": False, "site_allowlist_active": True}
    assert payload["available_permissions"] == [{"id": "ASSESS_ACCESS", "name": "Assess access", "description": "Access to Assess"}]
    assert "owners" not in payload
