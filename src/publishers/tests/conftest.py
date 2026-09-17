"""Pytest bootstrap and shared key fixtures for the publishers package.

Importing the application package reads the Docker secret ``/run/secrets/api_key``
at import time (``config.Config``). Tests have no secrets, so a stub ``config``
module is injected before any application import, exactly as the core and
presenters suites do.

Two publishers read a key file an operator names in a preset - the SFTP
publisher's private key and the email publisher's signing and encryption keys -
and both are mounted in from the host. The fixtures here generate real key
material so those paths are exercised for what they are, rather than mocked.

Permission failures are *injected* rather than provoked with ``chmod``: root
bypasses file modes, so a 0000 file is readable when the suite runs as root
(the usual case in a container) and unreadable otherwise, which would make the
most important assertions silently uid-dependent.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import ClassVar

# Make the service importable when the suite runs from the repo root (the
# aggregate testpaths config) as well as from src/publishers. This one goes to
# the FRONT: src/publishers/__init__.py is the Flask app package, so with src/
# on the path ahead of it `publishers` resolves there instead of to the inner
# src/publishers/publishers, and `from publishers.sftp_publisher import ...` -
# how the service itself imports, with /app on PYTHONPATH - stops resolving.
_SERVICE_ROOT = str(Path(__file__).resolve().parents[1])
if sys.path[:1] != [_SERVICE_ROOT]:
    sys.path.insert(0, _SERVICE_ROOT)

# Bind `publishers` to the inner package now, the way the running service does
# (its PYTHONPATH is /app, so `import publishers` is /app/publishers). Otherwise
# pytest gets there first: src/publishers has an __init__.py, so pytest collects
# the service root as a package and imports it as `publishers` with src/ on the
# path - which shadows the inner package, and every
# `from publishers.<x>_publisher import ...` inside the app stops resolving.
importlib.import_module("publishers")

if "config" not in sys.modules:

    class _AnyConfig(type):
        """Metaclass yielding a throwaway value for any Config attribute access."""

        def __getattr__(cls, name: str) -> str:
            return "test-value"

    _module = types.ModuleType("config")

    class Config(metaclass=_AnyConfig):
        """Stub of ``config.Config`` for import-time use in tests."""

    _module.Config = Config
    sys.modules["config"] = _module

KEY_PASSPHRASE = "correct horse battery staple"


def _write_openssh_key(path: Path, key: object, passphrase: str | None = None) -> Path:
    """Serialise a generated private key to OpenSSH format on disk."""
    encryption = serialization.BestAvailableEncryption(passphrase.encode()) if passphrase else serialization.NoEncryption()
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, encryption))
    return path


@pytest.fixture(scope="session")
def rsa_key_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An unencrypted RSA private key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return _write_openssh_key(tmp_path_factory.mktemp("keys") / "id_rsa", key)


@pytest.fixture(scope="session")
def ed25519_key_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An unencrypted Ed25519 private key."""
    key = ed25519.Ed25519PrivateKey.generate()
    return _write_openssh_key(tmp_path_factory.mktemp("keys") / "id_ed25519", key)


@pytest.fixture(scope="session")
def ecdsa_key_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An unencrypted ECDSA private key."""
    key = ec.generate_private_key(ec.SECP256R1())
    return _write_openssh_key(tmp_path_factory.mktemp("keys") / "id_ecdsa", key)


@pytest.fixture(scope="session")
def encrypted_key_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An Ed25519 private key protected by ``KEY_PASSPHRASE``."""
    key = ed25519.Ed25519PrivateKey.generate()
    return _write_openssh_key(tmp_path_factory.mktemp("keys") / "id_encrypted", key, KEY_PASSPHRASE)


@pytest.fixture
def not_a_key_file(tmp_path: Path) -> Path:
    """A readable file that is not a private key of any kind."""
    path = tmp_path / "notakey.txt"
    path.write_text("this is not a private key\n")
    return path


@pytest.fixture
def publisher_input() -> Callable[..., types.SimpleNamespace]:
    """Build the input object a publisher's ``publish`` receives.

    Returns:
        Callable: Takes the preset's parameter values as keyword arguments and
            returns the input, with the payload fields a presenter would fill in.
    """

    def _build(**param_key_values: str) -> types.SimpleNamespace:
        # The payload fields mirror shared.schema.publisher.PublisherInput, so a
        # publisher reading one the tests forgot fails here rather than silently.
        return types.SimpleNamespace(
            name="test preset",
            type="TEST_PUBLISHER",
            mime_type="application/json",
            data="eyJyZXBvcnQiOiAidGVzdCJ9",  # {"report": "test"}
            message_title=None,
            message_body=None,
            message_body_mime_type=None,
            message_headers=[],
            recipients=[],
            att_file_name=None,
            param_key_values=param_key_values,
        )

    return _build


