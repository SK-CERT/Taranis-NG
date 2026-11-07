"""Rules for creating and changing API keys: expiry policy, allowlists, scopes and names.

No database: the session is a recorder, and permissions and users are transient model objects.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from model import apikey as apikey_model
from model.apikey import ApiKey, check_expiry, hash_key, parse_expiry
from model.permission import Permission
from model.user import User
from shared.common import TZ

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=TZ)
OPEN = {"require_expiry": False, "max_days": None, "require_allowlist": False, "allowed_ips": None}


def _permission(permission_id: str) -> Permission:
    permission = Permission()
    permission.id = permission_id
    permission.name = permission_id.title()
    permission.description = ""
    return permission


PERMISSIONS = {permission_id: _permission(permission_id) for permission_id in ("ASSESS_ACCESS", "ANALYZE_ACCESS", "CONFIG_ACCESS")}


def _owner(*permission_ids: str) -> User:
    owner = User(-1, "soar", "SOAR integration")
    owner.id = 3
    owner.permissions = [PERMISSIONS[permission_id] for permission_id in permission_ids]
    return owner


@pytest.fixture
def session(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Record what is added and committed; names are free unless listed in ``taken``."""
    recorded = SimpleNamespace(added=[], commits=0, taken={})

    def commit() -> None:
        recorded.commits += 1

    monkeypatch.setattr(apikey_model, "db", SimpleNamespace(session=SimpleNamespace(add=recorded.added.append, commit=commit)))
    monkeypatch.setattr(ApiKey, "find_by_name", classmethod(lambda _cls, name, user_id=None: recorded.taken.get((user_id, name))))
    monkeypatch.setattr(apikey_model.Permission, "find", classmethod(lambda _cls, permission_id: PERMISSIONS.get(permission_id)))
    return recorded


def _create(data: dict, policy: dict | None = None, owner: User | None = None) -> tuple[ApiKey, str]:
    return ApiKey.create(owner or _owner("ASSESS_ACCESS", "ANALYZE_ACCESS"), data, created_by="admin", policy=policy or OPEN)


