"""Remote clients negotiate once and never acknowledge invalid or failed imports."""

from __future__ import annotations

import threading
from http import HTTPStatus
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
import requests
from flask import Flask
from managers import remote_manager
from marshmallow import ValidationError
from remote.remote_api import RemoteApi

if TYPE_CHECKING:
    from collections.abc import Iterator


UTC_CURSOR = "2026-07-01T22:30:00.123456Z"
LEGACY_CURSOR = "2026-07-02 00:30:00.123456"


def response(status: int, payload: object) -> Mock:
    """Build a transport response without touching the network."""
    return Mock(status_code=status, json=Mock(return_value=payload))


def access_info(cursor: str = UTC_CURSOR) -> dict:
    """Connection metadata served by both protocol versions."""
    return {"event_id": "event-1", "last_synced_news_items": cursor, "last_synced_report_items": cursor}


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> tuple[Mock, Mock]:
    """Record GET and PUT URLs and bodies."""
    get, put = Mock(), Mock(return_value=response(204, None))
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "put", put)
    return get, put


def test_v2_connection_keeps_one_protocol_for_get_put_and_disconnect(transport: tuple[Mock, Mock]) -> None:
    get, put = transport
    get.side_effect = [response(200, access_info()), response(200, {"news_items": [], "last_sync_time": UTC_CURSOR}), response(204, None)]
    api = RemoteApi("https://peer.test/", "secret")
    assert api.connect()[1] == HTTPStatus.OK
    assert api.version == 2
    batch, status = api.get_news_items()
    assert status == HTTPStatus.OK
    assert api.confirm_news_items_sync({"last_sync_time": batch["last_sync_time"]})[1] == HTTPStatus.NO_CONTENT
    assert api.disconnect()[1] == HTTPStatus.NO_CONTENT
    assert [call.args[0] for call in get.call_args_list] == [
        "https://peer.test/api/v2/remote/connect",
        "https://peer.test/api/v2/remote/sync-news-items",
        "https://peer.test/api/v2/remote/disconnect",
    ]
    assert put.call_args.args[0] == "https://peer.test/api/v2/remote/sync-news-items"
    assert put.call_args.kwargs["json"] == {"last_sync_time": UTC_CURSOR}


@pytest.mark.parametrize("missing_status", [404, 405])
def test_old_peer_negotiation_converts_metadata_and_keeps_publication_opaque(
    transport: tuple[Mock, Mock],
    missing_status: int,
) -> None:
    get, put = transport
    get.side_effect = [
        response(missing_status, "old proxy HTML"),
        response(200, access_info(LEGACY_CURSOR)),
        response(
            200,
            {"news_items": [{"collected": "02.07.2026 - 00:30", "published": "02.07.2026 - 00:15"}], "last_sync_time": LEGACY_CURSOR},
        ),
        response(204, None),
    ]
    api = RemoteApi("https://peer.test", "secret", legacy_timezone="Europe/Bratislava")
    assert api.connect()[1] == HTTPStatus.OK
    assert api.version == 1
    batch, status = api.get_news_items()
    assert status == HTTPStatus.OK
    assert batch["news_items"] == [{"collected": "2026-07-01T22:30:00Z", "published": "02.07.2026 - 00:15"}]
    assert batch["last_sync_time"] == LEGACY_CURSOR
    assert api.confirm_news_items_sync({"last_sync_time": batch["last_sync_time"]})[1] == HTTPStatus.NO_CONTENT
    assert api.disconnect()[1] == HTTPStatus.NO_CONTENT
    assert all("/v1/" in call.args[0] for call in get.call_args_list[1:])
    assert put.call_args.kwargs["json"] == {"last_sync_time": LEGACY_CURSOR}
    assert "/v1/" in put.call_args.args[0]


@pytest.mark.parametrize("status", [401, 403, 500, 502])
def test_auth_and_server_failures_never_trigger_legacy_fallback(transport: tuple[Mock, Mock], status: int) -> None:
    get, _put = transport
    get.return_value = response(status, {"error": "failure"})
    api = RemoteApi("https://peer.test", "secret")
    assert api.connect()[1] == status
    assert get.call_count == 1
    assert api.version == 2


def test_network_failure_never_triggers_legacy_fallback(transport: tuple[Mock, Mock]) -> None:
    get, _put = transport
    get.side_effect = requests.ConnectionError("unreachable")
    api = RemoteApi("https://peer.test", "secret")
    assert api.connect()[1] == HTTPStatus.SERVICE_UNAVAILABLE
    assert get.call_count == 1


@pytest.mark.parametrize("payload", [None, [], {}, access_info(LEGACY_CURSOR)])
def test_malformed_v2_success_is_rejected_without_fallback(transport: tuple[Mock, Mock], payload: object) -> None:
    get, _put = transport
    get.return_value = response(200, payload)
    assert RemoteApi("https://peer.test", "secret").connect()[1] == HTTPStatus.BAD_GATEWAY
    assert get.call_count == 1


