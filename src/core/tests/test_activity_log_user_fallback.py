"""The activity log must survive a user that could not be resolved.

Error paths call ``store_data_error_activity(get_user_from_jwt(), ...)``. That lookup
returns None whenever it fails - most often because the endpoint's own failed flush left
the session unusable, which is precisely when the error is being reported. Dereferencing
the user there raised AttributeError inside the error handler, so the endpoint's intended
400 became an opaque 500 and the real cause never reached the client.
"""

from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def log_manager() -> Iterator[types.ModuleType]:
    """Import managers.log_manager with its database and syslog dependencies stubbed out."""
    saved = {name: sys.modules.get(name) for name in ("managers.db_manager", "managers.log_manager")}

    db_module = types.ModuleType("managers.db_manager")
    db_module.db = types.SimpleNamespace(session=types.SimpleNamespace(rollback=lambda: None))
    sys.modules["managers.db_manager"] = db_module
    sys.modules.pop("managers.log_manager", None)

    import managers.log_manager as module  # noqa: PLC0415 - after the stubs are in place

    module.sys_logger = None
    yield module

    for name, previous in saved.items():
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


def test_identify_tolerates_a_missing_user(log_manager: types.ModuleType) -> None:
    """An unresolved user yields empty identity fields rather than raising."""
    assert log_manager._identify(None) == (None, None)


def test_identify_returns_the_user_identity(log_manager: types.ModuleType) -> None:
    """A resolved user is reported by id and name."""
    user = types.SimpleNamespace(id=7, name="Arthur Dent")

    assert log_manager._identify(user) == (7, "Arthur Dent")


@pytest.mark.parametrize(
    ("function", "extra_args"),
    [
        ("store_data_error_activity", ()),
        ("store_access_error_activity", ()),
        ("store_user_auth_error_activity", ()),
        ("store_user_activity", ("SOME_TYPE",)),
    ],
)
def test_activity_helpers_record_an_unresolved_user(
    log_manager: types.ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    function: str,
    extra_args: tuple,
) -> None:
    """Every helper taking a user still writes its record when the user is None."""
    recorded: list[tuple] = []
    monkeypatch.setattr(log_manager, "store_record", lambda *args: recorded.append(args))
    monkeypatch.setattr(log_manager, "resolve_ip_address", lambda: "127.0.0.1")
    monkeypatch.setattr(log_manager, "resolve_method", lambda: "DELETE")
    monkeypatch.setattr(log_manager, "resolve_resource", lambda: "/api/v1/config/attributes/1")
    # Reads the live Flask request, which no test has.
    monkeypatch.setattr(log_manager, "generate_escaped_data", str)

    # store_user_activity takes (user, activity_type, activity_detail); the rest take
    # (user, activity_detail).
    getattr(log_manager, function)(None, *extra_args, "boom")

    assert len(recorded) == 1
    assert None in recorded[0]
