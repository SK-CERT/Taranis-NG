"""Passkeys carry the AAGUID of their authenticator, and a name and icon when the list knows it.

The AAGUID is recorded at registration, the only moment it can be read. The name and icon come
from a community list core downloads and keeps in Redis, once an administrator turns the lookup on
in the settings. That list may be unreachable, retired, or partly malformed; these tests pin that
each of those costs at most the name and icon, never the page, and that a failed refresh keeps the
last good list.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest
import requests
from managers import db_manager, passkey_authenticator_manager, webauthn_manager
from model.setting import Setting
from model.user import User
from model.webauthn_credential import WebauthnCredential
from webauthn.helpers import bytes_to_base64url

URL = "https://example.test/combined_aaguid.json"
YUBIKEY = "cb69481e-8ff7-4039-93ec-0a2729a154a8"
BITWARDEN = "d548826e-79b4-db40-a3d8-11116f7e8349"
ICON_LIGHT = "data:image/svg+xml;base64,PHN2Zy8+"
ICON_DARK = "data:image/svg+xml;base64,PHN2ZyBkYXJrLz4="
UPSTREAM = {
    YUBIKEY: {"name": "YubiKey 5 Series", "icon_light": ICON_LIGHT, "icon_dark": ICON_DARK},
    BITWARDEN: {"name": "Bitwarden", "icon_light": ICON_LIGHT, "icon_dark": ICON_LIGHT},
}


class FakeRedis:
    """Enough Redis for the list cache: strings, one hash per key, NX locks, and a broken mode."""

    def __init__(self) -> None:
        """Start empty."""
        self.store: dict[str, object] = {}
        self.broken = False

    def _check(self) -> None:
        if self.broken:
            msg = "redis is down"
            raise ConnectionError(msg)

    def get(self, key: str) -> bytes | None:
        """Read a string."""
        self._check()
        value = self.store.get(key)
        return value.encode() if isinstance(value, str) else None

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:  # noqa: ARG002
        """Store a string; with nx, only when the key is free."""
        self._check()
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def exists(self, key: str) -> int:
        """Tell whether a key is set."""
        self._check()
        return int(key in self.store)

    def delete(self, *keys: str) -> None:
        """Forget keys."""
        self._check()
        for key in keys:
            self.store.pop(key, None)

    def hset(self, key: str, mapping: dict[str, str]) -> None:
        """Add fields to a hash."""
        self._check()
        self.store.setdefault(key, {}).update(mapping)

    def hget(self, key: str, field: str) -> bytes | None:
        """Read one field of a hash."""
        self._check()
        value = self.store.get(key, {}).get(field)
        return value.encode() if value is not None else None

    def rename(self, source: str, target: str) -> None:
        """Move a key over another."""
        self._check()
        self.store[target] = self.store.pop(source)


class Settings:
    """The two global settings, as an administrator left them."""

    def __init__(self) -> None:
        """Start as the migration seeds them: lookup off, upstream URL."""
        self.values = {
            passkey_authenticator_manager.LOOKUP_SETTING: "false",
            passkey_authenticator_manager.URL_SETTING: passkey_authenticator_manager.DEFAULT_URL,
        }

    def get_setting(self, _user: object, key: str, default_value: str = "") -> str:
        """Read one, as Setting.get_setting does."""
        return self.values.get(key, default_value)

    def get_setting_bool(self, user: object, key: str, default_value: bool = False) -> bool:
        """Read a switch, as Setting.get_setting_bool does."""
        return self.get_setting(user, key, "true" if default_value else "false").lower().strip() == "true"


class Upstream:
    """The list as GitHub serves it, counting downloads; set ``failure`` to make them fail."""

    def __init__(self) -> None:
        """Serve the sample list."""
        self.payload: object = UPSTREAM
        self.failure: Exception | None = None
        self.status = 200
        self.calls = 0

    def get(self, url: str, timeout: tuple[int, int]) -> SimpleNamespace:  # noqa: ARG002
        """Answer one download."""
        self.calls += 1
        if self.failure:
            raise self.failure

        def raise_for_status() -> None:
            if self.status >= 400:
                msg = f"{self.status} Server Error"
                raise requests.HTTPError(msg)

        def payload() -> object:
            if isinstance(self.payload, Exception):
                raise self.payload
            return self.payload

        return SimpleNamespace(raise_for_status=raise_for_status, json=payload)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Serve the settings without a database, with the lookup turned on and pointed at URL."""
    fake = Settings()
    fake.values[passkey_authenticator_manager.LOOKUP_SETTING] = "true"
    fake.values[passkey_authenticator_manager.URL_SETTING] = URL
    monkeypatch.setattr(Setting, "get_setting", fake.get_setting)
    monkeypatch.setattr(Setting, "get_setting_bool", fake.get_setting_bool)
    return fake


