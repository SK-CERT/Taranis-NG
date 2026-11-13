"""An administrator can clear a public-web node's cache on demand.

The resets core pushes after each change go only to nodes it thinks are up, on a thread, and
nobody learns how they went. This one is asked for: it goes to the node whatever its health
says and reports the node's answer.
"""

from __future__ import annotations

import types
from http import HTTPStatus

import pytest
from api import config as config_api
from flask import Flask
from remote import public_web_api


class _Node:
    def __init__(self, *, api_url: str = "http://public-web") -> None:
        self.id = 4
        self.name = "Cyberfeed node"
        self.api_url = api_url
        self.api_key = "secret"
        self.seen = False

    def update_last_seen(self) -> None:
        self.seen = True


@pytest.fixture
def activity(monkeypatch: pytest.MonkeyPatch) -> list:
    """The activities logged; no user, no database."""
    logged: list = []
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: None)
    monkeypatch.setattr(config_api.log_manager, "store_user_activity", lambda _user, kind, detail: logged.append((kind, detail)))
    monkeypatch.setattr(config_api.log_manager, "store_data_error_activity", lambda _user, msg, _ex: logged.append(("ERROR", msg)))
    return logged


def _post(monkeypatch: pytest.MonkeyPatch, node: _Node | None, answer: tuple | None = None) -> tuple[dict, HTTPStatus]:
    calls: list = []

    class _Api:
        def __init__(self, api_url: str, api_key: str) -> None:
            calls.append((api_url, api_key))

        def reset_cache(self) -> tuple:
            return answer

    monkeypatch.setattr(config_api.db, "session", types.SimpleNamespace(get=lambda _model, _node_id: node))
    monkeypatch.setattr(public_web_api, "PublicWebApi", _Api)
    resource = config_api.PublicWebNodeCacheResource()
    with Flask(__name__).test_request_context("/", method="POST"):
        result = resource.post.__wrapped__(resource, node_id=4)
    if answer is not None:
        assert calls == [("http://public-web", "secret")]
    return result


def test_the_node_drops_its_cache_and_counts_as_seen(monkeypatch: pytest.MonkeyPatch, activity: list) -> None:
    node = _Node()

    body, status = _post(monkeypatch, node, ({"reset": True}, HTTPStatus.OK))

    assert (body, status) == ({"reset": True}, HTTPStatus.OK)
    assert node.seen
    assert activity == [("PUBLIC_WEB_CACHE_RESET", "Cache of public-web node 'Cyberfeed node' cleared")]


@pytest.mark.parametrize(
    ("answer", "status", "message"),
    [
        (HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.SERVICE_UNAVAILABLE, "could not be reached"),
        (HTTPStatus.UNAUTHORIZED, HTTPStatus.BAD_GATEWAY, "rejected the API key"),
        (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_GATEWAY, "answered with HTTP 404"),
    ],
)
def test_a_node_that_did_not_clear_it_says_why(
    monkeypatch: pytest.MonkeyPatch,
    activity: list,
    answer: HTTPStatus,
    status: HTTPStatus,
    message: str,
) -> None:
    node = _Node()

    body, got = _post(monkeypatch, node, ({"error": "x"}, answer))

    assert got == status
    assert "Cyberfeed node" in body["error"]
    assert message in body["error"]
    assert not node.seen
    assert activity == []


@pytest.mark.usefixtures("activity")
def test_an_unknown_node_is_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _post(monkeypatch, None) == ({"error": "Public-web node not found"}, HTTPStatus.NOT_FOUND)


@pytest.mark.usefixtures("activity")
def test_a_node_without_management_url_cannot_be_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    body, status = _post(monkeypatch, _Node(api_url=""))

    assert status == HTTPStatus.BAD_REQUEST
    assert "API URL" in body["error"]


def test_the_route_needs_the_node_update_permission() -> None:
    import inspect  # noqa: PLC0415

    source = inspect.getsource(config_api.PublicWebNodeCacheResource)
    assert '@auth_required("CONFIG_PUBLIC_WEB_NODE_UPDATE")' in source
    assert '"/api/v1/config/public-web-nodes/<int:node_id>/reset-cache"' in inspect.getsource(config_api.initialize)
