"""Legacy remote peers retain their wall-clock wire format while v2 exchanges UTC."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from api import remote as remote_api
from flask import Flask
from managers import auth_manager
from managers.api_manager import SafeErrorApi
from managers.db_manager import db
from model.remote import RemoteAccess

if TYPE_CHECKING:
    from flask.testing import FlaskClient

AUTHORIZATION = {"Authorization": "ApiKey test-remote-key"}
STAMP = datetime(2026, 7, 15, 10, 0, tzinfo=UTC)


@pytest.fixture
def remote_client(monkeypatch: pytest.MonkeyPatch) -> tuple[FlaskClient, RemoteAccess]:
    monkeypatch.setattr(db.session, "commit", lambda: None)
    node = RemoteAccess(
        id=None,
        name="Remote",
        description="",
        enabled=True,
        api_key="test-remote-key",
        osint_sources=[],
        report_item_types=[],
    )
    node.legacy_timezone = "Europe/Bratislava"
    node.last_synced_news_items = STAMP
    node.last_synced_report_items = STAMP
    monkeypatch.setattr(RemoteAccess, "get_by_api_key", classmethod(lambda _cls, key: node if key == "test-remote-key" else None))
    monkeypatch.setattr(auth_manager.log_manager, "store_auth_error_activity", lambda *_args, **_kwargs: None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    remote_api.initialize(SafeErrorApi(app))
    return app.test_client(), node


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("microsecond", [0, 123456])
def test_connect_keeps_exact_original_keys_and_versioned_cursors(
    remote_client: tuple[FlaskClient, RemoteAccess],
    version: int,
    microsecond: int,
) -> None:
    client, node = remote_client
    node.last_synced_news_items = STAMP.replace(microsecond=microsecond)
    response = client.get(f"/api/v{version}/remote/connect", headers=AUTHORIZATION)
    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {"event_id", "last_synced_news_items", "last_synced_report_items", "news_items_provided", "report_items_provided"}
    assert data["event_id"] == node.event_id
    assert data["news_items_provided"] is False
    assert data["report_items_provided"] is False
    for key, expected in (("last_synced_news_items", STAMP.replace(microsecond=microsecond)), ("last_synced_report_items", STAMP)):
        if version == 1:
            # This is the exact strptime used by old remote clients, including .000000.
            parsed = datetime.strptime(data[key], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=ZoneInfo(node.legacy_timezone))
            assert parsed.astimezone(UTC) == expected
            assert "+" not in data[key]
            assert not data[key].endswith("Z")
        else:
            assert data[key].endswith("Z")
            assert datetime.fromisoformat(data[key]) == expected


@pytest.mark.parametrize(("version", "expected"), [(1, "2026-01-15 11:00:00.000000"), (2, "2026-01-15T10:00:00Z")])
def test_connect_uses_peer_timezone_winter_offset(
    remote_client: tuple[FlaskClient, RemoteAccess],
    version: int,
    expected: str,
) -> None:
    client, node = remote_client
    node.last_synced_news_items = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
    assert client.get(f"/api/v{version}/remote/connect", headers=AUTHORIZATION).get_json()["last_synced_news_items"] == expected


@pytest.mark.parametrize("version", [1, 2])
def test_news_response_converts_only_legacy_timestamp_fields(
    remote_client: tuple[FlaskClient, RemoteAccess],
    monkeypatch: pytest.MonkeyPatch,
    version: int,
) -> None:
    client, _ = remote_client
    items = [
        {
            "hash": "one",
            "collected": "2026-07-15T10:00:00Z",
            "published": "2026-07-15T11:30:00Z",
            "attributes": [{"value": "2026-07-15T10:00:00Z"}],
        },
        {"hash": "two", "collected": "2026-07-15T10:00:00Z", "published": "Source date unknown"},
        {"hash": "three", "collected": "2026-07-15T10:00:00Z", "published": "2026-07-15"},
    ]
    original = deepcopy(items)
    monkeypatch.setattr(remote_api.news_item.NewsItemData, "get_for_sync", classmethod(lambda *_args: (items, STAMP)))
    response = client.get(f"/api/v{version}/remote/sync-news-items", headers=AUTHORIZATION)
    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {"last_sync_time", "news_items"}
    assert data["last_sync_time"] == ("2026-07-15 12:00:00.000000" if version == 1 else "2026-07-15T10:00:00Z")
    if version == 1:
        assert data["news_items"][0]["collected"] == "15.07.2026 - 12:00"
        assert data["news_items"][0]["published"] == "15.07.2026 - 13:30"
    else:
        assert data["news_items"] == original
    assert data["news_items"][1]["published"] == "Source date unknown"
    assert data["news_items"][2]["published"] == "2026-07-15"
    assert data["news_items"][0]["attributes"] == original[0]["attributes"]
    assert items == original


@pytest.mark.parametrize("version", [1, 2])
def test_report_response_preserves_the_real_legacy_report_shape(
    remote_client: tuple[FlaskClient, RemoteAccess],
    monkeypatch: pytest.MonkeyPatch,
    version: int,
) -> None:
    client, _ = remote_client
    reports = [
        {"uuid": "report-id", "title": "Report", "title_prefix": "", "state_id": 1, "attributes": [{"title": "Time", "value": "text"}]},
    ]
    monkeypatch.setattr(remote_api.report_item.ReportItem, "get_for_sync", classmethod(lambda *_args: (reports, STAMP)))
    response = client.get(f"/api/v{version}/remote/sync-report-items", headers=AUTHORIZATION)
    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {"last_sync_time", "report_items"}
    assert data["last_sync_time"] == ("2026-07-15 12:00:00.000000" if version == 1 else "2026-07-15T10:00:00Z")
    assert data["report_items"] == reports


@pytest.mark.parametrize(
    ("path", "field"),
    [("sync-news-items", "last_synced_news_items"), ("sync-report-items", "last_synced_report_items")],
)
@pytest.mark.parametrize(
    ("version", "cursor"),
    [
        (1, "2026-07-15 12:00:00.000000"),
        (1, "2026-07-15T12:00:00+02:00"),
        (1, "2026-07-15T07:00:00-03:00"),
        (2, "2026-07-15T10:00:00Z"),
        (2, "2026-07-15T12:00:00+02:00"),
    ],
)
def test_acknowledgment_parses_legacy_wall_clocks_and_explicit_utc(
    remote_client: tuple[FlaskClient, RemoteAccess],
    path: str,
    field: str,
    version: int,
    cursor: str,
) -> None:
    client, node = remote_client
    setattr(node, field, datetime(2020, 1, 1, tzinfo=UTC))
    response = client.put(f"/api/v{version}/remote/{path}", headers=AUTHORIZATION, json={"last_sync_time": cursor})
    assert response.status_code == 200
    assert getattr(node, field) == STAMP
    assert getattr(node, field).tzinfo is UTC


@pytest.mark.parametrize("path", ["sync-news-items", "sync-report-items"])
@pytest.mark.parametrize("cursor", ["2026-07-15T10:00:00", "2026-07-15 10:00:00.000000", "15.07.2026 - 10:00"])
def test_v2_rejects_timezone_free_cursors(
    remote_client: tuple[FlaskClient, RemoteAccess],
    path: str,
    cursor: str,
) -> None:
    client, _ = remote_client
    response = client.put(f"/api/v2/remote/{path}", headers=AUTHORIZATION, json={"last_sync_time": cursor})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid request"


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("path", ["sync-news-items", "sync-report-items"])
@pytest.mark.parametrize("payload", [{}, {"last_sync_time": None}, {"last_sync_time": 123}, {"last_sync_time": "invalid"}, []])
def test_invalid_cursor_payloads_return_validation_errors(
    remote_client: tuple[FlaskClient, RemoteAccess],
    version: int,
    path: str,
    payload: dict | list,
) -> None:
    client, _ = remote_client
    response = client.put(f"/api/v{version}/remote/{path}", headers=AUTHORIZATION, json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid request"


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("path", ["connect", "disconnect", "sync-news-items", "sync-report-items"])
def test_both_versions_require_the_original_remote_api_key_authentication(
    remote_client: tuple[FlaskClient, RemoteAccess],
    version: int,
    path: str,
) -> None:
    client, _ = remote_client
    assert client.get(f"/api/v{version}/remote/{path}").status_code == 401
    assert client.get(f"/api/v{version}/remote/{path}", headers={"Authorization": "ApiKey incorrect"}).status_code == 401


@pytest.mark.parametrize("version", [1, 2])
def test_disabled_connect_and_disconnect_behavior_is_unchanged(remote_client: tuple[FlaskClient, RemoteAccess], version: int) -> None:
    client, node = remote_client
    node.enabled = False
    response = client.get(f"/api/v{version}/remote/connect", headers=AUTHORIZATION)
    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}
    node.connected = True
    response = client.get(f"/api/v{version}/remote/disconnect", headers=AUTHORIZATION)
    assert response.status_code == 200
    assert response.get_json() == {}
    assert node.connected is False


@pytest.mark.parametrize(("version", "expected"), [(1, "2026-07-15 06:00:00.000000"), (2, "2026-07-15T10:00:00Z")])
def test_legacy_peer_timezone_is_selected_per_remote_access(
    remote_client: tuple[FlaskClient, RemoteAccess],
    version: int,
    expected: str,
) -> None:
    client, node = remote_client
    node.legacy_timezone = "America/New_York"
    response = client.get(f"/api/v{version}/remote/connect", headers=AUTHORIZATION)
    assert response.status_code == 200
    assert response.get_json()["last_synced_news_items"] == expected
