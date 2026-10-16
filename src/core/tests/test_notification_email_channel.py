"""The e-mail channel speaks to the SMTP server the way its settings say, and says why it failed.

A fake SMTP server stands in for the network: these tests pin which connection each security
mode opens, when it logs in, what the message carries (an automatic message must say so, or
out-of-office replies bounce back to the sender), and that every failure comes back as a
readable ChannelError for the delivery log instead of an exception from smtplib.
"""

from __future__ import annotations

import smtplib
import ssl
from typing import Self

import pytest
from managers.notifications import channels
from managers.notifications.channels import ChannelError, EmailChannel

CONFIG = {
    "host": "smtp.example.test",
    "port": 587,
    "security": "starttls",
    "verify_tls": True,
    "username": "taranis",
    "from_address": "taranis@example.test",
    "from_name": "Taranis NG",
}


class FakeSMTP:
    """Records what a client did; raises what a test asks it to."""

    instances: list[FakeSMTP] = []  # noqa: RUF012 - reset by the fixture

    def __init__(self, host: str, port: int, timeout: float | None = None, context: ssl.SSLContext | None = None) -> None:
        """Connect (pretend)."""
        self.host, self.port, self.timeout, self.context = host, port, timeout, context
        self.calls: list[str] = []
        self.sent: list = []
        self.fail_with: Exception | None = None
        self.refused: dict = {}
        FakeSMTP.instances.append(self)
        if FakeSMTP.connect_error:
            raise FakeSMTP.connect_error

    connect_error: Exception | None = None

    def __enter__(self) -> Self:
        """Open the session."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Quit."""
        self.calls.append("quit")

    def starttls(self, context: ssl.SSLContext | None = None) -> None:
        """Upgrade to TLS."""
        self.calls.append("starttls")
        self.context = context

    def login(self, user: str, password: str) -> None:
        """Authenticate."""
        self.calls.append(f"login:{user}:{password}")
        if FakeSMTP.login_error:
            raise FakeSMTP.login_error

    login_error: Exception | None = None

    def send_message(self, message: object) -> dict:
        """Hand over the message."""
        self.calls.append("send")
        self.sent.append(message)
        return FakeSMTP.refused_recipients

    refused_recipients: dict = {}  # noqa: RUF012 - reset by the fixture


class FakeSMTPSSL(FakeSMTP):
    """SMTPS: TLS from the first byte."""


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    """Swap the network for the fake server."""
    FakeSMTP.instances = []
    FakeSMTP.connect_error = None
    FakeSMTP.login_error = None
    FakeSMTP.refused_recipients = {}
    monkeypatch.setattr(channels.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(channels.smtplib, "SMTP_SSL", FakeSMTPSSL)
    return FakeSMTP


def _send(config: dict | None = None, secret: str | None = "s3cret") -> FakeSMTP:  # noqa: S107 - a fake server's password
    EmailChannel.send(config or CONFIG, secret, "alice@example.test", "[Taranis NG] Passkey removed", "Hello Alice,\n")
    return FakeSMTP.instances[-1]


def test_starttls_upgrades_the_connection_before_logging_in() -> None:
    smtp = _send()

    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.example.test", 587, channels.SMTP_TIMEOUT)
    assert smtp.calls == ["starttls", "login:taranis:s3cret", "send", "quit"]
    assert smtp.context.verify_mode == ssl.CERT_REQUIRED


def test_ssl_opens_an_smtps_connection() -> None:
    smtp = _send({**CONFIG, "security": "ssl", "port": 465})

    assert isinstance(smtp, FakeSMTPSSL)
    assert "starttls" not in smtp.calls


def test_a_server_without_a_username_is_not_logged_in_to() -> None:
    smtp = _send({**CONFIG, "security": "none", "port": 25, "username": ""})

    assert smtp.calls == ["send", "quit"]


def test_certificate_checks_can_be_switched_off_for_an_internal_relay() -> None:
    smtp = _send({**CONFIG, "verify_tls": False})

    assert smtp.context.verify_mode == ssl.CERT_NONE
    assert smtp.context.check_hostname is False


def test_the_message_says_who_sent_it_and_that_nobody_should_reply_automatically() -> None:
    message = _send().sent[0]

    assert message["From"] == "Taranis NG <taranis@example.test>"
    assert message["To"] == "alice@example.test"
    assert message["Subject"] == "[Taranis NG] Passkey removed"
    assert message["Auto-Submitted"] == "auto-generated"
    assert message["X-Auto-Response-Suppress"] == "All"
    assert message["Message-ID"].endswith("@example.test>")
    assert message.get_content() == "Hello Alice,\n"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (smtplib.SMTPAuthenticationError(535, b"5.7.8 Bad credentials"), "SMTP login failed: 535 5.7.8 Bad credentials"),
        (ConnectionRefusedError(111, "Connection refused"), "Could not send through smtp.example.test:587"),
        (ssl.SSLError("certificate verify failed"), "Could not send through smtp.example.test:587"),
    ],
)
def test_failures_come_back_as_readable_channel_errors(error: Exception, expected: str) -> None:
    if isinstance(error, smtplib.SMTPAuthenticationError):
        FakeSMTP.login_error = error
    else:
        FakeSMTP.connect_error = error

    with pytest.raises(ChannelError, match=expected):
        _send()


def test_a_refused_recipient_is_a_failure() -> None:
    FakeSMTP.refused_recipients = {"alice@example.test": (550, b"No such user")}

    with pytest.raises(ChannelError, match="Recipient refused"):
        _send()


def test_settings_are_normalized_with_the_port_of_the_security_mode() -> None:
    config = EmailChannel.validate({"host": " smtp.example.test ", "security": "SSL", "from_address": "taranis@example.test"})

    assert config == {
        "host": "smtp.example.test",
        "port": 465,
        "security": "ssl",
        "verify_tls": True,
        "username": "",
        "from_address": "taranis@example.test",
        "from_name": "",
    }


@pytest.mark.parametrize(
    "bad",
    [
        {"host": "", "from_address": "taranis@example.test"},
        {"host": "smtp.example.test", "from_address": "not an address"},
        {"host": "smtp.example.test", "from_address": "taranis@example.test", "port": 70000},
        {"host": "smtp.example.test", "from_address": "taranis@example.test", "security": "tls13"},
        {"host": "smtp.example.test", "from_address": "taranis@example.test", "from_name": "Taranis\r\nBcc: x@y.z"},
    ],
)
def test_settings_that_cannot_work_or_would_inject_headers_are_refused(bad: dict) -> None:
    with pytest.raises(ValueError, match=r".+"):
        EmailChannel.validate(bad)


@pytest.mark.parametrize(
    ("email", "address"),
    [("alice@example.test", "alice@example.test"), (" alice@example.test ", "alice@example.test"), (None, None), ("", None), ("alice", None)],
)
def test_only_a_user_with_a_usable_address_can_be_reached(email: str | None, address: str | None) -> None:
    assert EmailChannel.address_for(type("User", (), {"email": email})()) == address
