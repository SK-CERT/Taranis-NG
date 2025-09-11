"""Publisher for publishing by email."""

import mimetypes
from base64 import b64decode
from datetime import datetime
from pathlib import Path

from envelope import Envelope

from shared.common import TZ
from shared.config_publisher import ConfigPublisher
from shared.log_manager import logger

from .base_publisher import BasePublisher


class EMAILPublisher(BasePublisher):
    """This class represents a publisher that sends emails using SMTP server.

    Attributes:
        type (str): The type of the publisher.
        name (str): The name of the publisher.
        description (str): The description of the publisher.
        parameters (list): The list of parameters required for email publishing.

    Methods:
        publish(publisher_input): Publishes an email using the provided publisher input.
    """

    type = "EMAIL_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input: dict) -> None:
        """Publish an email using the provided publisher input.

        Parameters:
            publisher_input (PublisherInput): The input containing the parameters for the email publisher.

        Raises:
            Exception: If an error occurs while sending the email.
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        smtp_server = publisher_input.param_key_values["SMTP_SERVER"]
        smtp_server_port = publisher_input.param_key_values["SMTP_SERVER_PORT"]
        user = publisher_input.param_key_values["EMAIL_USERNAME"]
        password = publisher_input.param_key_values["EMAIL_PASSWORD"]
        sender = publisher_input.param_key_values["EMAIL_SENDER"]
        recipients = publisher_input.param_key_values["EMAIL_RECIPIENT"]
        subject = publisher_input.param_key_values["EMAIL_SUBJECT"]
        message = publisher_input.param_key_values["EMAIL_MESSAGE"]
        sign = publisher_input.param_key_values["EMAIL_SIGN"]
        sign_password = publisher_input.param_key_values["EMAIL_SIGN_PASSWORD"]
        encrypt = publisher_input.param_key_values["EMAIL_ENCRYPT"]

        smtp = {"host": smtp_server, "port": smtp_server_port, "user": user, "password": password}

        envelope = Envelope()

        # if attachment data available from presenter
        if publisher_input.mime_type and publisher_input.data:
            attachment_mimetype = publisher_input.mime_type
            attachment_extension = mimetypes.guess_extension(attachment_mimetype)
            attachment_data = publisher_input.data[:]
            file_name = ""
            if publisher_input.att_file_name:
                file_name = b64decode(publisher_input.att_file_name).decode("UTF-8").strip()
            if file_name == "":
                now = datetime.now(TZ).strftime("%Y%m%d%H%M%S")
                file_name = f"file_{now}"
            file_name = f"{file_name}{attachment_extension}"
            attachment_list = [
                (
                    b64decode(attachment_data),
                    attachment_mimetype,
                    file_name,
                    False,
                ),
            ]
            # it is possible to attach multiple files
            envelope.attach(attachment_list)

        # when title available from presenter
        if publisher_input.message_title:
            subject = b64decode(publisher_input.message_title).decode("UTF-8")
        # when body available from presenter
        if publisher_input.message_body:
            message = b64decode(publisher_input.message_body).decode("UTF-8")

        if not message:
            envelope.message(" ")
        else:
            envelope.message(message)
        if not subject:
            envelope.subject(" ")
        else:
            envelope.subject(subject)
        envelope.from_(sender)
        envelope.to(recipients)

        if sign == "auto":
            envelope.signature(key=sign)
        elif Path(sign).is_file():
            self.logger.info(f"Signing email with file {sign}")
            with Path(sign).open("r") as sign_file:
                envelope.signature(key=sign_file.read(), passphrase=sign_password)
        if encrypt == "auto":
            envelope.encryption(key=encrypt)
        elif Path(encrypt).is_file():
            self.logger.info(f"Encrypting email with file {encrypt}")
            with Path(encrypt).open("r") as encrypt_file:
                envelope.encryption(key=encrypt_file.read())

        email_string = str(envelope)
        max_length = 3000
        if len(email_string) > max_length:
            email_string = f"{email_string[:max_length]}\n..."
        self.logger.debug(f"=== COMPOSED FOLLOWING EMAIL ===\n{email_string}")

        envelope.smtp(smtp)
        try:
            sent = envelope.send()
            success = bool(sent)
            if success:
                self.logger.info("Email sent successfully")
                Envelope.smtp_quit()
            else:
                self.logger.critical("Email sending failed")

        except Exception as error:
            self.logger.exception(f"Publishing fail: {error}")