def test_successful_response_with_invalid_json_is_a_gateway_error(transport: tuple[Mock, Mock]) -> None:
    get, _put = transport
    broken = response(200, None)
    broken.json.side_effect = requests.exceptions.JSONDecodeError("invalid", "x", 0)
    get.return_value = broken
    assert RemoteApi("https://peer.test", "secret").connect()[1] == HTTPStatus.BAD_GATEWAY
    assert get.call_count == 1


def test_v1_acknowledgment_adapts_offset_cursor_to_the_old_strict_parser(transport: tuple[Mock, Mock]) -> None:
    _get, put = transport
    api = RemoteApi("https://peer.test", "secret", legacy_timezone="Europe/Bratislava", version=1)
    assert api.confirm_news_items_sync({"last_sync_time": UTC_CURSOR})[1] == HTTPStatus.NO_CONTENT
    assert put.call_args.kwargs["json"] == {"last_sync_time": LEGACY_CURSOR}


@pytest.mark.parametrize("collected", ["02.07.2026 - 00:30", "2026-07-02T00:30:00", "invalid"])
def test_v2_naive_or_invalid_collection_metadata_is_rejected(transport: tuple[Mock, Mock], collected: str) -> None:
    get, _put = transport
    get.return_value = response(200, {"news_items": [{"collected": collected}], "last_sync_time": UTC_CURSOR})
    assert RemoteApi("https://peer.test", "secret", version=2).get_news_items()[1] == HTTPStatus.BAD_GATEWAY


def test_report_attribute_text_is_not_reinterpreted_as_timestamps(transport: tuple[Mock, Mock]) -> None:
    get, _put = transport
    reports = [{"attributes": [{"key": "collected", "value": "02.07.2026 - 00:30"}], "title": "An advisory"}]
    get.return_value = response(200, {"report_items": reports, "last_sync_time": UTC_CURSOR})
    data, status = RemoteApi("https://peer.test", "secret", version=2).get_report_items()
    assert status == HTTPStatus.OK
    assert data["report_items"] == reports


