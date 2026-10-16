"""Ways of delivering a notification to a user.

Each kind of channel knows how to validate its settings, where a user is reached on it, and how
to send one message. Only e-mail exists so far; ntfy, Matrix or Mattermost register a subclass in
``CHANNELS`` and give users an address on that service.
"""

from __future__ import annotations

import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from model.user import User

# Plenty for an SMTP dialogue; a dead server must not hold a sender for long.
SMTP_TIMEOUT = 15

SECURITY_MODES = ("none", "starttls", "ssl")
DEFAULT_PORTS = {"none": 25, "starttls": 587, "ssl": 465}
MAX_PORT = 65535
MAX_NAME_LENGTH = 100

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LINE_BREAK_RE = re.compile(r"[\r\n]")


class ChannelError(Exception):
    """A message could not be delivered; the text says why, for the delivery log."""


class Channel:
    """A kind of notification channel."""

    kind: ClassVar[str] = ""

    @classmethod
    def validate(cls, config: dict) -> dict:
        """Check and normalize the settings an administrator entered.

        Raises:
            ValueError: With a message for the administrator.
        """
        raise NotImplementedError

    @classmethod
    def address_for(cls, user: User) -> str | None:
        """Where the user is reached on this channel, or None when they cannot be."""
        raise NotImplementedError

    @classmethod
    def send(cls, config: dict, secret: str | None, recipient: str, subject: str, body: str) -> None:
        """Deliver one message.

        Raises:
            ChannelError: When it was not delivered.
        """
        raise NotImplementedError


def _single_line(value: object, field: str, max_length: int | None = None) -> str:
    text = str(value or "").strip()
    if LINE_BREAK_RE.search(text):
        msg = f"{field} must be a single line"
        raise ValueError(msg)
    if max_length is not None and len(text) > max_length:
        msg = f"{field} is too long"
        raise ValueError(msg)
    return text


def is_email_address(value: str | None) -> bool:
    """Tell whether a value looks like an e-mail address that can be put in a header."""
    return bool(value) and bool(EMAIL_RE.match(value)) and not LINE_BREAK_RE.search(value)


class EmailChannel(Channel):
    """E-mail through an SMTP server."""

    kind = "email"

    @classmethod
    def validate(cls, config: dict) -> dict:
        """Check the SMTP settings.

        Args:
            config (dict): host, port, security, verify_tls, username, from_address, from_name.

        Returns:
            dict: The settings, normalized.

        Raises:
            ValueError: With a message for the administrator.
        """
        host = _single_line(config.get("host"), "SMTP server")
        if not host or " " in host:
            msg = "SMTP server is required"
            raise ValueError(msg)
        security = str(config.get("security") or "starttls").strip().lower()
        if security not in SECURITY_MODES:
            msg = f"Security must be one of: {', '.join(SECURITY_MODES)}"
            raise ValueError(msg)
        port = config.get("port") or DEFAULT_PORTS[security]
        try:
            port = int(port)
        except (TypeError, ValueError):
            port = 0
        if not 1 <= port <= MAX_PORT:
            msg = "Port must be a number between 1 and 65535"
            raise ValueError(msg)
        from_address = _single_line(config.get("from_address"), "Sender address")
        if not is_email_address(from_address):
            msg = "Sender address must be an e-mail address"
            raise ValueError(msg)
        return {
            "host": host,
            "port": port,
            "security": security,
            "verify_tls": config.get("verify_tls", True) is not False,
            "username": _single_line(config.get("username"), "Username"),
            "from_address": from_address,
            "from_name": _single_line(config.get("from_name"), "Sender name", MAX_NAME_LENGTH),
        }

    @classmethod
    def address_for(cls, user: User) -> str | None:
        """The user's e-mail address, when they have a usable one."""
        address = (getattr(user, "email", None) or "").strip()
        return address if is_email_address(address) else None

    @classmethod
    def build_message(cls, config: dict, recipient: str, subject: str, body: str) -> EmailMessage:
        """Assemble the message: plain text, marked as automatically generated."""
        message = EmailMessage()
        from_address = config["from_address"]
        message["From"] = formataddr((config.get("from_name") or "", from_address))
        message["To"] = recipient
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=from_address.rsplit("@", 1)[-1])
        # RFC 3834: no auto-replies to this, and Exchange's equivalent.
        message["Auto-Submitted"] = "auto-generated"
        message["X-Auto-Response-Suppress"] = "All"
        message.set_content(body)
        return message

    @classmethod
    def send(cls, config: dict, secret: str | None, recipient: str, subject: str, body: str) -> None:
        """Send one e-mail.

        Raises:
            ChannelError: Naming what went wrong (connection, TLS, login, refused recipient).
        """
        message = cls.build_message(config, recipient, subject, body)
        context = ssl.create_default_context()
        if not config.get("verify_tls", True):
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        host, port, security = config["host"], int(config["port"]), config.get("security", "starttls")
        try:
            if security == "ssl":
                smtp = smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT, context=context)
            else:
                smtp = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT)
            with smtp:
                if security == "starttls":
                    smtp.starttls(context=context)
                if config.get("username"):
                    smtp.login(config["username"], secret or "")
                refused = smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as error:
            msg = f"SMTP login failed: {error.smtp_code} {_decode(error.smtp_error)}"
            raise ChannelError(msg) from error
        except smtplib.SMTPRecipientsRefused as error:
            msg = f"Recipient refused: {recipient}"
            raise ChannelError(msg) from error
        except smtplib.SMTPResponseException as error:
            msg = f"SMTP error: {error.smtp_code} {_decode(error.smtp_error)}"
            raise ChannelError(msg) from error
        except (smtplib.SMTPException, ssl.SSLError, OSError) as error:
            msg = f"Could not send through {host}:{port}: {error}"
            raise ChannelError(msg) from error
        if refused:
            msg = f"Recipient refused: {recipient}"
            raise ChannelError(msg)


def _decode(value: bytes | str) -> str:
    return value.decode(errors="replace") if isinstance(value, bytes) else str(value)


CHANNELS: dict[str, type[Channel]] = {EmailChannel.kind: EmailChannel}