@pytest.fixture
def redis(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> FakeRedis:  # noqa: ARG001
    """Point the manager at a fake Redis, with the lookup turned on."""
    fake = FakeRedis()
    monkeypatch.setattr(passkey_authenticator_manager, "redis_client", fake)
    return fake


@pytest.fixture
def upstream(monkeypatch: pytest.MonkeyPatch) -> Upstream:
    """Serve the list without a network."""
    fake = Upstream()
    monkeypatch.setattr(passkey_authenticator_manager.requests, "get", fake.get)
    return fake


def _age_the_list(redis: FakeRedis) -> None:
    """Make the cached list due for its weekly refresh."""
    redis.store[passkey_authenticator_manager.FETCHED_AT_KEY] = str(
        time.time() - passkey_authenticator_manager.REFRESH_AFTER_SECONDS - 1,
    )


@pytest.mark.usefixtures("redis", "upstream")
def test_a_known_aaguid_is_described_by_name_and_icons() -> None:
    assert passkey_authenticator_manager.describe(YUBIKEY.upper()) == {
        "name": "YubiKey 5 Series",
        "icon_light": ICON_LIGHT,
        "icon_dark": ICON_DARK,
    }


@pytest.mark.usefixtures("redis", "upstream")
def test_an_aaguid_the_list_does_not_know_is_not_described() -> None:
    assert passkey_authenticator_manager.describe("11111111-2222-3333-4444-555555555555") is None


@pytest.mark.usefixtures("redis")
@pytest.mark.parametrize("aaguid", [None, "", passkey_authenticator_manager.ZERO_AAGUID])
def test_a_missing_or_undisclosed_aaguid_downloads_nothing(upstream: Upstream, aaguid: str | None) -> None:
    assert passkey_authenticator_manager.describe(aaguid) is None
    assert upstream.calls == 0


def test_the_list_is_downloaded_once_and_then_served_from_redis(redis: FakeRedis, upstream: Upstream) -> None:
    passkey_authenticator_manager.describe(YUBIKEY)
    passkey_authenticator_manager.describe(BITWARDEN)

    assert upstream.calls == 1
    assert passkey_authenticator_manager.LOCK_KEY not in redis.store


def test_a_due_refresh_replaces_the_cached_list(redis: FakeRedis, upstream: Upstream) -> None:
    passkey_authenticator_manager.describe(YUBIKEY)
    _age_the_list(redis)
    upstream.payload = {YUBIKEY: {"name": "YubiKey 5 Series with NFC"}}

    assert passkey_authenticator_manager.describe(YUBIKEY)["name"] == "YubiKey 5 Series with NFC"
    # Entries the new list dropped are gone, not merged with the old ones.
    assert passkey_authenticator_manager.describe(BITWARDEN) is None


@pytest.mark.parametrize(
    "break_upstream",
    [
        pytest.param(lambda upstream: setattr(upstream, "failure", requests.ConnectTimeout("timed out")), id="timeout"),
        pytest.param(lambda upstream: setattr(upstream, "status", 500), id="server-error"),
        pytest.param(lambda upstream: setattr(upstream, "payload", ValueError("not json")), id="invalid-json"),
        pytest.param(lambda upstream: setattr(upstream, "payload", ["not", "an", "object"]), id="not-an-object"),
        pytest.param(lambda upstream: setattr(upstream, "payload", {}), id="retired-list"),
    ],
)
def test_a_failed_refresh_keeps_serving_the_last_good_list(redis: FakeRedis, upstream: Upstream, break_upstream) -> None:  # noqa: ANN001
    passkey_authenticator_manager.describe(YUBIKEY)
    _age_the_list(redis)
    stale_since = redis.store[passkey_authenticator_manager.FETCHED_AT_KEY]
    break_upstream(upstream)

    assert passkey_authenticator_manager.describe(YUBIKEY)["name"] == "YubiKey 5 Series"
    assert redis.store[passkey_authenticator_manager.FETCHED_AT_KEY] == stale_since
    # The lock stays until it expires, so the next lookups do not try again straight away.
    passkey_authenticator_manager.describe(YUBIKEY)
    assert upstream.calls == 2


@pytest.mark.usefixtures("redis")
def test_without_any_list_a_failed_download_describes_nothing(upstream: Upstream) -> None:
    upstream.failure = requests.ConnectionError("no route to host")

    assert passkey_authenticator_manager.describe(YUBIKEY) is None
    assert passkey_authenticator_manager.describe(YUBIKEY) is None
    assert upstream.calls == 1


@pytest.mark.usefixtures("upstream")
def test_a_redis_outage_costs_the_name_not_the_request(redis: FakeRedis) -> None:
    redis.broken = True

    assert passkey_authenticator_manager.describe(YUBIKEY) is None


@pytest.mark.usefixtures("redis")
def test_the_lookup_is_off_until_an_administrator_turns_it_on(settings: Settings, upstream: Upstream) -> None:
    settings.values = Settings().values  # as the migration seeds them

    assert passkey_authenticator_manager.lookup_enabled() is False
    assert passkey_authenticator_manager.describe(YUBIKEY) is None
    assert upstream.calls == 0


@pytest.mark.usefixtures("redis")
def test_an_empty_url_switches_the_lookup_off_too(settings: Settings, upstream: Upstream) -> None:
    settings.values[passkey_authenticator_manager.URL_SETTING] = "  "

    assert passkey_authenticator_manager.lookup_enabled() is False
    assert passkey_authenticator_manager.describe(YUBIKEY) is None
    assert upstream.calls == 0


@pytest.mark.usefixtures("redis")
def test_pointing_the_setting_at_another_list_refreshes_it_straight_away(settings: Settings, upstream: Upstream) -> None:
    passkey_authenticator_manager.describe(YUBIKEY)
    settings.values[passkey_authenticator_manager.URL_SETTING] = "https://mirror.example.test/aaguids.json"
    upstream.payload = {YUBIKEY: {"name": "From the mirror"}}

    assert passkey_authenticator_manager.describe(YUBIKEY)["name"] == "From the mirror"
    assert upstream.calls == 2


@pytest.mark.usefixtures("redis", "upstream")
def test_a_settings_failure_costs_the_name_not_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: object, **_kwargs: object) -> bool:
        msg = "database is down"
        raise RuntimeError(msg)

    monkeypatch.setattr(Setting, "get_setting_bool", broken)

    assert passkey_authenticator_manager.lookup_enabled() is False
    assert passkey_authenticator_manager.describe(YUBIKEY) is None