@pytest.fixture
def manager_context(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """Contain database writes and background threads behind explicit fakes."""
    session = Mock()
    monkeypatch.setattr(remote_manager, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(remote_manager.EventThread, "app", Flask("remote-client-tests"))
    monkeypatch.setattr(remote_manager, "sse_manager", SimpleNamespace(sse_manager=Mock()))
    remote_manager.remote_clients.clear()
    remote_manager.event_handlers.clear()
    node = SimpleNamespace(
        id=42,
        name="Peer",
        remote_url="https://peer.test",
        api_key="secret",
        legacy_timezone="Europe/Bratislava",
        api_version=1,
        osint_source_group_id="group-1",
        connect=Mock(),
        disconnect=Mock(),
        enabled=True,
    )
    monkeypatch.setattr(remote_manager.RemoteNode, "find", Mock(return_value=node))
    yield SimpleNamespace(node=node, session=session)
    remote_manager.remote_clients.clear()
    remote_manager.event_handlers.clear()


def test_manager_retains_the_negotiated_client_for_events_and_manual_disconnect(
    manager_context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = Mock(version=1)
    api.connect.return_value = (access_info(LEGACY_CURSOR), HTTPStatus.OK)
    api.disconnect.return_value = ({}, HTTPStatus.OK)
    constructor = Mock(return_value=api)
    events = Mock()
    monkeypatch.setattr(remote_manager, "RemoteApi", constructor)
    monkeypatch.setattr(remote_manager, "connect_to_events", events)
    assert remote_manager.connect_to_node(42)[1] == HTTPStatus.OK
    events.assert_called_once_with(manager_context.node, api)
    manager_context.node.connect.assert_called_once_with(access_info(LEGACY_CURSOR), api_version=1)
    remote_manager.disconnect_from_node(42)
    assert constructor.call_count == 1
    api.disconnect.assert_called_once()
    assert 42 not in remote_manager.remote_clients


def test_failed_import_rolls_back_and_does_not_acknowledge(
    manager_context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = Mock(version=1)
    api.get_news_items.return_value = ({"news_items": [], "last_sync_time": LEGACY_CURSOR}, HTTPStatus.OK)
    monkeypatch.setattr(remote_manager.NewsItemAggregate, "add_remote_news_items", Mock(side_effect=ValidationError("bad batch")))
    thread = remote_manager.EventThread(manager_context.node, threading.Event(), api)
    assert thread._sync(news=True) is False
    manager_context.session.rollback.assert_called_once()
    api.confirm_news_items_sync.assert_not_called()


def test_failed_acknowledgment_is_reported_as_failed_sync(
    manager_context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = Mock(version=2)
    api.get_news_items.return_value = ({"news_items": [], "last_sync_time": UTC_CURSOR}, HTTPStatus.OK)
    api.confirm_news_items_sync.return_value = ({}, HTTPStatus.BAD_GATEWAY)
    importer = Mock()
    monkeypatch.setattr(remote_manager.NewsItemAggregate, "add_remote_news_items", importer)
    thread = remote_manager.EventThread(manager_context.node, threading.Event(), api)
    assert thread._sync(news=True) is False
    importer.assert_called_once_with([], manager_context.node, "group-1", api_version=2)
    api.confirm_news_items_sync.assert_called_once_with({"last_sync_time": UTC_CURSOR})


def test_invalid_connect_response_is_contained_and_state_cleared(
    manager_context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = Mock(version=2)
    api.connect.return_value = (access_info(), HTTPStatus.OK)
    api.disconnect.return_value = ({}, HTTPStatus.OK)
    manager_context.node.connect.side_effect = ValidationError("invalid timestamp")
    monkeypatch.setattr(remote_manager, "RemoteApi", Mock(return_value=api))
    events = Mock()
    monkeypatch.setattr(remote_manager, "connect_to_events", events)
    assert remote_manager.connect_to_node(42)[1] == HTTPStatus.BAD_GATEWAY
    assert manager_context.session.rollback.called
    manager_context.node.disconnect.assert_called_once()
    api.disconnect.assert_called_once()
    events.assert_not_called()


def test_startup_continues_after_one_peer_fails(manager_context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    nodes = [manager_context.node, SimpleNamespace(id=43, name="Second peer", enabled=True)]
    monkeypatch.setattr(remote_manager.RemoteNode, "get", Mock(return_value=(nodes, 2)))
    connector = Mock(side_effect=[ValidationError("bad peer"), ({}, HTTPStatus.OK)])
    monkeypatch.setattr(remote_manager, "connect_to_node", connector)
    remote_manager.initialize(Flask("startup-tests"))
    assert [call.args[0] for call in connector.call_args_list] == [42, 43]


def test_malformed_successful_connect_cleans_up_the_remote_session(
    manager_context: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    transport: tuple[Mock, Mock],
) -> None:
    get, _put = transport
    get.side_effect = [response(200, access_info(LEGACY_CURSOR)), response(204, None)]
    events = Mock()
    monkeypatch.setattr(remote_manager, "connect_to_events", events)
    assert remote_manager.connect_to_node(42)[1] == HTTPStatus.BAD_GATEWAY
    assert [call.args[0] for call in get.call_args_list] == [
        "https://peer.test/api/v2/remote/connect",
        "https://peer.test/api/v2/remote/disconnect",
    ]
    manager_context.node.disconnect.assert_called_once()
    events.assert_not_called()


def test_invalid_peer_timezone_is_a_configuration_error(manager_context: SimpleNamespace) -> None:
    manager_context.node.legacy_timezone = "not/a/timezone"
    assert remote_manager.connect_to_node(42)[1] == HTTPStatus.BAD_REQUEST
    manager_context.node.disconnect.assert_called_once()


def test_manual_disconnect_clears_state_even_with_invalid_legacy_settings(manager_context: SimpleNamespace) -> None:
    manager_context.node.legacy_timezone = "not/a/timezone"
    remote_manager.disconnect_from_node(42)
    manager_context.node.disconnect.assert_called_once()


@pytest.mark.parametrize("missing_status", [404, 405])
def test_manual_disconnect_without_runtime_version_falls_back_without_connecting(
    manager_context: SimpleNamespace,
    transport: tuple[Mock, Mock],
    missing_status: int,
) -> None:
    get, _put = transport
    del manager_context.node.api_version
    get.side_effect = [response(missing_status, "old proxy HTML"), response(204, None)]
    remote_manager.disconnect_from_node(42)
    assert [call.args[0] for call in get.call_args_list] == [
        "https://peer.test/api/v2/remote/disconnect",
        "https://peer.test/api/v1/remote/disconnect",
    ]
    manager_context.node.disconnect.assert_called_once()


@pytest.mark.parametrize("known_by_connect", [True, False])
def test_disconnect_never_changes_a_known_protocol(transport: tuple[Mock, Mock], known_by_connect: bool) -> None:
    get, _put = transport
    if known_by_connect:
        api = RemoteApi("https://peer.test", "secret")
        get.return_value = response(200, access_info())
        assert api.connect()[1] == HTTPStatus.OK
        get.reset_mock()
    else:
        api = RemoteApi("https://peer.test", "secret", version=2)
    get.return_value = response(404, {"error": "missing"})
    assert api.disconnect()[1] == HTTPStatus.NOT_FOUND
    get.assert_called_once_with("https://peer.test/api/v2/remote/disconnect", headers=api.headers, timeout=30)
    assert api.version == 2


@pytest.mark.parametrize("status", [401, 403, 500])
def test_unknown_disconnect_does_not_fall_back_on_auth_or_server_errors(transport: tuple[Mock, Mock], status: int) -> None:
    get, _put = transport
    get.return_value = response(status, {"error": "failure"})
    api = RemoteApi("https://peer.test", "secret")
    assert api.disconnect()[1] == status
    assert get.call_count == 1
    assert api.version == 2


def test_unknown_disconnect_does_not_fall_back_on_network_error(transport: tuple[Mock, Mock]) -> None:
    get, _put = transport
    get.side_effect = requests.ConnectionError("unreachable")
    api = RemoteApi("https://peer.test", "secret")
    assert api.disconnect()[1] == HTTPStatus.SERVICE_UNAVAILABLE
    assert get.call_count == 1
    assert api.version == 2
