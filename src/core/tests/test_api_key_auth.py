"""User API keys authenticate ``auth_required`` endpoints, within their limits.

A key is looked up by its hash and must be enabled and unexpired, its owner active, and the
trusted client address in the site-wide and the key's own allowlist. It acts with its owner's
permissions, or only the picked ones the owner still has. Endpoints that manage keys refuse
keys altogether. No database: the lookup and the policy are stubbed, the checks are the model's.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from http import HTTPStatus
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify
from managers import auth_manager
from model import apikey as apikey_model
from model.apikey import ApiKey, hash_key, new_secret
from shared.common import TZ
from werkzeug.middleware.proxy_fix import ProxyFix

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=TZ)
PLAINTEXT = "tnk_test-key-0123456789abcdefghijklmnopqrstuvwxyzAB"


class FakeKey:
    """An API key row with the model's own checks and a recorded ``touch``."""

    refusal = ApiKey.refusal
    is_expired = ApiKey.is_expired
    effective_permissions = ApiKey.effective_permissions

    def __init__(self, owner: SimpleNamespace, **fields: object) -> None:
        """Build an enabled, unrestricted, never-expiring key of ``owner``; ``fields`` override."""
        self.id = 7
        self.name = "SOAR sync"
        self.user = owner
        self.user_id = owner.id
        self.enabled = True
        self.expires_at = None
        self.restricted = False
        self.permissions: list = []
        self.allowed_ips = None
        self.touched: list[str | None] = []
        self.__dict__.update(fields)

    def touch(self, ip: str | None) -> None:
        """Record the use instead of writing it."""
        self.touched.append(ip)


def _owner(*permission_ids: str, status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        id=3,
        username="soar",
        status=status,
        permissions=[SimpleNamespace(id=permission_id) for permission_id in permission_ids],
        roles=[],
    )


