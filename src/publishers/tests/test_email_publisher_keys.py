"""Signing and encryption keys an email preset names.

A preset that names a key file is asking for the report to be protected. The
question these ask is what happens when that file cannot be read: the answer
has to be a failed publish, never a message that goes out unprotected.

They work against the ``FakeEnvelope`` in conftest, which records the key material the
publisher applied. Whether the library then produces a correctly signed message is not
covered anywhere: ``M2Crypto`` is installed in neither the test environment nor the
publishers image, so S/MIME cannot actually run here.
"""

from __future__ import annotations

import errno
import os
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from publishers.email_publisher import EMAILPublisher

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import FakeEnvelope


@pytest.fixture
def signing_key(tmp_path: Path) -> Path:
    """A readable file standing in for signing material."""
    path = tmp_path / "sign.pem"
    path.write_text("-----BEGIN PGP PRIVATE KEY BLOCK-----\nkey\n")
    return path


def test_a_configured_key_that_is_missing_fails_the_publish(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
    tmp_path: Path,
) -> None:
    """The regression this suite exists for.

    ``Path(sign).is_file()`` was False for a path that does not exist, which
    skipped the whole branch: the report was sent unsigned, with no error and no
    log line. A preset asking for a signature must fail instead.
    """
    preset = email_preset(EMAIL_SIGN=str(tmp_path / "absent.pem"))

    body, status = EMAILPublisher().publish(preset)

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "email signing key" in body["error"]
    assert envelope.last.signed_with is None
    assert not envelope.last.sent


def test_a_missing_encryption_key_is_never_sent_in_clear(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
    tmp_path: Path,
) -> None:
    """Same for encryption, where sending anyway means sending in the clear."""
    preset = email_preset(EMAIL_ENCRYPT=str(tmp_path / "absent.pem"))

    body, status = EMAILPublisher().publish(preset)

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "email encryption key" in body["error"]
    assert not envelope.last.sent


def test_an_unreadable_key_explains_the_unprivileged_user(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
    signing_key: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mounted-key case, injected so the result does not depend on the uid."""

    def deny(self: Path, *_args: object, **_kwargs: object) -> str:
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(self))

    monkeypatch.setattr(Path, "read_text", deny)

    body, status = EMAILPublisher().publish(email_preset(EMAIL_SIGN=str(signing_key)))

    assert status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert f"chown {os.getuid()}" in body["error"]
    assert not envelope.last.sent


def test_a_readable_key_signs_the_message(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
    signing_key: Path,
) -> None:
    """The configured key's contents reach the envelope."""
    _, status = EMAILPublisher().publish(email_preset(EMAIL_SIGN=str(signing_key)))

    assert status == HTTPStatus.OK
    assert envelope.last.signed_with == signing_key.read_text()


def test_auto_is_passed_through_rather_than_read_as_a_path(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    """The literal "auto" asks the envelope library to find the key; it is not a path."""
    _, status = EMAILPublisher().publish(email_preset(EMAIL_SIGN="auto", EMAIL_ENCRYPT="auto"))

    assert status == HTTPStatus.OK
    assert envelope.last.signed_with == "auto"
    assert envelope.last.encrypted_with == "auto"


def test_an_unconfigured_preset_sends_without_protection(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    """An empty setting means the preset never asked for signing; that still sends."""
    _, status = EMAILPublisher().publish(email_preset())

    assert status == HTTPStatus.OK
    assert envelope.last.signed_with is None
    assert envelope.last.encrypted_with is None
    assert envelope.last.sent
