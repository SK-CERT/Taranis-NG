"""The shared diagnostic for a key file a preset names but the publisher cannot read.

Both publishers that read a mounted key report the failure through
``unreadable_key_error``, so what an operator is told - which path was actually
opened, and that an unprivileged service could not open it - is asserted here
once.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest
from managers.key_files import unreadable_key_error


def _permission_denied(path: str) -> PermissionError:
    """Build the error the OS raises for a file the service may not read."""
    return PermissionError(errno.EACCES, os.strerror(errno.EACCES), path)


def _not_found(path: str) -> FileNotFoundError:
    """Build the error the OS raises for a path that does not exist."""
    return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)


def test_relative_path_is_reported_as_the_absolute_one_opened() -> None:
    """A preset's relative path means nothing outside the container; resolve it.

    The failure that prompted this named ``crypto/taranis``, which exists
    nowhere the operator could look - it is ``/app/crypto/taranis`` inside the
    publishers image.
    """
    error = unreadable_key_error("crypto/taranis", "SSH key", _permission_denied("crypto/taranis"))

    reported = str(error)
    assert str(Path("crypto/taranis").resolve()) in reported
    # The path is reported absolute, never as the bare relative string given.
    assert " at /" in reported


def test_permission_denied_names_the_uid_and_the_remedy() -> None:
    """The service no longer runs as root, so say so and how to fix it."""
    message = str(unreadable_key_error("/app/crypto/taranis", "SSH key", _permission_denied("/app/crypto/taranis")))

    assert "Permission denied" in message
    assert f"uid {os.getuid()}" in message
    assert f"chown {os.getuid()}" in message


def test_other_errors_do_not_claim_a_permission_problem() -> None:
    """A missing key is not an ownership problem; do not send the operator chowning."""
    message = str(unreadable_key_error("/app/crypto/typo", "SSH key", _not_found("/app/crypto/typo")))

    assert "No such file or directory" in message
    assert "chown" not in message
    assert "uid" not in message


def test_description_identifies_which_configured_file_failed() -> None:
    """A preset can name three key files; the message has to say which one."""
    path = "/app/crypto/sign.pem"

    assert "email signing key" in str(unreadable_key_error(path, "email signing key", _not_found(path)))
    assert "SSH key" in str(unreadable_key_error(path, "SSH key", _not_found(path)))


def test_the_original_error_is_available_as_the_cause() -> None:
    """The replacement carries the message; the original still carries the errno."""
    original = _permission_denied("/app/crypto/taranis")
    replacement = unreadable_key_error("/app/crypto/taranis", "SSH key", original)

    with pytest.raises(OSError, match="Cannot read the SSH key") as caught:
        raise replacement from original

    assert caught.value.__cause__ is original
    assert caught.value.__cause__.errno == errno.EACCES
