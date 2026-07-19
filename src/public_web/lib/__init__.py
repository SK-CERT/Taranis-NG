"""Public-web library utilities.

Common utilities and helpers for the public-web application.
"""

import logging
import traceback
from argparse import ArgumentParser

from envelope import Envelope
from lib.config_reader import ConfigReader

# Constants that can be anywhere in the lib directory.
IP_ADDRESS = str

config = ConfigReader()


def get_script_argument_parser() -> ArgumentParser:
    """Returns an argument parser with silent and debug options.

    Can be used in script such as rescan or process-incoming.
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--silent",
        action="store_true",
        help="do not print anything but errors to the standard output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="also log the debug outputs",
    )
    return parser


def send_mail(
    body: str,
    subject: str,
    recipients: list[str],
    logger: logging.Logger | None = None,
    sender: str = "public-web@localhost",
    force_send: bool = False,
    smtp: dict[str, str | int] | None = None,
) -> bool:
    """Send an email using Envelope.

    Sends an email with the given parameters, but only if the app
    is in production mode or force_send is True (send even in dev mode). Logs
    error output if it was unsuccessful.
    """
    if not (config.is_production() or force_send):
        info_message = (
            f"Development mode is enabled, this e-mail was not sent:\n"
            f"Recipients: {', '.join(recipients)}\n"
            f"Sender: {sender}\n"
            f"Subject: {subject}\n"
            f"Body: {body}"
        )
        # Development mode: log instead of sending email
        if logger:
            logger.info(info_message)
        else:
            print(info_message)  # noqa: T201
        return False

    envelope = Envelope()
    envelope.message(body or " ")
    envelope.subject(subject or " ")
    envelope.from_(sender)
    envelope.to(recipients)

    if smtp:
        envelope.smtp(smtp)

    try:
        sent = envelope.send()
        if not sent:
            error_message = f"Sending mail with subject '{subject}' to '{', '.join(recipients)}' failed."
            if logger:
                logger.error(error_message)
            else:
                print(error_message)  # noqa: T201
            return False
        return True
    except Exception:  # pylint: disable=locally-disabled, broad-exception-caught
        error_message = f"Sending mail with subject '{subject}' to '{', '.join(recipients)}' failed."
        if logger:
            logger.exception(error_message)
        else:
            print(error_message)  # noqa: T201
        return False


def handle_exception(
    message: str,
    subject: str,
    logger: logging.Logger | None = None,
    info: bool = True,  # noqa: ARG001
    force_send: bool = True,
) -> None:
    """Log the exception and send it via e-mail."""
    if logger:
        logger.exception(message)

    recipients = config.admin_mail()
    mail_message = f"{message}\n\n{traceback.format_exc()}"
    send_mail(mail_message, subject, recipients, logger, force_send=force_send)
