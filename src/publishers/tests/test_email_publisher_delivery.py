"""What the email publisher actually puts on the wire.

The other two email suites replace ``envelope.Envelope`` with a fake, which is the right tool
for the publisher's own decisions but can only ever confirm what we *asked* the library to do.
That blind spot is how envelope 2.4.0 shipped here: it answered "sending failed" for messages
its SMTP server had accepted in full, and every test passed.

So these drive the real envelope over a stub ``smtplib.SMTP`` and assert on the delivered
message - the bytes the server was handed, re-parsed with ``email.policy.default``. That covers
the subject, the body and its declared type, the attachment, the custom headers and the SMTP
envelope, and it fails on a dependency regression of any shape rather than only the one we have
already met.

Signing and encryption stay with the fake-envelope suite in ``test_email_publisher_keys.py``:
``M2Crypto`` is installed in neither the test environment nor the publishers image, so S/MIME
cannot run here, and GPG would want a throwaway keyring per test.
"""

from __future__ import annotations

import re
import sys
from base64 import b64encode
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar

import pytest
from envelope import smtp_handler
from publishers.email_publisher import EMAILPublisher

if TYPE_CHECKING:
    from collections.abc import Callable
    from email.message import EmailMessage
    from email.message import Message as RawMessage


def encoded(text: str) -> str:
    """Base64, the way a presenter hands core a rendered title, body or file name."""
    return b64encode(text.encode()).decode()


class RecordingSMTP:
    """Stand-in for ``smtplib.SMTP``: opens no socket, refuses nobody, keeps the bytes.

    The publisher passes its SMTP settings as a dict, so the transport cannot be injected
    through the publisher's own interface - envelope builds it. Patching the name envelope
    resolves is the seam, and the state is class-level because the instance is created deep
    inside ``SMTPHandler.connect()``.
    """

    connected_to: ClassVar[tuple[str, int] | None] = None
    starttls_used: ClassVar[bool] = False
    credentials: ClassVar[tuple[str, str] | None] = None
    quit_called: ClassVar[bool] = False
    sent: ClassVar[list[tuple[str | None, list[str], bytes]]] = []
    # What the server rejects: {recipient: (code, reason)}, empty means it took everything.
    refuse: ClassVar[dict[str, tuple[int, bytes]]] = {}
    refuse_connection: ClassVar[bool] = False

    def __init__(self, host: str = "", port: int = 0, *_args: object, **_kwargs: object) -> None:
        """Take the arguments ``SMTPHandler.connect()`` passes (local_hostname, timeout) and connect to nothing."""
        if RecordingSMTP.refuse_connection:
            raise ConnectionRefusedError
        RecordingSMTP.connected_to = (host, port)

    def starttls(self, *_args: object, **_kwargs: object) -> None:
        """Upgrade the imaginary connection."""
        RecordingSMTP.starttls_used = True

    def login(self, user: str, password: str) -> None:
        """Authenticate, successfully, against nothing."""
        RecordingSMTP.credentials = (user, password)

    def send_message(self, msg: RawMessage, from_addr: str | None = None, to_addrs: list[str] | None = None) -> dict:
        """Serialise the message and report the refused recipients, as smtplib does."""
        RecordingSMTP.sent.append((from_addr, to_addrs or [], msg.as_bytes()))
        return dict(RecordingSMTP.refuse)

    def quit(self) -> None:
        """End the session."""
        RecordingSMTP.quit_called = True


@dataclass(frozen=True)
class Publication:
    """One call to ``publish()``: what it answered, and what the SMTP server saw."""

    status: HTTPStatus
    response: dict
    # None when nothing was ever handed to the server.
    message: EmailMessage | None
    # The SMTP envelope. `from_addr` is None: the publisher sets no envelope sender, so
    # smtplib derives MAIL FROM from the `From` header - assert on that instead.
    from_addr: str | None
    to_addrs: list[str]


@pytest.fixture
def smtp_server(monkeypatch: pytest.MonkeyPatch) -> type[RecordingSMTP]:
    """Put the stub transport under the real envelope."""
    RecordingSMTP.connected_to = None
    RecordingSMTP.starttls_used = False
    RecordingSMTP.credentials = None
    RecordingSMTP.quit_called = False
    RecordingSMTP.sent = []
    RecordingSMTP.refuse = {}
    RecordingSMTP.refuse_connection = False
    # SMTPHandler caches connections in a class-level dict keyed by the smtp settings, so
    # without this a neighbouring test's transport is reused instead of the one just built.
    smtp_handler.SMTPHandler._instances.clear()
    monkeypatch.setattr(smtp_handler, "SMTP", RecordingSMTP)
    return RecordingSMTP


