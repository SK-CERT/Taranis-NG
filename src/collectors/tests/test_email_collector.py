"""Tests for how the email collector turns a message into a news item.

The point of interest is the body: an email states its own format, and the collector has
to keep it - HTML as HTML, plain text with its line breaks intact - the way the RSS and
web collectors keep the formatting of what they fetch.

Emails are built with ``email.message.EmailMessage`` and re-parsed from bytes, so every
test runs through the same MIME and charset decoding the IMAP and POP3 fetchers do.
"""

from __future__ import annotations

import email
import hashlib
import types
from email import policy
from email.message import EmailMessage
from typing import TYPE_CHECKING

import pytest
from collectors.email_collector import EmailCollector

if TYPE_CHECKING:
    from collections.abc import Callable


class RecordingLogger:
    """Stand-in for the per-source logger, keeping what was logged for assertions."""

    def __init__(self) -> None:
        """Start with an empty record for every level a collector logs at."""
        self.messages: dict[str, list[str]] = {level: [] for level in ("debug", "info", "warning", "error", "exception")}

    def __getattr__(self, level: str) -> Callable[[str], None]:
        """Return a logging call for any level, recording what it is given."""

        def record(message: str) -> None:
            self.messages[level].append(str(message))

        return record


@pytest.fixture
def collector() -> EmailCollector:
    """An email collector wired to a fake source, ready to process messages."""
    instance = EmailCollector()
    instance.source = types.SimpleNamespace(id="source-1", name="test mailbox", logger=RecordingLogger(), word_lists=[])
    instance.news_items = []
    return instance


def build_email(*, plain: str | None = None, html: str | None = None, charset: str = "utf-8", **headers: str) -> EmailMessage:
    """Build a message and hand back what a fetcher would parse off the wire."""
    message = EmailMessage()
    message["Subject"] = headers.pop("subject", "Test subject")
    message["From"] = headers.pop("sender", "Sender Name <sender@example.com>")
    message["Message-ID"] = headers.pop("message_id", "<msg-1@example.com>")
    message["Date"] = headers.pop("date", "Tue, 01 Apr 2025 10:30:00 +0000")
    for name, value in headers.items():
        message[name] = value

    if plain is not None:
        message.set_content(plain, charset=charset)
    if html is not None:
        if plain is None:
            message.set_content(html, subtype="html", charset=charset)
        else:
            message.add_alternative(html, subtype="html", charset=charset)

    return email.message_from_bytes(message.as_bytes(), policy=policy.default)


def process(collector: EmailCollector, message: EmailMessage) -> list:
    """Run one message through the collector and return the news items it produced."""
    collector._EmailCollector__process_email(message)
    return collector.news_items


def test_html_body_keeps_its_markup(collector: EmailCollector) -> None:
    message = build_email(html="<html><body><p>An <strong>important</strong> advisory.</p></body></html>")

    (news_item,) = process(collector, message)

    assert news_item.content == "<p>An <strong>important</strong> advisory.</p>"
    # The review is the same text with the markup taken off.
    assert news_item.review == "An important advisory."


def test_html_only_email_is_collected(collector: EmailCollector) -> None:
    # Before, only text/plain was looked at, so an HTML-only email produced nothing at all.
    message = build_email(html="<p>HTML only</p>")

    assert len(process(collector, message)) == 1


def test_html_alternative_wins_over_plain_text(collector: EmailCollector) -> None:
    message = build_email(plain="Plain fallback", html="<p>The <em>rich</em> version</p>")

    (news_item,) = process(collector, message)

    assert news_item.content == "<p>The <em>rich</em> version</p>"
    assert "Plain fallback" not in news_item.content


def test_plain_text_body_keeps_its_line_breaks_and_indentation(collector: EmailCollector) -> None:
    message = build_email(plain="Affected products:\n  - Product A\n  - Product B\n")

    (news_item,) = process(collector, message)

    assert news_item.content.startswith("<pre>")
    assert "Affected products:\n  - Product A\n  - Product B" in news_item.content


def test_plain_text_body_keeps_a_bracketed_url(collector: EmailCollector) -> None:
    # Parsed rather than escaped, <https://...> reads as a tag and the URL vanishes.
    message = build_email(plain="Details at <https://example.com/advisory>")

    (news_item,) = process(collector, message)

    assert "&lt;https://example.com/advisory&gt;" in news_item.content


def test_table_layout_of_an_html_email_survives(collector: EmailCollector) -> None:
    message = build_email(html="<table><tr><td>CVE-2025-0001</td><td>Critical</td></tr></table>")

    (news_item,) = process(collector, message)

    assert "CVE-2025-0001" in news_item.content
    assert "Critical" in news_item.content


def test_tracking_markup_is_dropped_from_an_html_email(collector: EmailCollector) -> None:
    message = build_email(html='<div><style>p{color:red}</style><p>Body</p><img src="https://tracker.test/p.gif"></div>')

    (news_item,) = process(collector, message)

    assert "tracker.test" not in news_item.content
    assert "color:red" not in news_item.content
    assert "Body" in news_item.content