@pytest.mark.usefixtures("redis")
def test_unusable_entries_and_icons_are_dropped_one_by_one(upstream: Upstream) -> None:
    good = "11111111-1111-1111-1111-111111111111"
    unsafe_icon = "22222222-2222-2222-2222-222222222222"
    huge_icon = "33333333-3333-3333-3333-333333333333"
    nameless = "44444444-4444-4444-4444-444444444444"
    upstream.payload = {
        good: {"name": "  Good Key  ", "icon_light": ICON_LIGHT},
        unsafe_icon: {"name": "Unsafe", "icon_light": "javascript:alert(1)", "icon_dark": "data:text/html;base64,PHA+"},
        huge_icon: {"name": "Huge", "icon_light": "data:image/png;base64," + "A" * passkey_authenticator_manager.MAX_ICON_LENGTH},
        nameless: {"icon_light": ICON_LIGHT},
        "not-an-aaguid": {"name": "Broken key"},
        "55555555-5555-5555-5555-555555555555": "not an object",
    }

    assert passkey_authenticator_manager.describe(good) == {"name": "Good Key", "icon_light": ICON_LIGHT, "icon_dark": None}
    assert passkey_authenticator_manager.describe(unsafe_icon) == {"name": "Unsafe", "icon_light": None, "icon_dark": None}
    assert passkey_authenticator_manager.describe(huge_icon) == {"name": "Huge", "icon_light": None, "icon_dark": None}
    assert passkey_authenticator_manager.describe(nameless) is None