def test_a_new_key_keeps_only_its_hash_and_prefix(session: SimpleNamespace) -> None:
    record, plaintext = _create({"name": "  SOAR sync ", "description": "Pulls news items"})

    assert session.added == [record]
    assert session.commits == 1
    assert record.name == "SOAR sync"
    assert record.key_hash == hash_key(plaintext)
    assert record.key_prefix == plaintext[:12]
    assert record.created_by == "admin"
    assert record.user_id == 3
    assert record.enabled is True
    assert record.restricted is False
    assert record.permissions == []
    assert plaintext not in repr(record.to_dict())
    assert record.to_dict()["user"] == {"id": 3, "username": "soar", "name": "SOAR integration"}


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"name": "  "}, "needs a name"),
        ({"name": "x" * 101}, "at most 100 characters"),
        ({"name": "ok", "description": "x" * 501}, "at most 500 characters"),
        ({"name": "ok", "expires_at": "next week"}, "not a valid expiry date"),
        ({"name": "ok", "expires_at": "2020-01-01T00:00:00+00:00"}, "must be in the future"),
        ({"name": "ok", "allowed_ips": "example.com"}, "is not an IP address"),
        ({"name": "ok", "restricted": True, "permissions": ["CONFIG_ACCESS"]}, "its owner does not have: CONFIG_ACCESS"),
    ],
)
def test_a_key_that_breaks_a_rule_is_refused_and_nothing_is_stored(session: SimpleNamespace, data: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _create(data)
    assert session.added == []
    assert session.commits == 0


def test_names_are_unique_per_owner(session: SimpleNamespace) -> None:
    session.taken[(3, "SOAR sync")] = SimpleNamespace(id=1)
    with pytest.raises(ValueError, match="already has an API key named 'SOAR sync'"):
        _create({"name": "SOAR sync"})
    session.taken = {(4, "SOAR sync"): SimpleNamespace(id=1)}  # another user's key of that name
    assert _create({"name": "SOAR sync"})[0].name == "SOAR sync"


def test_a_restricted_key_keeps_the_picked_permissions(session: SimpleNamespace) -> None:  # noqa: ARG001
    record, _plaintext = _create({"name": "ok", "restricted": True, "permissions": [{"id": "ANALYZE_ACCESS"}, "ANALYZE_ACCESS"]})
    assert record.restricted is True
    assert [permission.id for permission in record.permissions] == ["ANALYZE_ACCESS"]
    assert [permission["id"] for permission in record.to_dict()["permissions"]] == ["ANALYZE_ACCESS"]


def test_an_unrestricted_key_ignores_picked_permissions(session: SimpleNamespace) -> None:  # noqa: ARG001
    record, _plaintext = _create({"name": "ok", "restricted": False, "permissions": ["CONFIG_ACCESS"]})
    assert record.permissions == []


@pytest.mark.parametrize(
    ("policy", "expires_at", "message"),
    [
        ({"require_expiry": True}, None, "must have an expiry date"),
        ({"max_days": 90}, None, "must have an expiry date"),  # a cap implies an expiry
        ({"max_days": 90}, NOW + timedelta(days=92), "at most 90 days"),
        ({}, NOW - timedelta(seconds=1), "must be in the future"),
    ],
)
def test_the_expiry_policy(policy: dict, expires_at: datetime | None, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        check_expiry(expires_at, {**OPEN, **policy}, now=NOW)


@pytest.mark.parametrize(
    ("policy", "expires_at"),
    [
        ({}, None),
        ({"require_expiry": True}, NOW + timedelta(days=3650)),
        ({"max_days": 90}, NOW + timedelta(days=90)),
        ({"max_days": 90}, NOW + timedelta(days=90, hours=23)),  # a date picked as a day runs to its end
    ],
)
def test_expiries_the_policy_allows(policy: dict, expires_at: datetime | None) -> None:
    check_expiry(expires_at, {**OPEN, **policy}, now=NOW)


def test_expiries_are_read_as_iso_with_naive_ones_in_the_server_zone() -> None:
    assert parse_expiry("2027-12-31 16:55") == datetime(2027, 12, 31, 16, 55, tzinfo=TZ)
    assert parse_expiry("2027-12-31T16:55:00Z").utcoffset() == timedelta(0)
    assert parse_expiry("") is None
    assert parse_expiry(None) is None


def test_an_allowlist_can_be_required(session: SimpleNamespace) -> None:  # noqa: ARG001
    policy = {**OPEN, "require_allowlist": True}
    with pytest.raises(ValueError, match="must have an IP allowlist"):
        _create({"name": "ok"}, policy)
    record, _plaintext = _create({"name": "ok", "allowed_ips": "185.10.20.0/24\n8.8.8.8"}, policy)
    assert record.allowed_ips == "185.10.20.0/24\n8.8.8.8/32"
    assert record.to_dict()["allowed_ips"] == ["185.10.20.0/24", "8.8.8.8/32"]
    with pytest.raises(ValueError, match="is not a public IP address or range"):
        _create({"name": "private", "allowed_ips": "10.0.0.0/8"}, policy)


def _existing(session: SimpleNamespace, **fields: object) -> ApiKey:
    record, _plaintext = _create({"name": "SOAR sync", **fields})
    session.commits = 0
    return record


def test_an_update_changes_only_what_it_names(session: SimpleNamespace) -> None:
    record = _existing(session, description="Pulls news items", allowed_ips="185.10.20.0/24")
    record.apply_update({"enabled": False}, policy=OPEN)

    assert record.enabled is False
    assert record.description == "Pulls news items"
    assert record.allowed_ips == "185.10.20.0/24"
    assert session.commits == 1


def test_an_update_that_breaks_a_rule_changes_nothing(session: SimpleNamespace) -> None:
    record = _existing(session)
    with pytest.raises(ValueError, match="is not an IP address"):
        record.apply_update({"name": "renamed", "enabled": False, "allowed_ips": "nope"}, policy=OPEN)
    assert (record.name, record.enabled, record.allowed_ips) == ("SOAR sync", True, None)
    assert session.commits == 0


def test_an_update_cannot_clear_a_required_allowlist(session: SimpleNamespace) -> None:
    record = _existing(session, allowed_ips="185.10.20.0/24")
    with pytest.raises(ValueError, match="must have an IP allowlist"):
        record.apply_update({"allowed_ips": ""}, policy={**OPEN, "require_allowlist": True})
    record.apply_update({"allowed_ips": ""}, policy=OPEN)
    assert record.allowed_ips is None


def test_an_update_keeps_a_permission_the_owner_lost_but_cannot_add_one(session: SimpleNamespace) -> None:
    record = _existing(session, restricted=True, permissions=["ASSESS_ACCESS", "ANALYZE_ACCESS"])
    record.user.permissions = [PERMISSIONS["ANALYZE_ACCESS"]]  # the owner lost ASSESS_ACCESS

    record.apply_update({"name": "renamed", "restricted": True, "permissions": ["ASSESS_ACCESS"]}, policy=OPEN)
    assert [permission.id for permission in record.permissions] == ["ASSESS_ACCESS"]

    with pytest.raises(ValueError, match="does not have: CONFIG_ACCESS"):
        record.apply_update({"permissions": ["ASSESS_ACCESS", "CONFIG_ACCESS"]}, policy=OPEN)

    record.apply_update({"restricted": False}, policy=OPEN)
    assert (record.restricted, record.permissions) == (False, [])
