"""Legacy peer configuration and detached SSE connection state remain consistent."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from marshmallow import ValidationError
from model import remote as remote_model
from model.remote import RemoteNode
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def _node() -> RemoteNode:
    return RemoteNode(
        id=None,
        name="Peer",
        description="",
        enabled=True,
        remote_url="https://peer.test",
        events_url="https://peer.test/sse",
        api_key="key",
        sync_news_items=True,
        sync_report_items=True,
        osint_source_group_id=None,
        legacy_timezone="Europe/Bratislava",
    )


def test_disconnected_detached_node_does_not_overwrite_current_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    RemoteNode.__table__.create(engine)
    with Session(engine) as setup:
        node = _node()
        node.event_id = "connected"
        setup.add(node)
        setup.commit()
        node_id = node.id
        setup.expunge(node)
    with Session(engine) as current:
        persisted = current.get(RemoteNode, node_id)
        assert persisted is not None
        persisted.legacy_timezone = "America/New_York"
        current.commit()
        monkeypatch.setattr(remote_model, "db", SimpleNamespace(session=current))
        node.disconnect()
        assert current.execute(select(RemoteNode.event_id).where(RemoteNode.id == node_id)).scalar_one() is None
        current.expire_all()
        refreshed = current.get(RemoteNode, node_id)
        assert refreshed is not None
        assert refreshed.legacy_timezone == "America/New_York"


def test_v1_node_connection_uses_configured_provider_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    node = _node()
    monkeypatch.setattr(remote_model, "db", SimpleNamespace(session=SimpleNamespace(commit=lambda: None)))
    node.connect(
        {
            "event_id": "peer-event",
            "last_synced_news_items": "2026-11-03 11:00:00.000000",
            "last_synced_report_items": "2026-07-03 12:00:00.000000",
        },
        api_version=1,
    )
    assert node.last_synced_news_items == datetime(2026, 11, 3, 10, tzinfo=UTC)
    assert node.last_synced_report_items == datetime(2026, 7, 3, 10, tzinfo=UTC)


def test_v2_bad_cursor_does_not_partially_change_connection_state(monkeypatch: pytest.MonkeyPatch) -> None:
    node = _node()
    node.event_id = "old-event"
    node.last_synced_news_items = datetime(2026, 1, 1, tzinfo=UTC)
    session = SimpleNamespace(commit=lambda: pytest.fail("invalid cursor was committed"))
    monkeypatch.setattr(remote_model, "db", SimpleNamespace(session=session))
    with pytest.raises(ValidationError):
        node.connect(
            {"event_id": "new-event", "last_synced_news_items": "2026-11-03T10:00:00Z", "last_synced_report_items": "2026-11-03 10:00:00"},
            api_version=2,
        )
    assert node.event_id == "old-event"
    assert node.last_synced_news_items == datetime(2026, 1, 1, tzinfo=UTC)