@pytest.mark.usefixtures("redis", "upstream")
def test_a_dark_icon_identical_to_the_light_one_is_not_sent_twice() -> None:
    assert passkey_authenticator_manager.describe(BITWARDEN) == {"name": "Bitwarden", "icon_light": ICON_LIGHT, "icon_dark": None}


def test_registration_records_the_aaguid_the_authenticator_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    added = []
    monkeypatch.setattr(webauthn_manager, "_rp_config", lambda: ("taranis.test", "Taranis NG", ["https://taranis.test"]))
    monkeypatch.setattr(
        webauthn_manager,
        "_pop_challenge",
        lambda _purpose, _challenge_id: {"challenge": bytes_to_base64url(b"challenge"), "user_id": 7},
    )
    monkeypatch.setattr(
        webauthn_manager,
        "verify_registration_response",
        lambda **_kwargs: SimpleNamespace(credential_id=b"credential", credential_public_key=b"key", sign_count=0, aaguid=YUBIKEY),
    )
    monkeypatch.setattr(db_manager.db, "session", SimpleNamespace(add=added.append, commit=lambda: None))

    record = webauthn_manager.finish_registration(SimpleNamespace(id=7), "challenge-id", {"response": {}}, "Work key")

    assert added == [record]
    assert record.aaguid == YUBIKEY


def test_the_gui_gets_the_aaguid_and_its_authenticator_with_each_passkey(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(passkey_authenticator_manager, "describe", lambda aaguid: {"name": f"named {aaguid}"} if aaguid else None)
    monkeypatch.setattr(passkey_authenticator_manager, "lookup_enabled", lambda: True)
    recorded = WebauthnCredential(7, "Work key", "credential", "key", aaguid=YUBIKEY)
    legacy = WebauthnCredential(7, "Old key", "credential-2", "key")

    assert recorded.to_json()["aaguid"] == YUBIKEY
    assert recorded.to_json()["authenticator"] == {"name": f"named {YUBIKEY}"}
    assert legacy.to_json()["aaguid"] is None
    assert legacy.to_json()["authenticator"] is None
    assert recorded.to_json()["authenticator_lookup"] is True
    # Never key material.
    assert "public_key" not in recorded.to_json()
    assert "credential_id" not in recorded.to_json()

    mfa = User.mfa.fget(SimpleNamespace(totp_secret="secret", webauthn_credentials=[recorded, legacy]))

    assert mfa["totp"] is True
    assert mfa["passkeys"] == 2
    assert [passkey["name"] for passkey in mfa["passkey_details"]] == ["Work key", "Old key"]
    assert json.dumps(mfa)  # it travels to the GUI as JSON