@pytest.fixture
def publish(
    smtp_server: type[RecordingSMTP],
    email_preset: Callable[..., object],
) -> Callable[..., Publication]:
    """Publish an email preset and report what came out the other end.

    Returns:
        Callable: Takes the preset parameters and payload fields to override (see the
            ``email_preset`` fixture) and returns the resulting :class:`Publication`.
    """

    def _publish(**overrides: object) -> Publication:
        response, status = EMAILPublisher().publish(email_preset(**overrides))
        from_addr, to_addrs, raw = smtp_server.sent[-1] if smtp_server.sent else (None, [], None)
        return Publication(
            status=status,
            response=response,
            # Re-parsed rather than inspected in place: the default policy hands back raw
            # encoded words, and this is also the shape the receiving client would see.
            message=BytesParser(policy=policy.default).parsebytes(raw) if raw else None,
            from_addr=from_addr,
            to_addrs=to_addrs,
        )

    return _publish


# --------------------------------------------------------------------------- transport


def test_a_message_the_server_accepted_is_reported_as_sent(publish: Callable[..., Publication]) -> None:
    """The regression this suite exists for: an accepted message must not report failure."""
    publication = publish()

    assert publication.message is not None, "nothing reached the SMTP server"
    assert publication.status == HTTPStatus.OK, f"delivered message reported as failed: {publication.response}"
    assert publication.response == {"message": "Email sent successfully"}


def test_the_server_the_preset_names_is_the_one_we_talk_to(
    publish: Callable[..., Publication],
    smtp_server: type[RecordingSMTP],
) -> None:
    publish(SMTP_SERVER="mail.cert.example", SMTP_SERVER_PORT="2525")

    assert smtp_server.connected_to == ("mail.cert.example", 2525)


def test_the_session_is_encrypted_and_authenticated(
    publish: Callable[..., Publication],
    smtp_server: type[RecordingSMTP],
) -> None:
    """Port 587 is submission: STARTTLS, then the preset's credentials."""
    publish(SMTP_SERVER_PORT="587", EMAIL_USERNAME="taranis", EMAIL_PASSWORD="hunter2")

    assert smtp_server.starttls_used
    assert smtp_server.credentials == ("taranis", "hunter2")


def test_a_preset_without_credentials_does_not_authenticate(
    publish: Callable[..., Publication],
    smtp_server: type[RecordingSMTP],
) -> None:
    """The unauthenticated relay case, which is what the real presets here use."""
    publication = publish(SMTP_SERVER_PORT="25", EMAIL_USERNAME="", EMAIL_PASSWORD="")

    assert publication.status == HTTPStatus.OK
    assert smtp_server.credentials is None
    assert not smtp_server.starttls_used


def test_a_successful_send_closes_the_session(
    publish: Callable[..., Publication],
    smtp_server: type[RecordingSMTP],
) -> None:
    publish()

    assert smtp_server.quit_called


def test_an_unreachable_server_is_reported_as_failed(
    publish: Callable[..., Publication],
    smtp_server: type[RecordingSMTP],
) -> None:
    """The other direction: a send that never left must not be reported as sent."""
    smtp_server.refuse_connection = True

    publication = publish()

    assert publication.status == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "error" in publication.response
    assert smtp_server.sent == []


def test_a_refused_recipient_is_still_reported_as_sent(
    publish: Callable[..., Publication],
    smtp_server: type[RecordingSMTP],
) -> None:
    """A known limitation, pinned here so a future envelope changing it is noticed.

    envelope discards the mapping of recipients the server rejected - it only logs
    "Unable to send to all recipients" - so the publisher has nothing to report a partial
    delivery with, and answers OK. Fixing that means taking the SMTP conversation over from
    envelope, which is a decision, not a test change.
    """
    smtp_server.refuse = {"two@example.org": (550, b"5.1.1 no such user")}

    publication = publish(EMAIL_RECIPIENT="one@example.org, two@example.org")

    assert publication.status == HTTPStatus.OK


