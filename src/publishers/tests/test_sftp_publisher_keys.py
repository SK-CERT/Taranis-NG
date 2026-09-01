"""Loading the private key an SFTP preset names.

These drive the real ``SFTPPublisher.publish`` with paramiko's client replaced,
so the assertions cover both the key loading and what the publisher then does
with the result - which is the half that used to go wrong quietly.
"""

from __future__ import annotations

import errno
import os
from http import HTTPStatus
from typing import TYPE_CHECKING

import paramiko
import pytest
from conftest import KEY_PASSPHRASE
from publishers.sftp_publisher import SFTPPublisher

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class FakeSFTP:
    """The SFTP channel, recording what was uploaded."""

    def __init__(self) -> None:
        """Start with nothing uploaded."""
        self.uploaded: list[tuple[str, bytes]] = []

    def putfo(self, file_object: object, path: str, confirm: bool = True) -> None:
        """Record an upload, reading the payload the way paramiko does."""
        assert confirm, "the publisher should ask for the upload to be confirmed"
        self.uploaded.append((path, file_object.read()))

    def close(self) -> None:
        """Close the channel."""


class FakeSSHClient:
    """Stand-in for ``paramiko.SSHClient`` that records the connect arguments."""

    last: FakeSSHClient | None = None

    def __init__(self) -> None:
        """Register this instance as the most recently constructed one."""
        self.connect_kwargs: dict | None = None
        self.sftp = FakeSFTP()
        FakeSSHClient.last = self

    def set_missing_host_key_policy(self, policy: object) -> None:
        """Accept whatever policy the publisher installs."""

    def get_host_keys(self) -> dict:
        """Return an empty host key store."""
        return {}

    def connect(self, **kwargs: object) -> None:
        """Record how authentication was attempted."""
        self.connect_kwargs = kwargs

    def open_sftp(self) -> FakeSFTP:
        """Return the recording channel."""
        return self.sftp

    def exec_command(self, command: str) -> None:
        """Accept a post-upload command."""

    def close(self) -> None:
        """Close the connection."""


@pytest.fixture
def ssh_client(monkeypatch: pytest.MonkeyPatch) -> type[FakeSSHClient]:
    """Replace the paramiko client the publisher builds."""
    FakeSSHClient.last = None
    monkeypatch.setattr(paramiko, "SSHClient", FakeSSHClient)
    return FakeSSHClient


@pytest.fixture
def sftp_preset(publisher_input: Callable[..., object]) -> Callable[..., object]:
    """Build an SFTP preset, overriding only what a test cares about."""

    def _build(**overrides: str) -> object:
        values = {
            "SFTP_URL": "sftp.example.org",
            "PORT": "22",
            "USERNAME": "taranis",
            "PASSWORD": "",
            "PATH": "/upload",
            "FILENAME": "report",
            "COMMAND": "",
            "SSH_KEY": "",
            "SSH_KEY_PASSWORD": "",
            "HOST_KEY": "",
        }
        values.update(overrides)
        return publisher_input(**values)

    return _build


@pytest.mark.parametrize("key_fixture", ["rsa_key_file", "ed25519_key_file", "ecdsa_key_file"])
def test_every_key_type_paramiko_still_supports_is_loaded(
    key_fixture: str,
    request: pytest.FixtureRequest,
    sftp_preset: Callable[..., object],
    ssh_client: type[FakeSSHClient],
) -> None:
    """RSA, Ed25519 and ECDSA all authenticate.

    These are every type paramiko 5 can load, DSA having been removed with
    ``paramiko.DSSKey``. The loader's dead reference to that class is reached
    only once every type has failed, which
    ``test_a_file_that_is_not_a_key_names_the_supported_types`` covers.
    """
    key_path = request.getfixturevalue(key_fixture)

    _, status = SFTPPublisher().publish(sftp_preset(SSH_KEY=str(key_path)))

    assert status == HTTPStatus.OK
    assert "pkey" in ssh_client.last.connect_kwargs


