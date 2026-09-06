"""Custom mail headers a presenter asks the email publisher to set.

The presenter that renders these is a separate node reached over the network, so its
output is untrusted input here. ``envelope.header()`` reroutes ``bcc``, ``cc`` and ``to``
to its own setters, and the SMTP recipient list is built from those - so a header this
publisher accepts without checking could add a recipient. These assert that it checks.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from publishers.email_publisher import EMAILPublisher

from publishers import email_publisher

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeEnvelope:
    """Stand-in for ``envelope.Envelope`` that records the headers it was given."""

    last: FakeEnvelope | None = None

    def __init__(self) -> None:
        """Register this instance and start with no headers."""
        self.headers: list[tuple[str, str]] = []
        self.header_error: Exception | None = None
        self.sent = False
        FakeEnvelope.last = self

    def header(self, key: str, val: str | None = None) -> FakeEnvelope:
        """Record a header. Overrides the catch-all below, which would swallow the call."""
        if self.header_error is not None:
            raise self.header_error
        self.headers.append((key, val))
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
    monkeypatch.setattr(email_publisher, "Envelope", FakeEnvelope)
    return FakeEnvelope


@pytest.fixture
def email_preset(publisher_input: Callable[..., object]) -> Callable[..., object]:
    """Build an email preset carrying the given custom headers."""

    def _build(message_headers: object) -> object:
        preset = publisher_input(
            SMTP_SERVER="smtp.example.org",
            SMTP_SERVER_PORT="587",
            EMAIL_USERNAME="taranis",
            EMAIL_PASSWORD="hunter2",
            EMAIL_SENDER="taranis@example.org",
            EMAIL_RECIPIENT="constituency@example.org",
            EMAIL_SUBJECT="Security Warning",
            EMAIL_MESSAGE="See attached.",
            EMAIL_SIGN="",
            EMAIL_SIGN_PASSWORD="",
            EMAIL_ENCRYPT="",
        )
        preset.message_headers = message_headers
        return preset

    return _build


def test_every_header_reaches_the_envelope_in_order(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    preset = email_preset(
        [
            {"name": "X-Report-Category", "value": "Ransomware, Phishing"},
            {"name": "X-Report-Max-CVSS", "value": "9.8"},
        ],
    )

    _, status = EMAILPublisher().publish(preset)

    assert status == HTTPStatus.OK
    assert envelope.last.headers == [("X-Report-Category", "Ransomware, Phishing"), ("X-Report-Max-CVSS", "9.8")]


def test_a_repeated_header_name_is_passed_through_twice(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    # envelope.header() appends on repeat, which is how a template emits one line per value.
    preset = email_preset(
        [
            {"name": "X-Report-Category", "value": "Ransomware"},
            {"name": "X-Report-Category", "value": "Phishing"},
        ],
    )

    EMAILPublisher().publish(preset)

    assert envelope.last.headers == [("X-Report-Category", "Ransomware"), ("X-Report-Category", "Phishing")]


@pytest.mark.parametrize("message_headers", [None, []])
def test_no_headers_sets_none_and_still_publishes(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
    message_headers: object,
) -> None:
    # None is the asset-notification path, where no presenter ran at all.
    _, status = EMAILPublisher().publish(email_preset(message_headers))

    assert status == HTTPStatus.OK
    assert envelope.last.headers == []
    assert envelope.last.sent


def test_a_hostile_presenter_cannot_add_a_recipient(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    """Defence in depth: the pair arrives pre-structured, bypassing the presenter's parser."""
    preset = email_preset(
        [
            {"name": "Bcc", "value": "attacker@evil.test"},
            {"name": "X-Report-Type", "value": "Advisory"},
        ],
    )

    _, status = EMAILPublisher().publish(preset)

    assert status == HTTPStatus.OK
    assert envelope.last.headers == [("X-Report-Type", "Advisory")]


def test_a_value_with_a_newline_is_scrubbed_before_the_envelope_sees_it(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    # EmailMessage.__setitem__ raises ValueError on CR/LF; we must never get that far.
    preset = email_preset([{"name": "X-Report-Category", "value": "Ransomware\r\nBcc: attacker@evil.test"}])

    EMAILPublisher().publish(preset)

    assert envelope.last.headers == [("X-Report-Category", "Ransomware Bcc: attacker@evil.test")]


def test_a_failing_header_call_does_not_cost_the_send(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    """A decorative header must never fail the publish.

    ``envelope.header()`` catches only ``TypeError``, and the publisher's own ``try``
    starts below the header loop, so anything else would escape ``publish()`` and become
    an unexplained 500.
    """
    preset = email_preset([{"name": "X-Report-Category", "value": "Ransomware"}])

    envelope_class = envelope
    original_init = envelope_class.__init__

    def init_with_failing_header(self: FakeEnvelope) -> None:
        original_init(self)
        self.header_error = ValueError("header values may not contain linefeed")

    envelope_class.__init__ = init_with_failing_header
    try:
        _, status = EMAILPublisher().publish(preset)
    finally:
        envelope_class.__init__ = original_init

    assert status == HTTPStatus.OK
    assert envelope.last.sent