def test_every_preset_recipient_is_on_the_envelope(publish: Callable[..., Publication]) -> None:
    """A comma-separated preset field is several recipients, not one malformed address."""
    publication = publish(EMAIL_RECIPIENT="one@example.org, two@example.org")

    # envelope builds the recipient list from a set, so the order is not ours to expect.
    assert sorted(publication.to_addrs) == ["one@example.org", "two@example.org"]
    assert publication.message["To"] == "one@example.org, two@example.org"


# ---------------------------------------------------------------------- subject and body


def test_the_preset_subject_and_body_are_used_when_no_presenter_ran(publish: Callable[..., Publication]) -> None:
    publication = publish(EMAIL_SUBJECT="Security Warning", EMAIL_MESSAGE="See attached.")

    assert publication.message["Subject"] == "Security Warning"
    assert body_of(publication.message) == "See attached."


def test_the_presenter_overrides_the_preset_subject_and_body(publish: Callable[..., Publication]) -> None:
    publication = publish(
        EMAIL_SUBJECT="Security Warning",
        EMAIL_MESSAGE="See attached.",
        message_title=encoded("[TLP:CLEAR] Weekly report"),
        message_body=encoded("Three vulnerabilities were published."),
    )

    assert publication.message["Subject"] == "[TLP:CLEAR] Weekly report"
    assert body_of(publication.message) == "Three vulnerabilities were published."


def test_diacritics_survive_the_round_trip(publish: Callable[..., Publication]) -> None:
    """The reports here are Czech; a subject is encoded words by the time it is sent."""
    title = "Zranitelnost v Cisco ASA"
    body = "Cisco opravuje 8 zranitelností ve svých produktech."

    publication = publish(message_title=encoded(title), message_body=encoded(body))

    assert publication.message["Subject"] == title
    assert body_of(publication.message) == body


@pytest.mark.skipif(
    sys.version_info < (3, 13),
    reason=(
        "CPython below 3.13 drops the space where it folds a long non-ASCII header: the two "
        "halves become adjacent encoded words, and RFC 2047 says the whitespace between those "
        "is not text. Both CI (.github/python-version) and the image run 3.13, where it is fixed."
    ),
)
def test_a_long_subject_keeps_its_spaces_where_it_folds(publish: Callable[..., Publication]) -> None:
    """A real product title, long enough that the Subject header has to be folded."""
    title = "Cisco opravuje 8 zranitelností, jednu aktivně zneužívanou"

    publication = publish(message_title=encoded(title))

    assert publication.message["Subject"] == title


def test_an_empty_subject_and_body_still_send(publish: Callable[..., Publication]) -> None:
    """An unconfigured preset field must not cost the publication."""
    publication = publish(EMAIL_SUBJECT="", EMAIL_MESSAGE="")

    assert publication.status == HTTPStatus.OK
    assert publication.message is not None


def test_an_html_body_is_declared_as_html(publish: Callable[..., Publication]) -> None:
    """Without the declared type the client renders the markup as text."""
    publication = publish(
        message_body=encoded("<p>Three vulnerabilities were published.</p>"),
        message_body_mime_type="text/html",
    )

    html = publication.message.get_body(preferencelist=("html",))
    assert html is not None, "no text/html part in the delivered message"
    assert "<p>Three vulnerabilities were published.</p>" in html.get_content()


def test_a_body_without_a_declared_type_is_plain_text(publish: Callable[..., Publication]) -> None:
    """No presenter ran, so nothing declared a type; sniffing the body misreads "port <n>" as markup."""
    publication = publish(message_body=encoded("Listening on port <port_number>."), message_body_mime_type=None)

    assert publication.message.get_body(preferencelist=("plain",)).get_content_type() == "text/plain"


def test_a_notification_template_keeps_its_plain_text_subject(publish: Callable[..., Publication]) -> None:
    """Asset notifications carry no presenter, so their title and body arrive unencoded.

    Decoding them as base64 raised binascii.Error out of publish() as an unexplained 500.
    """
    publication = publish(
        message_title="Vulnerability found in your asset",
        message_body="A report item was completed for one of your assets.",
        mime_type=None,
        data=None,
    )

    assert publication.status == HTTPStatus.OK
    assert publication.message["Subject"] == "Vulnerability found in your asset"
    assert body_of(publication.message) == "A report item was completed for one of your assets."


