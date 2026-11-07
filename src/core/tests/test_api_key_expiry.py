"""Owners are told once when an API key expires.

The scheduler's job marks every key that has expired since its last run and tells the owners of
the ones that were in use: enabled, of an active account. No database: the lookup, the session
and the notifications are stubbed.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from managers import api_key_manager
from shared.common import TZ

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=TZ)
ALICE = SimpleNamespace(id=1, username="alice", status="active")
GONE = SimpleNamespace(id=2, username="gone", status="disabled")


def _key(key_id: int, owner: SimpleNamespace, *, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=key_id,
        name=f"key {key_id}",
        key_prefix=f"tnk_{key_id:08d}",
        user=owner,
        user_id=owner.id,
        enabled=enabled,
        expires_at=NOW - timedelta(minutes=3),
        expiry_notified_at=None,
    )


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    state = SimpleNamespace(keys=[], told=[], commits=0, asked_at=[])

    def expired_unreported(_cls: type, now: datetime) -> list:
        state.asked_at.append(now)
        return [key for key in state.keys if key.expiry_notified_at is None and key.expires_at <= now]

    def commit() -> None:
        state.commits += 1

    monkeypatch.setattr(api_key_manager.ApiKey, "expired_unreported", classmethod(expired_unreported))
    monkeypatch.setattr(api_key_manager.db, "session", SimpleNamespace(commit=commit, rollback=lambda: None))
    monkeypatch.setattr(
        api_key_manager.notification_manager,
        "notify_user",
        lambda user, event, *, actor=None, system=False, **details: state.told.append((user, event, actor, system, details)),
    )
    return state


def test_the_owner_of_a_key_in_use_is_told_once(world: SimpleNamespace) -> None:
    world.keys = [_key(1, ALICE)]

    assert api_key_manager.notify_expired(NOW) == 1
    assert api_key_manager.notify_expired(NOW + timedelta(minutes=5)) == 0

    [(user, event, actor, system, details)] = world.told
    assert (user, event, actor, system) == (ALICE, "api_key_expired", None, True)
    assert details["api_key_name"] == "key 1"
    assert details["api_key_prefix"] == "tnk_00000001…"
    assert details["expired_at"].startswith("2026-11-07 11:57")
    assert "expires" not in details
    assert world.keys[0].expiry_notified_at == NOW


def test_paused_keys_and_keys_of_inactive_accounts_are_marked_without_a_message(world: SimpleNamespace) -> None:
    world.keys = [_key(1, ALICE, enabled=False), _key(2, GONE), _key(3, ALICE)]

    assert api_key_manager.notify_expired(NOW) == 1
    assert [details["api_key_name"] for _user, _event, _actor, _system, details in world.told] == ["key 3"]
    assert all(key.expiry_notified_at == NOW for key in world.keys)


def test_keys_are_marked_before_anyone_is_told(world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing message must not leave the key unmarked, or every run would repeat it."""
    world.keys = [_key(1, ALICE)]

    def fail(*_args: object, **_kwargs: object) -> None:
        assert world.commits == 1
        raise RuntimeError

    monkeypatch.setattr(api_key_manager.notification_manager, "notify_user", fail)
    with pytest.raises(RuntimeError):
        api_key_manager.notify_expired(NOW)
    assert world.keys[0].expiry_notified_at == NOW


def test_nothing_is_written_when_nothing_expired(world: SimpleNamespace) -> None:
    assert api_key_manager.notify_expired(NOW) == 0
    assert world.commits == 0


def test_the_scheduler_looks_every_few_minutes() -> None:
    scheduled = []
    manager = SimpleNamespace(schedule_job_minutes=lambda *args: scheduled.append(args))

    api_key_manager.schedule(manager, "app")

    assert scheduled == [(api_key_manager.EXPIRY_CHECK_MINUTES, api_key_manager.expiry_job, "API key expiry notices", "app")]
