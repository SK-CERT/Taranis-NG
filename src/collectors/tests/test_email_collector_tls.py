"""The e-mail collector checks the mail server's certificate unless the source opts out.

``imaplib.IMAP4_SSL`` and ``poplib.POP3_SSL`` without a context use an unverified one (no
certificate check, no host name check): anyone on the network path could read the mailbox
password and the mail, and slip in mail that becomes news items. There was no timeout either,
so a server that stopped answering held the source's run forever.
"""

from __future__ import annotations

import collections
import ssl
import types
from typing import TYPE_CHECKING

import pytest
from collectors.email_collector import EmailCollector
from shared.schema.parameter import ParameterType

from collectors import email_collector

if TYPE_CHECKING:
    from collections.abc import Callable


class RecordingLogger:
    """Stand-in for the source logger: remembers what was logged at each level."""

    def __init__(self) -> None:
        """Start with nothing logged."""
        self.messages: dict[str, list[str]] = collections.defaultdict(list)

    def __getattr__(self, level: str) -> Callable[..., None]:
        """Any level is a method that records its message."""

        def record(message: str = "", *_args: object, **_kwargs: object) -> None:
            self.messages[level].append(str(message))

        return record


class FakeImap:
    """An IMAP server with an empty inbox."""

    def login(self, _username: str, _password: str) -> None:
        """Accept any account."""

    def select(self, _mailbox: str) -> None:
        """Open the inbox."""

    def search(self, _charset: object, *_criteria: str) -> tuple[str, list[bytes]]:
        """Find nothing."""
        return "OK", [b""]

    def close(self) -> None:
        """Close the inbox."""

    def logout(self) -> None:
        """End the session."""


class FakePop3:
    """A POP3 server with an empty mailbox."""

    def user(self, _username: str) -> None:
        """Accept any account."""

    def pass_(self, _password: str) -> None:
        """Accept any password."""

    def list(self) -> tuple[bytes, list[bytes], int]:
        """List nothing."""
        return b"+OK", [], 0

    def quit(self) -> None:
        """End the session."""


@pytest.fixture
def connections(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Record how each protocol class is asked to connect, without a network."""
    seen: list[dict] = []

    def imap(host: str, port: str, **options: object) -> FakeImap:
        seen.append({"protocol": "imap", "host": host, "port": port, **options})
        return FakeImap()

    def pop3(host: str, port: str, **options: object) -> FakePop3:
        seen.append({"protocol": "pop3", "host": host, "port": port, **options})
        return FakePop3()

    monkeypatch.setattr(email_collector.imaplib, "IMAP4_SSL", imap)
    monkeypatch.setattr(email_collector.poplib, "POP3_SSL", pop3)
    return seen


def collect(protocol: str, **parameters: str) -> EmailCollector:
    collector = EmailCollector()
    collector.source = types.SimpleNamespace(
        id="source-1",
        name="a mailbox",
        param_key_values=collections.defaultdict(
            str,
            {
                "EMAIL_SERVER_TYPE": protocol,
                "EMAIL_SERVER_HOSTNAME": "mail.example.org",
                "EMAIL_SERVER_PORT": "993" if protocol == "imap" else "995",
                "EMAIL_USERNAME": "reader@example.org",
                "EMAIL_PASSWORD": "s3cret-value",
                **parameters,
            },
        ),
        logger=RecordingLogger(),
        word_lists=[],
    )
    collector.publish = lambda _news_items: None
    collector.collect()
    return collector


@pytest.mark.parametrize("protocol", ["imap", "pop3"])
def test_the_certificate_and_host_name_are_checked_by_default(connections: list[dict], protocol: str) -> None:
    collector = collect(protocol)

    (connection,) = connections
    context = connection["ssl_context" if protocol == "imap" else "context"]
    assert connection["host"] == "mail.example.org"
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert collector.source.logger.messages["exception"] == []


@pytest.mark.parametrize("protocol", ["imap", "pop3"])
def test_a_source_can_opt_out(connections: list[dict], protocol: str) -> None:
    collect(protocol, IGNORE_TLS_ERRORS="true")

    (connection,) = connections
    context = connection["ssl_context" if protocol == "imap" else "context"]
    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False


@pytest.mark.parametrize("protocol", ["imap", "pop3"])
def test_a_server_that_stops_answering_times_out(connections: list[dict], protocol: str) -> None:
    collect(protocol)

    (connection,) = connections
    assert connection["timeout"] == email_collector.MAIL_SERVER_TIMEOUT
    assert 0 < email_collector.MAIL_SERVER_TIMEOUT <= 300


@pytest.mark.parametrize("protocol", ["imap", "pop3"])
def test_an_untrusted_certificate_is_reported_as_such(monkeypatch: pytest.MonkeyPatch, protocol: str) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        error = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate")
        error.verify_message = "self-signed certificate"  # set by the ssl module when the handshake fails
        raise error

    monkeypatch.setattr(email_collector.imaplib, "IMAP4_SSL", refuse)
    monkeypatch.setattr(email_collector.poplib, "POP3_SSL", refuse)

    messages = collect(protocol).source.logger.messages

    assert messages["error"] == [
        (
            "The mail server's TLS certificate is not trusted (self-signed certificate). "
            "Turn on 'Ignore TLS certificate errors' for this source only if that is expected"
        ),
    ]
    assert messages["exception"] == []
    assert "s3cret-value" not in repr(dict(messages))


def test_the_opt_out_is_a_parameter_of_the_e_mail_collector() -> None:
    (parameter,) = [parameter for parameter in EmailCollector.parameters if parameter.key == "IGNORE_TLS_ERRORS"]

    assert parameter.type == ParameterType.BOOLEAN
    assert parameter.default_value == "false"
