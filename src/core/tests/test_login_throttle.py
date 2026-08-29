"""Failed-login throttling semantics (Redis faked in-process)."""

from __future__ import annotations

import pytest
from managers import login_throttle


class _FakeRedis:
    """Just enough Redis: get/set(TTL)/delete keyed by string."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int = 0) -> None:
        self.store[key] = value
        self.ttls[key] = ex

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    redis_state = _FakeRedis()
    monkeypatch.setattr(login_throttle, "redis_client", redis_state)
    return redis_state


@pytest.mark.usefixtures("fake_redis")
def test_under_threshold_attempts_are_allowed() -> None:
    for _ in range(login_throttle.FAIL_THRESHOLD - 1):
        login_throttle.register_failure("alice")
    assert login_throttle.check_lock("alice") is True


@pytest.mark.usefixtures("fake_redis")
def test_threshold_failure_locks_the_account() -> None:
    for _ in range(login_throttle.FAIL_THRESHOLD):
        login_throttle.register_failure("alice")
    assert login_throttle.check_lock("alice") is False


@pytest.mark.usefixtures("fake_redis")
def test_lockout_duration_grows_with_each_extra_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escalation must survive the wait it imposes.

    An attacker never gets to fail again *during* a lockout - the gate refuses
    them before any credential check - so the only way to reach the sixth
    failure is to wait the lockout out. A frozen clock therefore proves nothing:
    it tests a state production cannot reach. This advances time exactly the way
    an attacker would experience it.
    """
    clock = {"now": 1_000_000}
    monkeypatch.setattr(login_throttle, "_now", lambda: clock["now"])

    for _ in range(login_throttle.FAIL_THRESHOLD):
        login_throttle.register_failure("alice")
        clock["now"] += 1  # attempts take a moment each
    _, _, locked_until = login_throttle._read("alice")
    assert locked_until == clock["now"] - 1 + login_throttle.LOCKOUT_SECONDS

    # wait out the lock, then come straight back: the count must carry over
    clock["now"] = locked_until + 1
    assert login_throttle.check_lock("alice") is True
    login_throttle.register_failure("alice")

    fails, _, locked_until = login_throttle._read("alice")
    assert fails == login_throttle.FAIL_THRESHOLD + 1
    assert locked_until == clock["now"] + login_throttle.LOCKOUT_SECONDS * login_throttle.LOCKOUT_MULTIPLIER


@pytest.mark.usefixtures("fake_redis")
def test_lockout_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    # without a cap the doubling reaches months; walk far enough past the
    # threshold that the clamp has to engage
    clock = {"now": 1_000_000}
    monkeypatch.setattr(login_throttle, "_now", lambda: clock["now"])
    for _ in range(login_throttle.FAIL_THRESHOLD + 20):
        login_throttle.register_failure("alice")
        _, _, locked_until = login_throttle._read("alice")
        clock["now"] = max(clock["now"] + 1, locked_until + 1)

    assert locked_until - (clock["now"] - 1) <= login_throttle.LOCKOUT_MAX_SECONDS


def test_success_resets_the_counter(fake_redis: _FakeRedis) -> None:
    login_throttle.register_failure("alice")
    login_throttle.register_success("alice")
    assert login_throttle.check_lock("alice") is True
    assert "login_fail:alice" not in fake_redis.store


@pytest.mark.usefixtures("fake_redis")
def test_lock_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 1_000_000}
    monkeypatch.setattr(login_throttle, "_now", lambda: clock["now"])
    for _ in range(login_throttle.FAIL_THRESHOLD):
        login_throttle.register_failure("alice")
    assert login_throttle.is_locked("alice") is True

    clock["now"] += login_throttle.LOCKOUT_SECONDS + 1
    assert login_throttle.is_locked("alice") is False


@pytest.mark.usefixtures("fake_redis")
def test_failures_outside_the_window_start_a_fresh_count(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 1_000_000}
    monkeypatch.setattr(login_throttle, "_now", lambda: clock["now"])
    login_throttle.register_failure("alice")  # first failure: window starts
    clock["now"] += login_throttle.FAIL_WINDOW + 10  # the window has expired
    login_throttle.register_failure("alice")  # this is a fresh count, not #2

    fails, last_fail, _ = login_throttle._read("alice")
    assert fails == 1
    assert last_fail == clock["now"]


@pytest.mark.usefixtures("fake_redis")
def test_usernames_are_counted_separately() -> None:
    for _ in range(login_throttle.FAIL_THRESHOLD):
        login_throttle.register_failure("alice")
    assert login_throttle.check_lock("bob") is True


def test_redis_outage_never_blocks_login(fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        msg = "connection refused"
        raise ConnectionError(msg)

    monkeypatch.setattr(fake_redis, "get", broken)
    monkeypatch.setattr(fake_redis, "set", broken)
    assert login_throttle.check_lock("alice") is True  # degrade open, not closed
    login_throttle.register_failure("alice")  # must not raise
    monkeypatch.setattr(fake_redis, "delete", broken)
    login_throttle.register_success("alice")  # must not raise
