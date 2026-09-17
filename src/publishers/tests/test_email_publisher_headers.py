"""Custom mail headers a presenter asks the email publisher to set.

The presenter that renders these is a separate node reached over the network, so its
output is untrusted input here. ``envelope.header()`` reroutes ``bcc``, ``cc`` and ``to``
to its own setters, and the SMTP recipient list is built from those - so a header this
publisher accepts without checking could add a recipient. These assert that it checks.

They work against the ``FakeEnvelope`` in conftest, which answers what the publisher
*asked* for. That the headers then survive to the wire is asserted end to end in
``test_email_publisher_delivery.py``.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from publishers.email_publisher import EMAILPublisher

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import FakeEnvelope


def test_every_header_reaches_the_envelope_in_order(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    preset = email_preset(
        message_headers=[
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
        message_headers=[
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
    _, status = EMAILPublisher().publish(email_preset(message_headers=message_headers))

    assert status == HTTPStatus.OK
    assert envelope.last.headers == []
    assert envelope.last.sent


def test_a_hostile_presenter_cannot_add_a_recipient(
    email_preset: Callable[..., object],
    envelope: type[FakeEnvelope],
) -> None:
    """Defence in depth: the pair arrives pre-structured, bypassing the presenter's parser."""
    preset = email_preset(
        message_headers=[
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
    preset = email_preset(message_headers=[{"name": "X-Report-Category", "value": "Ransomware\r\nBcc: attacker@evil.test"}])

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
    preset = email_preset(message_headers=[{"name": "X-Report-Category", "value": "Ransomware"}])
    envelope.header_error = ValueError("header values may not contain linefeed")

    _, status = EMAILPublisher().publish(preset)

    assert status == HTTPStatus.OK
    assert envelope.last.sent