# What an operator fills in for a working email preset. A test overrides the one or two
# values it is about, so the rest of the preset stays out of the way of what it asserts.
EMAIL_PRESET_VALUES = {
    "SMTP_SERVER": "smtp.example.org",
    "SMTP_SERVER_PORT": "587",
    "EMAIL_USERNAME": "taranis",
    "EMAIL_PASSWORD": "hunter2",
    "EMAIL_SENDER": "taranis@example.org",
    "EMAIL_RECIPIENT": "constituency@example.org",
    "EMAIL_SUBJECT": "Security Warning",
    "EMAIL_MESSAGE": "See attached.",
    "EMAIL_SIGN": "",
    "EMAIL_SIGN_PASSWORD": "",
    "EMAIL_ENCRYPT": "",
}


@pytest.fixture
def email_preset(publisher_input: Callable[..., types.SimpleNamespace]) -> Callable[..., types.SimpleNamespace]:
    """Build an email preset, overriding only what a test cares about.

    Preset parameters and payload fields are told apart by case, the way they are named in
    the product: ``EMAIL_SUBJECT`` is what the operator configured, ``message_title`` is what
    core sent for this one publication.

    Returns:
        Callable: Takes ``UPPERCASE`` preset parameters and lowercase ``PublisherInput``
            payload fields as keyword arguments, and returns the input object.
    """

    def _build(**overrides: object) -> types.SimpleNamespace:
        values = dict(EMAIL_PRESET_VALUES)
        payload = {}
        for key, value in overrides.items():
            if key.isupper():
                values[key] = value
            else:
                payload[key] = value

        preset = publisher_input(**values)
        for field, value in payload.items():
            # SimpleNamespace takes any attribute, so a typo would just sit there unread.
            if not hasattr(preset, field):
                msg = f"{field!r} is not a PublisherInput payload field"
                raise AttributeError(msg)
            setattr(preset, field, value)
        return preset

    return _build


class FakeEnvelope:
    """Stand-in for ``envelope.Envelope``, recording what the publisher asked of it.

    For the tests that are about the publisher's own decisions: which headers it passes on,
    which key material it applies, whether it sent at all. The tests about the message that
    actually goes out drive the real envelope over a stub SMTP server instead, in
    ``test_email_publisher_delivery.py`` - a fake cannot tell you what the library produced.
    """

    last: FakeEnvelope | None = None
    # Set on the class before publishing to make the next envelope's header() raise; the
    # publisher builds its own envelope, so a test cannot reach the instance in time.
    header_error: ClassVar[Exception | None] = None

    def __init__(self) -> None:
        """Register this instance and start with nothing applied."""
        self.headers: list[tuple[str, str]] = []
        self.signed_with: str | None = None
        self.signed_passphrase: str | None = None
        self.encrypted_with: str | None = None
        self.sent = False
        FakeEnvelope.last = self

    def header(self, key: str, val: str | None = None) -> FakeEnvelope:
        """Record a header. Overrides the catch-all below, which would swallow the call."""
        if FakeEnvelope.header_error is not None:
            raise FakeEnvelope.header_error
        self.headers.append((key, val))
        return self

    def signature(self, key: str | None = None, passphrase: str | None = None) -> FakeEnvelope:
        """Record the signing key and its passphrase."""
        self.signed_with = key
        self.signed_passphrase = passphrase
        return self

    def encryption(self, key: str | None = None) -> FakeEnvelope:
        """Record the encryption key."""
        self.encrypted_with = key
        return self

    def send(self) -> bool:
        """Pretend the message went out."""
        self.sent = True
        return True

    def __getattr__(self, name: str) -> Callable[..., FakeEnvelope]:
        """Accept every other envelope call (message, subject, attach, smtp...)."""
        return lambda *_args, **_kwargs: self

    @staticmethod
    def smtp_quit() -> None:
        """Close the SMTP session."""

    def __str__(self) -> str:
        """Render the composed message for the publisher's debug log."""
        return "<envelope>"


@pytest.fixture
def envelope(monkeypatch: pytest.MonkeyPatch) -> type[FakeEnvelope]:
    """Replace the envelope the publisher builds."""
    FakeEnvelope.last = None
    # By name, so conftest needs no import of the service module before the config stub
    # above is in place. The knob goes through monkeypatch to be restored after the test.
    monkeypatch.setattr("publishers.email_publisher.Envelope", FakeEnvelope)
    monkeypatch.setattr(FakeEnvelope, "header_error", None)
    return FakeEnvelope
