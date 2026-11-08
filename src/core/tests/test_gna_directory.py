"""The GCVE GNA directory: signed, cached, and the source of an organization's GNA short name.

No network and no Redis: the downloads and the cache are stubbed. A key pair made here signs the
test directories; the gcve.eu key is checked against what gcve.eu published.
"""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from managers import gna_directory

from shared import gcve

CUSTOM_URL = "https://directory.example.org/gcve.json"
ENTRIES = [
    {"id": 0, "short_name": "CVE", "full_name": "CVE Program"},
    {
        "id": 65535,
        "short_name": "TEST-GNA",
        "full_name": "Example test authority",
        "gcve_url": "https://advisories.example.org/",
        "gcve_pull_api": "https://advisories.example.org/",
        "inserted_at": "2026-01-31T07:42:49Z",
    },
    {"id": 4242, "short_name": "A-SHORT-NAME-FAR-LONGER-THAN-THIRTY-TWO", "gcve_dump": "ftp://not-a-web-address/"},
    {"id": "7", "short_name": "not a number"},
    "not an entry",
]
BODY = json.dumps(ENTRIES).encode()


@pytest.fixture(scope="module")
def key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem(key: rsa.RSAPrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def _sign(key: rsa.RSAPrivateKey, body: bytes) -> bytes:
    # As gcve.eu publishes it: base64 in lines.
    encoded = base64.b64encode(key.sign(body, padding.PKCS1v15(), hashes.SHA512()))
    return b"\n".join(encoded[index : index + 64] for index in range(0, len(encoded), 64)) + b"\n"


def test_a_signature_by_the_key_verifies_and_nothing_else_does(key: rsa.RSAPrivateKey) -> None:
    signature = _sign(key, BODY)

    assert gna_directory.verify(BODY, signature, _pem(key))
    assert not gna_directory.verify(BODY + b" ", signature, _pem(key))
    assert not gna_directory.verify(BODY, b"not base64 !", _pem(key))
    # Not signed by gcve.eu.
    assert not gna_directory.verify(BODY, signature)


def test_the_pinned_key_is_the_gcve_eu_one() -> None:
    public_key = serialization.load_pem_public_key(gna_directory.PUBLIC_KEY_PEM)
    assert public_key.key_size == 4096


def test_only_usable_entries_are_kept() -> None:
    entries = gna_directory.parse(BODY)

    assert sorted(entries) == ["0", "4242", "65535"]
    assert entries["65535"] == {
        "id": 65535,
        "short_name": "TEST-GNA",
        "full_name": "Example test authority",
        "gcve_url": "https://advisories.example.org/",
        "gcve_pull_api": "https://advisories.example.org/",
    }
    # A short name no record can carry, and an address that is no web address, are dropped.
    assert entries["4242"] == {"id": 4242}
    with pytest.raises(gna_directory.DirectoryError, match="not a list"):
        gna_directory.parse(b'{"id": 1}')
    with pytest.raises(gna_directory.DirectoryError, match="no GNA"):
        gna_directory.parse(b"[]")


def _serve(monkeypatch: pytest.MonkeyPatch, files: dict[str, bytes]) -> list[str]:
    asked: list[str] = []

    def get(url: str, _limit: int) -> bytes:
        asked.append(url)
        if url not in files:
            msg = f"{url} answered HTTP 404"
            raise gna_directory.DirectoryError(msg)
        return files[url]

    monkeypatch.setattr(gna_directory, "_get", get)
    return asked


def test_the_gcve_eu_directory_needs_its_signature(monkeypatch: pytest.MonkeyPatch, key: rsa.RSAPrivateKey) -> None:
    url = gcve.DEFAULT_DIRECTORY_URL
    _serve(monkeypatch, {url: BODY, url + ".sigsha512": _sign(key, BODY)})

    with pytest.raises(gna_directory.DirectoryError, match="was refused: its signature does not match"):
        gna_directory.download(url)

    # Signed by the key the directory is checked with.
    monkeypatch.setattr(gna_directory, "PUBLIC_KEY_PEM", _pem(key))
    data = gna_directory.download(url)
    assert (data["url"], data["verified"], data["warning"]) == (url, True, None)
    assert data["entries"]["65535"]["short_name"] == "TEST-GNA"


def test_another_directory_may_be_unsigned_and_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, {CUSTOM_URL: BODY})

    data = gna_directory.download(CUSTOM_URL)

    assert data["verified"] is False
    assert data["warning"].startswith("it has no signature")
    assert "65535" in data["entries"]


class FakeRedis:
    """Strings and NX locks."""

    def __init__(self) -> None:
        """Start empty."""
        self.store: dict[str, str] = {}

    def get(self, key: str) -> bytes | None:
        """Read a string."""
        value = self.store.get(key)
        return value.encode() if value is not None else None

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool:  # noqa: ARG002
        """Store a string; with nx, only when the key is free."""
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def delete(self, *keys: str) -> None:
        """Forget keys."""
        for key in keys:
            self.store.pop(key, None)


@pytest.fixture
def cache(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()
    monkeypatch.setattr(gna_directory, "redis_client", redis)
    monkeypatch.setattr(gna_directory, "directory_url", lambda: CUSTOM_URL)
    return redis


def test_the_directory_is_downloaded_once_a_day_and_kept_when_a_download_fails(monkeypatch: pytest.MonkeyPatch, cache: FakeRedis) -> None:
    asked = _serve(monkeypatch, {CUSTOM_URL: BODY})

    first = gna_directory.directory()
    again = gna_directory.directory()

    assert first["entries"] == again["entries"]
    assert asked.count(CUSTOM_URL) == 1
    assert gna_directory.lookup(65535)["short_name"] == "TEST-GNA"

    # A forced download that fails keeps the directory, and says why.
    _serve(monkeypatch, {})
    failed = gna_directory.directory(force=True)
    assert failed["entries"] == first["entries"]
    assert "answered HTTP 404" in failed["error"]
    assert gna_directory.status(failed)["error"] == failed["error"]
    assert cache.get(gna_directory.CACHE_KEY) is not None


def test_no_lookup_when_the_setting_is_empty(monkeypatch: pytest.MonkeyPatch, cache: FakeRedis) -> None:  # noqa: ARG001
    monkeypatch.setattr(gna_directory, "directory_url", lambda: None)

    assert gna_directory.directory() is None
    assert gna_directory.lookup(65535) is None


def test_an_organizations_gna_takes_its_names_from_the_directory() -> None:
    data = {"entries": gna_directory.parse(BODY)}
    gna = SimpleNamespace(gna_id=65535, short_name="OLD-NAME", directory=None, directory_checked_at=None)

    assert gna_directory.check_organization(gna, data)
    assert gna.short_name == "TEST-GNA"
    assert gna.directory["full_name"] == "Example test authority"
    assert gna.directory_checked_at is not None
    assert not gna_directory.check_organization(gna, data)

    # A number the directory does not list has no name.
    gna.gna_id = 1
    assert gna_directory.check_organization(gna, data)
    assert (gna.short_name, gna.directory) == (None, None)

    # Without a directory nothing changes.
    gna.short_name = "KEPT"
    assert not gna_directory.check_organization(gna, None)
    assert not gna_directory.check_organization(gna, {"entries": {}})
    assert gna.short_name == "KEPT"
