"""The FTP publisher's upload path.

It used to stage the payload as a temporary file in the working directory,
which the image owns as root - so every publish failed once the service stopped
running as root, and the ``finally`` that removed the file then raised
FileNotFoundError over the top of the real error.
"""

from __future__ import annotations

import errno
import ftplib
import os
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from publishers.ftp_publisher import FTPPublisher

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeFTP:
    """Stand-in for ``ftplib.FTP``, recording what was stored."""

    last: FakeFTP | None = None

    def __init__(self) -> None:
        """Register this instance as the most recently constructed one."""
        self.stored: list[tuple[str, bytes]] = []
        self.quit_called = False
        FakeFTP.last = self

    def connect(self, host: str, port: int) -> None:
        """Accept the connection."""

    def login(self, user: str | None, passwd: str | None) -> None:
        """Accept the credentials."""

    def storbinary(self, command: str, fp: object) -> None:
        """Record the upload, reading the payload the way ftplib does."""
        self.stored.append((command, fp.read()))

    def quit(self) -> None:
        """Close the session."""
        self.quit_called = True


@pytest.fixture
def unwritable_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Put the publisher in a working directory it cannot write to.

    This is /app in the image: root owns it so the runtime user cannot create
    files there. Simulated rather than reproduced with permissions, because root
    bypasses file modes and the suite would otherwise assert nothing when it runs
    as root - which is the normal case in a container.
    """
    monkeypatch.chdir(tmp_path)
    real_open = Path.open

    def guarded(self: Path, mode: str = "r", *args: object, **kwargs: object) -> object:
        if any(flag in mode for flag in "wax"):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(self))
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    return tmp_path


@pytest.fixture
def ftp(monkeypatch: pytest.MonkeyPatch) -> type[FakeFTP]:
    """Replace the FTP client the publisher builds."""
    FakeFTP.last = None
    monkeypatch.setattr(ftplib, "FTP", FakeFTP)
    return FakeFTP


def test_the_payload_is_uploaded_from_memory(
    publisher_input: Callable[..., object],
    ftp: type[FakeFTP],
    unwritable_cwd: Path,
) -> None:
    """The upload succeeds even though the working directory refuses writes.

    It used to stage the payload there first, so this failed outright once the
    service stopped running as root - and the ``finally`` that removed the file
    then raised FileNotFoundError over the top of the real error, so what
    reached the operator did not mention permissions at all.
    """
    preset = publisher_input(FTP_URL="ftp://user:pass@ftp.example.org/incoming/")

    _, status = FTPPublisher().publish(preset)

    assert status == HTTPStatus.OK
    assert list(unwritable_cwd.iterdir()) == []
    command, payload = ftp.last.stored[0]
    assert command.startswith("STOR /incoming/file_")
    assert payload == b'{"report": "test"}'
    assert ftp.last.quit_called


@pytest.mark.usefixtures("ftp", "unwritable_cwd")
def test_an_unsupported_scheme_is_reported_not_raised(
    publisher_input: Callable[..., object],
) -> None:
    """The branch returns its own error, not one from a cleanup step.

    This return used to run a ``finally`` that unlinked the staged file, so the
    error the operator saw came from the cleanup rather than from the scheme.
    """
    preset = publisher_input(FTP_URL="sftp://user:pass@ftp.example.org/incoming/")

    body, status = FTPPublisher().publish(preset)

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "not supported by the FTP publisher" in body["error"]


@pytest.mark.usefixtures("ftp", "unwritable_cwd")
def test_a_failed_upload_reports_the_upload_error(
    publisher_input: Callable[..., object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The error that reaches the operator is the one that actually happened."""

    def refuse(*_args: object) -> None:
        msg = "550 Permission denied on the remote server"
        raise ftplib.error_perm(msg)  # noqa: S321 - the publisher under test speaks FTP

    monkeypatch.setattr(FakeFTP, "storbinary", refuse)
    preset = publisher_input(FTP_URL="ftp://user:pass@ftp.example.org/incoming/")

    body, status = FTPPublisher().publish(preset)

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "550 Permission denied on the remote server" in body["error"]