def test_non_utf8_body_is_decoded_with_its_declared_charset(collector: EmailCollector) -> None:
    message = build_email(plain="Přehled zranitelností", charset="iso-8859-2")

    (news_item,) = process(collector, message)

    assert "Přehled zranitelností" in news_item.content


def test_headers_become_the_news_item_metadata(collector: EmailCollector) -> None:
    message = build_email(plain="Body", subject="=?utf-8?q?Encoded_subject?=")

    (news_item,) = process(collector, message)

    assert news_item.title == "Encoded subject"
    # Parenthesised rather than "Name <address>", which sanitization would read as a tag.
    assert news_item.author == "Sender Name (sender@example.com)"
    assert news_item.source == "sender@example.com"
    assert news_item.published == "01.04.2025 - 10:30"


def test_sender_without_a_display_name_is_the_bare_address(collector: EmailCollector) -> None:
    message = build_email(plain="Body", sender="alerts@example.com")

    (news_item,) = process(collector, message)

    assert news_item.author == "alerts@example.com"
    assert news_item.source == "alerts@example.com"


def test_hash_is_unchanged_by_the_author_reformatting(collector: EmailCollector) -> None:
    # The hash is what stops an email being collected twice. It stays keyed on the raw
    # sender, subject and Message-ID, so upgrading does not re-import whole mailboxes.
    message = build_email(plain="Body")

    (news_item,) = process(collector, message)

    for_hash = "Sender Name <sender@example.com>" + "Test subject" + "<msg-1@example.com>"
    assert news_item.hash == hashlib.sha256(for_hash.encode()).hexdigest()


def test_email_without_a_date_is_still_collected(collector: EmailCollector) -> None:
    message = build_email(plain="Body")
    del message["Date"]

    (news_item,) = process(collector, message)

    assert news_item.published  # falls back to the time of collection


def test_email_without_a_body_is_still_collected(collector: EmailCollector) -> None:
    message = build_email(subject="No body at all")

    (news_item,) = process(collector, message)

    assert news_item.content == ""
    assert news_item.title == "No body at all"
    assert any("No text or HTML body" in warning for warning in collector.source.logger.messages["warning"])


def test_one_unprocessable_email_does_not_end_the_run(collector: EmailCollector, monkeypatch: pytest.MonkeyPatch) -> None:
    # Both fetchers hold the whole mailbox in one try block, so an email that raises used
    # to cost every email after it too.
    def explode(*_args: object, **_kwargs: object) -> None:
        message = "malformed"
        raise ValueError(message)

    monkeypatch.setattr(EmailCollector, "_EmailCollector__get_content", explode)
    collector._EmailCollector__process_email_safely(build_email(plain="Body"))

    assert collector.news_items == []
    assert any("Processing an email failed" in logged for logged in collector.source.logger.messages["exception"])


def test_a_broken_attached_email_does_not_lose_the_email_carrying_it(
    collector: EmailCollector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = EmailCollector._EmailCollector__get_content

    def fail_for_the_attached_one(self: EmailCollector, email_message: EmailMessage, title: str) -> str:
        if title == "Attached advisory":
            message = "malformed attachment"
            raise ValueError(message)
        return original(self, email_message, title)

    monkeypatch.setattr(EmailCollector, "_EmailCollector__get_content", fail_for_the_attached_one)

    attached = EmailMessage()
    attached["Subject"] = "Attached advisory"
    attached["From"] = "cert@example.org"
    attached["Date"] = "Tue, 01 Apr 2025 09:00:00 +0000"
    attached.set_content("Forwarded body")

    carrier = EmailMessage()
    carrier["Subject"] = "FW: advisory"
    carrier["From"] = "analyst@example.com"
    carrier["Message-ID"] = "<msg-3@example.com>"
    carrier["Date"] = "Tue, 01 Apr 2025 10:30:00 +0000"
    carrier.set_content("See the forwarded email.")
    carrier.add_attachment(attached, filename="advisory.eml")

    (news_item,) = process(collector, email.message_from_bytes(carrier.as_bytes(), policy=policy.default))

    assert news_item.title == "FW: advisory"
    assert "See the forwarded email." in news_item.content


def test_attachment_is_collected_alongside_an_html_body(collector: EmailCollector) -> None:
    message = EmailMessage()
    message["Subject"] = "With attachment"
    message["From"] = "sender@example.com"
    message["Message-ID"] = "<msg-2@example.com>"
    message["Date"] = "Tue, 01 Apr 2025 10:30:00 +0000"
    message.set_content("<p>See the attached report.</p>", subtype="html")
    message.add_attachment(b"%PDF-1.4 fake", maintype="application", subtype="pdf", filename="report.pdf")
    parsed = email.message_from_bytes(message.as_bytes(), policy=policy.default)

    (news_item,) = process(collector, parsed)

    assert "See the attached report." in news_item.content
    assert [attribute.key for attribute in news_item.attributes] == ["application/pdf"]
    assert news_item.attributes[0].value == "report.pdf"
