"""Publisher for publishing by email."""

from datetime import datetime
from base64 import b64decode
import os
from managers.log_manager import logger
from .base_publisher import BasePublisher
from shared.schema.parameter import Parameter, ParameterType
from envelope import Envelope
import mimetypes


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
    name = "EMAIL Publisher"
    description = "Publisher for publishing by email"

    parameters = [
        Parameter(0, "SMTP_SERVER", "SMTP server", "SMTP server for sending emails", ParameterType.STRING),
        Parameter(0, "SMTP_SERVER_PORT", "SMTP server port", "SMTP server port for sending emails", ParameterType.STRING),
        Parameter(0, "EMAIL_USERNAME", "Email username", "Username for email account", ParameterType.STRING),
        Parameter(0, "EMAIL_PASSWORD", "Email password", "Password for email account", ParameterType.STRING),
        Parameter(0, "EMAIL_SENDER", "Email sender", "Email address of the sender", ParameterType.STRING),
        Parameter(0, "EMAIL_RECIPIENT", "Email recipient", "Email address of the recipient", ParameterType.STRING),
        Parameter(0, "EMAIL_SUBJECT", "Email subject", "Text of email subject", ParameterType.STRING),
        Parameter(0, "EMAIL_MESSAGE", "Email message", "Text of email message", ParameterType.STRING),
        Parameter(0, "EMAIL_SIGN", "Email signature", "File used for signing or auto", ParameterType.STRING),
        Parameter(0, "EMAIL_SIGN_PASSWORD", "Email signature password", "Password for signing file", ParameterType.STRING),
        Parameter(0, "EMAIL_ENCRYPT", "Email encryption", "File used for encryption or auto", ParameterType.STRING),
    ]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):
        """Publish an email using the provided publisher input.

        Parameters:
            publisher_input (PublisherInput): The input containing the parameters for the email publisher.

        Returns:
            bool: True if the email was sent successfully, False otherwise.

        Raises:
            Exception: If an error occurs while sending the email.
        """
        smtp_server = publisher_input.parameter_values_map["SMTP_SERVER"]
        smtp_server_port = publisher_input.parameter_values_map["SMTP_SERVER_PORT"]
        user = publisher_input.parameter_values_map["EMAIL_USERNAME"]
        password = publisher_input.parameter_values_map["EMAIL_PASSWORD"]
        sender = publisher_input.parameter_values_map["EMAIL_SENDER"]
        recipients = publisher_input.parameter_values_map["EMAIL_RECIPIENT"]
        subject = publisher_input.parameter_values_map["EMAIL_SUBJECT"]
        message = publisher_input.parameter_values_map["EMAIL_MESSAGE"]
        sign = publisher_input.parameter_values_map["EMAIL_SIGN"]
        sign_password = publisher_input.parameter_values_map["EMAIL_SIGN_PASSWORD"]
        encrypt = publisher_input.parameter_values_map["EMAIL_ENCRYPT"]

        now = datetime.now().strftime("%Y%m%d%H%M%S")

        smtp = {"host": smtp_server, "port": smtp_server_port, "user": user, "password": password}

        envelope = Envelope()

        # if attachment data available from presenter
        if publisher_input.mime_type and publisher_input.data:
            attachment_mimetype = publisher_input.mime_type
            attachment_extension = mimetypes.guess_extension(attachment_mimetype)
            attachment_data = publisher_input.data[:]
            attachment_list = [
                (
                    b64decode(attachment_data),
                    attachment_mimetype,
                    f"file_{now}{attachment_extension}",
                    False,
                )
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
        elif os.path.isfile(sign):
            logger.info(f"Signing email with file {sign}")
            envelope.signature(key=open(sign), passphrase=sign_password)

        if encrypt == "auto":
            envelope.encryption(key=encrypt)
        elif os.path.isfile(encrypt):
            logger.info(f"Encrypting email with file {encrypt}")
            envelope.encryption(key=open(encrypt))

        logger.debug(f"=== COMPOSED FOLLOWING EMAIL ===\n{envelope}")

        envelope.smtp(smtp)
        try:
            sent = envelope.send()
            success = bool(sent)
            if success:
                logger.info("Email sent successfully")
                Envelope.smtp_quit()
            else:
                logger.critical("Email sending failed")

        except Exception as error:
            BasePublisher.print_exception(self, error)