@pytest.fixture
def log(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Record what the auth manager logs, instead of writing it."""
    entries: list[tuple[str, str]] = []
    monkeypatch.setattr(auth_manager.log_manager, "store_auth_error_activity", lambda detail, *_a, **_k: entries.append(("error", detail)))
    monkeypatch.setattr(
        auth_manager.log_manager,
        "store_auth_warning_activity",
        lambda detail, *_a, **_k: entries.append(("warning", detail)),
    )
    monkeypatch.setattr(
        auth_manager.log_manager,
        "store_user_auth_error_activity",
        lambda _u, detail, *_a, **_k: entries.append(("error", detail)),
    )
    monkeypatch.setattr(
        auth_manager.log_manager,
        "store_user_activity",
        lambda _u, kind, detail, **_k: entries.append(("activity", f"{kind} {detail}")),
    )
    return entries


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> dict:
    """The site-wide API key policy the checks read."""
    policy = {"require_expiry": False, "max_days": None, "require_allowlist": False, "allowed_ips": None}
    monkeypatch.setattr(auth_manager.SecuritySettings, "get_api_key_policy", classmethod(lambda _cls: policy))
    return policy


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> dict[str, FakeKey]:
    """Presented key -> row; the lookup compares hashes like the real one."""
    rows: dict[str, FakeKey] = {}

    def find_by_key(_cls: type, plain: str | None) -> FakeKey | None:
        if not plain:
            return None
        return next((row for key, row in rows.items() if hash_key(key) == hash_key(plain)), None)

    monkeypatch.setattr(auth_manager.ApiKey, "find_by_key", classmethod(find_by_key))
    return rows


@pytest.fixture
def jwt_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(auth_manager, "get_user_from_jwt_token", lambda: calls.append("jwt"))
    return calls


@pytest.fixture
def app(log: list, site: dict, jwt_calls: list) -> Flask:  # noqa: ARG001 - the fixtures stub what the routes use
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

    @app.get("/assess")
    @auth_manager.auth_required("ASSESS_ACCESS")
    def assess():  # noqa: ANN202
        return jsonify(user=auth_manager.get_user_from_jwt().username)

    @app.get("/keys")
    @auth_manager.auth_required("MY_API_KEYS_MANAGE", allow_api_key=False)
    def manage_keys():  # noqa: ANN202
        return jsonify(ok=True)

    return app


def _get(app: Flask, path: str = "/assess", authorization: str | None = f"ApiKey {PLAINTEXT}", ip: str = "198.51.100.7") -> tuple[int, dict]:
    headers = {"Authorization": authorization} if authorization is not None else {}
    response = app.test_client().get(path, headers=headers, environ_base={"REMOTE_ADDR": ip})
    return response.status_code, response.get_json()


def test_a_key_acts_as_its_owner_and_its_use_is_recorded(app: Flask, keys: dict, log: list) -> None:
    keys[PLAINTEXT] = row = FakeKey(_owner("ASSESS_ACCESS"))

    assert _get(app) == (HTTPStatus.OK, {"user": "soar"})
    assert row.touched == ["198.51.100.7"]
    assert ("activity", "{'ASSESS_ACCESS'} API key: SOAR sync") in log


def test_a_key_request_is_never_tried_as_a_jwt(app: Flask, keys: dict, log: list, jwt_calls: list) -> None:
    """Trying it logged a bogus "Missing JWT" auth error for every call made with a key."""
    keys[PLAINTEXT] = FakeKey(_owner("ASSESS_ACCESS"))

    assert _get(app)[0] == HTTPStatus.OK
    assert _get(app, authorization="ApiKey unknown")[0] == HTTPStatus.UNAUTHORIZED
    assert jwt_calls == []
    assert not any("JWT" in detail for _level, detail in log)
    assert ("error", "Unauthorized API call access (invalid API key)") in log


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        ({"enabled": False}, "the key is disabled"),
        ({"expires_at": datetime.now(TZ) - timedelta(minutes=1)}, "the key has expired"),
        ({"allowed_ips": "10.0.0.0/8"}, "client IP 198.51.100.7 is not in the key's allowlist"),
    ],
)
def test_a_key_that_cannot_be_used_is_refused_with_the_reason_logged(app: Flask, keys: dict, log: list, fields: dict, reason: str) -> None:
    keys[PLAINTEXT] = row = FakeKey(_owner("ASSESS_ACCESS"), **fields)

    assert _get(app)[0] == HTTPStatus.UNAUTHORIZED
    assert log == [("warning", f"API key 'SOAR sync' of user id 3 refused: {reason}")]  # the one entry
    assert row.touched == []


def test_an_unexpired_key_still_works(app: Flask, keys: dict) -> None:
    keys[PLAINTEXT] = FakeKey(_owner("ASSESS_ACCESS"), expires_at=datetime.now(TZ) + timedelta(days=1))
    assert _get(app)[0] == HTTPStatus.OK


def test_a_key_of_an_account_that_is_not_active_is_refused(app: Flask, keys: dict, log: list) -> None:
    keys[PLAINTEXT] = FakeKey(_owner("ASSESS_ACCESS", status="disabled"))

    assert _get(app)[0] == HTTPStatus.UNAUTHORIZED
    assert ("warning", "API key access of non-active user blocked: soar") in log


def test_the_site_wide_and_the_keys_own_allowlist_must_both_admit_the_caller(app: Flask, keys: dict, site: dict) -> None:
    keys[PLAINTEXT] = FakeKey(_owner("ASSESS_ACCESS"), allowed_ips="198.51.100.0/24")
    site["allowed_ips"] = "10.0.0.0/8"
    assert _get(app)[0] == HTTPStatus.UNAUTHORIZED
    assert _get(app, ip="10.1.1.1")[0] == HTTPStatus.UNAUTHORIZED

    site["allowed_ips"] = "10.0.0.0/8\n198.51.100.0/25"
    assert _get(app)[0] == HTTPStatus.OK


def test_a_spoofed_forwarded_for_header_does_not_get_past_an_allowlist(app: Flask, keys: dict) -> None:
    """The proxy appends the real address; whatever the client put in front is ignored."""
    keys[PLAINTEXT] = FakeKey(_owner("ASSESS_ACCESS"), allowed_ips="10.0.0.0/8")
    response = app.test_client().get(
        "/assess",
        headers={"Authorization": f"ApiKey {PLAINTEXT}", "X-Forwarded-For": "10.0.0.5, 198.51.100.7"},
        environ_base={"REMOTE_ADDR": "172.18.0.2"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_a_restricted_key_has_only_the_picked_permissions_its_owner_still_has(app: Flask, keys: dict) -> None:
    owner = _owner("ASSESS_ACCESS", "ANALYZE_ACCESS")
    keys[PLAINTEXT] = row = FakeKey(owner, restricted=True, permissions=[SimpleNamespace(id="ANALYZE_ACCESS")])
    assert _get(app)[0] == HTTPStatus.UNAUTHORIZED

    row.permissions = [SimpleNamespace(id="ASSESS_ACCESS")]
    assert _get(app)[0] == HTTPStatus.OK

    owner.permissions = [SimpleNamespace(id="ANALYZE_ACCESS")]  # the owner lost it
    assert _get(app)[0] == HTTPStatus.UNAUTHORIZED


def test_a_restricted_key_with_nothing_picked_can_do_nothing() -> None:
    """Not "everything": deleting a key's last permission must never widen it."""
    row = FakeKey(_owner("ASSESS_ACCESS"), restricted=True, permissions=[])
    assert row.effective_permissions({"ASSESS_ACCESS", "CONFIG_ACCESS"}) == set()
    assert FakeKey(_owner()).effective_permissions({"ASSESS_ACCESS"}) == {"ASSESS_ACCESS"}


def test_endpoints_that_manage_keys_refuse_keys(app: Flask, keys: dict, log: list) -> None:
    keys[PLAINTEXT] = row = FakeKey(_owner("MY_API_KEYS_MANAGE"))

    assert _get(app, "/keys")[0] == HTTPStatus.UNAUTHORIZED
    assert row.touched == []
    assert ("warning", "API key refused: this endpoint needs a signed-in user") in log


@pytest.mark.parametrize(
    "authorization",
    [
        f"apikey {PLAINTEXT}",  # the scheme is case-sensitive
        f"ApiKey{PLAINTEXT}",
        "ApiKey ",
        f"Bearer {PLAINTEXT}",
        PLAINTEXT,
    ],
)
def test_only_an_exact_apikey_header_presents_a_key(app: Flask, keys: dict, authorization: str) -> None:
    keys[PLAINTEXT] = FakeKey(_owner("ASSESS_ACCESS"))
    assert _get(app, authorization=authorization)[0] == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize(
    ("header", "key"),
    [
        (f"ApiKey {PLAINTEXT}", PLAINTEXT),
        (f"ApiKey  {PLAINTEXT} ", PLAINTEXT),
        (f"apikey {PLAINTEXT}", ""),
        ("ApiKeyabc", ""),
        ("Bearer abc", ""),
        ("", ""),
    ],
)
def test_the_key_is_read_from_the_header_strictly(header: str, key: str) -> None:
    app = Flask(__name__)
    with app.test_request_context("/", headers={"Authorization": header}):
        assert auth_manager.get_api_key() == key


def test_new_keys_are_random_prefixed_and_only_their_hash_is_kept() -> None:
    first, second = new_secret(), new_secret()
    assert first != second
    assert first.startswith("tnk_")
    assert len(first) == len("tnk_") + 43
    assert len(hash_key(first)) == 64
    assert hash_key(first) == hash_key(first)
    assert first not in hash_key(first)


def test_a_legacy_key_is_found_by_the_hash_the_migration_stored() -> None:
    """The migration hashes keys with Postgres' sha256 over the UTF-8 bytes: the same digest."""
    assert hash_key("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class _Session:
    def __init__(self) -> None:
        self.executed = 0
        self.committed = 0

    def execute(self, _statement: object) -> None:
        self.executed += 1

    def commit(self) -> None:
        self.committed += 1


def test_a_use_is_written_at_most_once_a_minute_unless_the_address_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _Session()
    monkeypatch.setattr(apikey_model, "db", SimpleNamespace(session=session))
    row = SimpleNamespace(id=7, last_used_at=NOW - timedelta(seconds=30), last_used_ip="198.51.100.7")

    ApiKey.touch(row, "198.51.100.7", now=NOW)
    assert session.executed == 0

    ApiKey.touch(row, "198.51.100.8", now=NOW)
    assert session.executed == 1

    row.last_used_ip = "198.51.100.8"
    row.last_used_at = NOW - timedelta(seconds=61)
    ApiKey.touch(row, "198.51.100.8", now=NOW)
    assert (session.executed, session.committed) == (2, 2)


def test_a_failed_use_write_never_fails_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    rolled_back: list[bool] = []

    def fail(_statement: object) -> None:
        raise RuntimeError

    session = SimpleNamespace(execute=fail, commit=lambda: None, rollback=lambda: rolled_back.append(True))
    monkeypatch.setattr(apikey_model, "db", SimpleNamespace(session=session))
    ApiKey.touch(SimpleNamespace(id=7, last_used_at=None, last_used_ip=None), "198.51.100.7", now=NOW)
    assert rolled_back == [True]
