"""A signed-in user acts with the permissions their account has now.

``auth_required`` took a JWT request's permissions from the token, copied there when it was
issued. Taking a role away from someone changed nothing until their token expired - and the GUI
refreshes it every few hours, with whatever the account then held, so a session that stayed open
kept the role it had.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from flask import Flask
from managers import auth_manager

APP = Flask(__name__)


@auth_manager.auth_required("PUBLISH_ACCESS")
def _publish() -> tuple[dict, HTTPStatus]:
    return {"ok": True}, HTTPStatus.OK


@pytest.fixture
def signed_in(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A JWT request of a user whose token claims PUBLISH_ACCESS."""
    account = SimpleNamespace(id=1, username="alice", permissions=[], roles=[])
    monkeypatch.setattr(auth_manager, "uses_api_key", lambda: False)
    monkeypatch.setattr(auth_manager, "get_user_from_jwt_token", lambda: account)
    monkeypatch.setattr(auth_manager, "get_jwt", lambda: {"user_claims": {"permissions": ["PUBLISH_ACCESS"]}})
    for name in ("store_user_activity", "store_user_auth_error_activity", "store_auth_error_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return account


def _call() -> tuple:
    with APP.test_request_context("/"):
        return _publish()


def test_a_permission_the_account_lost_no_longer_works(signed_in: SimpleNamespace) -> None:  # noqa: ARG001
    # The token still says PUBLISH_ACCESS; the account no longer has it.
    assert _call()[1] == HTTPStatus.UNAUTHORIZED


def test_a_permission_the_account_has_works(signed_in: SimpleNamespace) -> None:
    signed_in.roles = [SimpleNamespace(permissions=[SimpleNamespace(id="PUBLISH_ACCESS")])]

    assert _call() == ({"ok": True}, HTTPStatus.OK)