def test_a_plain_word_that_looks_like_base64_is_left_alone(publish: Callable[..., Publication]) -> None:
    r"""A plain word can be valid base64: "Test" used to be delivered as b'M\xeb-'. It is not UTF-8, so it stays."""
    publication = publish(message_title="Test", message_body="Test")

    assert publication.message["Subject"] == "Test"
    assert body_of(publication.message) == "Test"


# ------------------------------------------------------------------------- attachment


def test_the_attachment_is_named_by_the_presenter_and_arrives_intact(publish: Callable[..., Publication]) -> None:
    publication = publish(
        mime_type="application/json",
        data=encoded('{"report": "test"}'),
        att_file_name=encoded("weekly report"),
    )

    attachment = only_attachment(publication.message)
    assert attachment.get_filename() == "weekly report.json"
    assert attachment.get_content_type() == "application/json"
    assert attachment.get_payload(decode=True) == b'{"report": "test"}'


def test_an_unnamed_attachment_falls_back_to_a_timestamp(publish: Callable[..., Publication]) -> None:
    """A product type with no file name template still has to produce a usable file."""
    publication = publish(att_file_name=None)

    assert re.fullmatch(r"file_\d{14}\.json", only_attachment(publication.message).get_filename())


def test_a_pdf_attachment_keeps_its_extension(publish: Callable[..., Publication]) -> None:
    publication = publish(mime_type="application/pdf", data=encoded("%PDF-1.4"), att_file_name=encoded("advisory"))

    assert only_attachment(publication.message).get_filename() == "advisory.pdf"


def test_a_publication_without_data_carries_no_attachment(publish: Callable[..., Publication]) -> None:
    """The notification path, where no presenter rendered anything to attach."""
    publication = publish(mime_type=None, data=None, message_body=encoded("An asset of yours is affected."))

    assert list(publication.message.iter_attachments()) == []
    assert publication.message.get_content_type() == "text/plain"


# ---------------------------------------------------------------------------- headers


def test_custom_headers_reach_the_wire_in_order(publish: Callable[..., Publication]) -> None:
    """Repeats included: that is how a headers template emits one line per value."""
    publication = publish(
        message_headers=[
            {"name": "X-Report-Category", "value": "Ransomware"},
            {"name": "X-Report-Category", "value": "Phishing"},
            {"name": "X-Report-Max-CVSS", "value": "9.8"},
        ],
    )

    assert publication.message.get_all("X-Report-Category") == ["Ransomware", "Phishing"]
    assert publication.message["X-Report-Max-CVSS"] == "9.8"


def test_a_hostile_bcc_header_does_not_reach_the_recipient_list(publish: Callable[..., Publication]) -> None:
    """The end-to-end form of the check in test_email_publisher_headers.py.

    ``envelope.header()`` reroutes bcc, cc and to into the real SMTP recipient list, so this
    is the assertion that matters: not that the header was dropped, but that nobody was added.
    """
    publication = publish(
        message_headers=[
            {"name": "Bcc", "value": "attacker@evil.test"},
            {"name": "X-Report-Type", "value": "Advisory"},
        ],
    )

    assert publication.to_addrs == ["constituency@example.org"]
    assert publication.message["Bcc"] is None
    assert publication.message["X-Report-Type"] == "Advisory"


def test_the_message_carries_the_headers_the_publisher_owns(publish: Callable[..., Publication]) -> None:
    """From, To, Date and Message-ID: a message missing these is spam to most filters."""
    publication = publish(EMAIL_SENDER="taranis@example.org", EMAIL_RECIPIENT="constituency@example.org")

    assert publication.message["From"] == "taranis@example.org"
    assert publication.message["To"] == "constituency@example.org"
    assert publication.message["Date"]
    assert publication.message["Message-ID"]


def body_of(message: EmailMessage) -> str:
    """Return the plain text part of a delivered message, decoded."""
    return message.get_body(preferencelist=("plain",)).get_content().rstrip("\n")


def only_attachment(message: EmailMessage) -> EmailMessage:
    """Return the single attachment of a delivered message."""
    attachments = list(message.iter_attachments())
    assert len(attachments) == 1, f"expected exactly one attachment, got {len(attachments)}"
    return attachments[0]
