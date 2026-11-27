"""A disabled Remote Access's key authenticates nothing.

``enabled`` used to be checked only in ``connect()``: the sync endpoints and the event stream
took the key regardless, so a peer an administrator had switched off kept pulling every news
item and report item it was ever configured for, and could rewind its own sync cursor to get
the whole history again.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import sse
from flask import Flask
from managers import auth_manager
from model.remote import RemoteAccess

APP = Flask(__name__)


@pytest.fixture
def remote_access(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    access = types.SimpleNamespace(name="peer", enabled=True)
    monkeypatch.setattr(RemoteAccess, "get_by_api_key", classmethod(lambda _cls, _key: access))
    for name in ("store_auth_error_activity", "store_auth_warning_activity"):
        monkeypatch.setattr(auth_manager.log_manager, name, lambda *_args, **_kwargs: None)
    return access


@auth_manager.api_key_required("remote")
def _sync(remote_node: types.SimpleNamespace) -> tuple[dict, HTTPStatus]:
    return {"served": remote_node.name}, HTTPStatus.OK


def _call() -> tuple[dict, HTTPStatus]:
    with APP.test_request_context("/api/v1/remote/sync-news-items", headers={"Authorization": "ApiKey k3y"}):
        return _sync()


def test_an_enabled_remote_access_is_served(remote_access: types.SimpleNamespace) -> None:  # noqa: ARG001
    assert _call() == ({"served": "peer"}, HTTPStatus.OK)


@pytest.mark.parametrize("enabled", [False, None])
def test_a_disabled_remote_access_is_refused(remote_access: types.SimpleNamespace, enabled: bool | None) -> None:
    remote_access.enabled = enabled

    assert _call()[1] == HTTPStatus.UNAUTHORIZED


def test_a_disabled_remote_access_gets_no_event_stream(remote_access: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    remote_access.enabled = False
    monkeypatch.setattr(sse.logger, "warning", lambda *_args, **_kwargs: None)

    with APP.test_request_context("/sse?channel=remote", headers={"Authorization": "ApiKey k3y"}):
        body, status = sse.SseResource().get()

    assert status == HTTPStatus.FORBIDDEN
    assert "disabled" in body
