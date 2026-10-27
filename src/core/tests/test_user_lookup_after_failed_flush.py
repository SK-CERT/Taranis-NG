"""The user lookup for an error log works after the endpoint's own failed flush.

Error paths call ``store_data_error_activity(get_user_from_jwt(), ...)``, and Python runs that
lookup before anything has rolled back. On a session a failed flush left unusable (a duplicate
name, say), the lookups failed and logged bogus "Authentication generation could not be
verified" and "Missing JWT" errors next to the real one. The lookup rolls such a session back
first, and leaves a usable one - possibly holding the caller's pending changes - alone.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from managers import auth_manager

USER = SimpleNamespace(id=1, name="Arthur Dent")


class _Session:
    """The bits of a SQLAlchemy session the lookup looks at, recording what happens."""

    def __init__(self, calls: list[str], *, active: bool) -> None:
        self.is_active = active
        self._calls = calls

    def rollback(self) -> None:
        self._calls.append("rollback")
        self.is_active = True


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(auth_manager, "get_user_from_api_key", lambda: calls.append("api key"))
    monkeypatch.setattr(auth_manager, "get_user_from_jwt_token", lambda: calls.append("jwt") or USER)
    return calls


def test_a_session_a_failed_flush_left_unusable_is_rolled_back_before_the_lookup(calls: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_manager, "db", SimpleNamespace(session=_Session(calls, active=False)))

    assert auth_manager.get_user_from_jwt() is USER
    assert calls == ["rollback", "api key", "jwt"]


def test_a_usable_session_keeps_what_it_holds(calls: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_manager, "db", SimpleNamespace(session=_Session(calls, active=True)))

    assert auth_manager.get_user_from_jwt() is USER
    assert calls == ["api key", "jwt"]