def test_encrypted_key_is_loaded_with_its_passphrase(
    encrypted_key_file: Path,
    sftp_preset: Callable[..., object],
    ssh_client: type[FakeSSHClient],
) -> None:
    """A passphrase-protected key works when the preset carries the passphrase."""
    preset = sftp_preset(SSH_KEY=str(encrypted_key_file), SSH_KEY_PASSWORD=KEY_PASSPHRASE)

    _, status = SFTPPublisher().publish(preset)

    assert status == HTTPStatus.OK
    assert ssh_client.last.connect_kwargs["pkey"].get_name() == "ssh-ed25519"


def test_encrypted_key_without_a_passphrase_says_so(
    encrypted_key_file: Path,
    sftp_preset: Callable[..., object],
    ssh_client: type[FakeSSHClient],
) -> None:
    """Report the missing passphrase, not a complaint about the last key type.

    The OpenSSH envelope is decrypted before the key type inside it matters, so
    retrying the other classes only replaced this diagnosis with a worse one.
    """
    body, status = SFTPPublisher().publish(sftp_preset(SSH_KEY=str(encrypted_key_file)))

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "encrypted" in body["error"]
    assert ssh_client.last is None or ssh_client.last.connect_kwargs is None


@pytest.mark.usefixtures("ssh_client")
def test_a_file_that_is_not_a_key_names_the_supported_types(
    not_a_key_file: Path,
    sftp_preset: Callable[..., object],
) -> None:
    """Say what the file is not, and what would have worked."""
    body, status = SFTPPublisher().publish(sftp_preset(SSH_KEY=str(not_a_key_file)))

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert str(not_a_key_file) in body["error"]
    for key_type in ("RSA", "Ed25519", "ECDSA"):
        assert key_type in body["error"]


def test_an_unusable_key_never_falls_back_to_password_authentication(
    not_a_key_file: Path,
    sftp_preset: Callable[..., object],
    ssh_client: type[FakeSSHClient],
) -> None:
    """A preset naming a key must fail rather than quietly authenticate by password.

    The loader used to return None when no key type matched, which sent the
    caller down the ``else`` branch and connected with the preset's password. On
    the pinned paramiko that return was unreachable - the missing DSSKey raised
    AttributeError first - so this guards the contract rather than a live bug:
    a key the preset names is now either used or fatal, never skipped.
    """
    preset = sftp_preset(SSH_KEY=str(not_a_key_file), PASSWORD="a-password-that-must-not-be-used")

    _, status = SFTPPublisher().publish(preset)

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert ssh_client.last is None or ssh_client.last.connect_kwargs is None


def test_a_preset_with_no_key_still_authenticates_by_password(
    sftp_preset: Callable[..., object],
    ssh_client: type[FakeSSHClient],
) -> None:
    """Password auth stays available for the presets that are configured for it."""
    _, status = SFTPPublisher().publish(sftp_preset(PASSWORD="hunter2"))

    assert status == HTTPStatus.OK
    assert ssh_client.last.connect_kwargs["password"] == "hunter2"
    assert "pkey" not in ssh_client.last.connect_kwargs


@pytest.mark.usefixtures("ssh_client")
def test_a_relative_key_path_is_reported_as_the_absolute_one(
    sftp_preset: Callable[..., object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reported path has to be findable; ``crypto/taranis`` was not."""
    monkeypatch.chdir(tmp_path)

    body, status = SFTPPublisher().publish(sftp_preset(SSH_KEY="crypto/taranis"))

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert str(tmp_path / "crypto" / "taranis") in body["error"]


@pytest.mark.usefixtures("ssh_client")
def test_an_unreadable_key_explains_the_unprivileged_user(
    rsa_key_file: Path,
    sftp_preset: Callable[..., object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A key only root can read is the failure this whole path exists for.

    Injected rather than provoked with ``chmod``, so the assertion holds whether
    or not the suite happens to run as root.
    """

    def deny(*_args: object, **_kwargs: object) -> None:
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(rsa_key_file))

    monkeypatch.setattr(paramiko.RSAKey, "__init__", deny)

    body, status = SFTPPublisher().publish(sftp_preset(SSH_KEY=str(rsa_key_file)))

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "Permission denied" in body["error"]
    assert f"chown {os.getuid()}" in body["error"]
