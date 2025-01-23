"""Module for email collector."""

import datetime
import hashlib
import uuid
import imaplib
import poplib
from email import policy
import email.header
import email.utils
import socket

from .base_collector import BaseCollector
from managers.log_manager import logger
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemData, NewsItemAttribute


class EmailCollector(BaseCollector):
    """Collector for gathering data from emails.

    Attributes:
        type (str): Type of the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (list): List of parameters required for the collector.
    Methods:
        collect(source): Collect data from email source.
    """

    type = "EMAIL_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    @BaseCollector.ignore_exceptions
    def collect(self, source):
        """Collect data from email source.

        Parameters:
            source -- Source object.
        """
        news_items = []
        email_server_type = source.parameter_values["EMAIL_SERVER_TYPE"]
        email_server_hostname = source.parameter_values["EMAIL_SERVER_HOSTNAME"]
        email_server_port = source.parameter_values["EMAIL_SERVER_PORT"]
        email_username = source.parameter_values["EMAIL_USERNAME"]
        email_password = source.parameter_values["EMAIL_PASSWORD"]
        proxy_server = source.parameter_values["PROXY_SERVER"]

        def proxy_tunnel():
            logger.debug(f"{self.collector_source} Establishing proxy tunnel")
            server = f"{email_server_hostname.lower()}"
            port = email_server_port

            server_proxy = proxy_server.rsplit(":", 1)[0]
            server_proxy_port = proxy_server.rsplit(":", 1)[-1]

            proxy = (str(server_proxy), int(server_proxy_port))
            con = f"CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n"

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(proxy)
            s.send(str.encode(con))
            s.recv(4096)

        def process_email(email_message):
            email_string = email_message.as_string()
            if len(email_string) > 3000:
                email_string = f"{email_string[:3000]}\n..."
            logger.debug(f"{self.collector_source} Processing email: {email_string}")
            review = ""
            content = ""
            address = ""
            link = ""
            news_item = None

            title = str(email.header.make_header(email.header.decode_header(email_message["Subject"])))
            logger.debug(f"{self.collector_source} Processing email: {title}")
            author = str(email.header.make_header(email.header.decode_header(email_message["From"])))
            address = email.utils.parseaddr(email_message["From"])[1]
            message_id = str(email.header.make_header(email.header.decode_header(email_message["Message-ID"])))
            date_tuple = email.utils.parsedate_tz(email_message["Date"])
            published = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple)).strftime("%d.%m.%Y - %H:%M")

            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    charset = part.get_content_charset()
                    logger.debug(f"{self.collector_source} Detected encoding of email '{title}': {charset}")
                    text_data = part.get_payload(decode=True)
                    if charset is None:
                        charset = "utf-8"
                    content = text_data.decode(charset)
                    review = content[:500]

                    for_hash = author + title + message_id

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        title,
                        review,
                        address,
                        link,
                        published,
                        author,
                        datetime.datetime.now(),
                        content,
                        source.id,
                        attributes,
                    )
                    break

            if news_item:
                for part in email_message.walk():
                    file_name = part.get_filename()
                    binary_mime_type = part.get_content_type()
                    if binary_mime_type == "message/rfc822":
                        logger.debug(f"{self.collector_source} Found an attached email")
                        attached = part.get_payload()
                        if isinstance(attached, list):
                            attached_email = attached[0]
                        else:
                            attached_email = attached
                        # Process .eml file as an email
                        process_email(attached_email)

                    elif binary_mime_type == "application/pkcs7-signature" or binary_mime_type == "application/x-pkcs7-signature":
                        logger.debug(f"{self.collector_source} Found a X.509 signature attachment")
                        # Skip signature attachments
                        continue

                    elif binary_mime_type == "application/pgp-signature":
                        logger.debug(f"{self.collector_source} Found a PGP signature attachment")
                        binary_value = part.get_payload()
                        # Skip signature attachments
                        continue

                    elif file_name:
                        # Handle other binary attachments
                        logger.debug(f"{self.collector_source} Found an attachment '{file_name}' with MIME type '{binary_mime_type}'")
                        binary_value = part.get_payload()
                        if binary_value:
                            news_attribute = NewsItemAttribute(binary_mime_type, file_name, binary_mime_type, binary_value)
                            news_item.attributes.append(news_attribute)
                        else:
                            logger.error(f"{self.collector_source} Attachment is empty or could not be decoded: {file_name}")

                news_items.append(news_item)

        if email_server_type.lower() == "imap":
            logger.debug(f"{self.collector_source} Fetching emails using IMAP")
            try:
                if proxy_server:
                    proxy_tunnel()

                connection = imaplib.IMAP4_SSL(email_server_hostname.lower(), email_server_port)
                connection.login(email_username, email_password)
                connection.select("inbox")

                result, data = connection.uid("search", None, "UNSEEN")
                i = len(data[0].split())

                for x in range(i):
                    attributes = []
                    latest_email_uid = data[0].split()[x]
                    result, email_data = connection.uid("fetch", latest_email_uid, "(RFC822)")
                    raw_email = email_data[0][1]
                    raw_email_string = raw_email.decode("utf-8")
                    email_message = email.message_from_string(raw_email_string, policy=policy.default)

                    process_email(email_message)

                connection.close()
                connection.logout()
            except Exception as error:
                logger.exception(f"{self.collector_source} Failed to fetch emails using IMAP: {error}")

        elif email_server_type.lower() == "pop3":
            logger.debug(f"{self.collector_source} Fetching emails using POP3")
            try:
                if proxy_server:
                    proxy_tunnel()

                connection = poplib.POP3_SSL(email_server_hostname.lower(), email_server_port)
                connection.user(email_username)
                connection.pass_(email_password)

                num_messages = len(connection.list()[1])

                for i in range(num_messages):
                    attributes = []

                    raw_email = b"\n".join(connection.retr(i + 1)[1])
                    email_message = email.message_from_bytes(raw_email)

                    process_email(email_message)

                connection.quit()
            except Exception as error:
                logger.exception(f"{self.collector_source} Failed to fetch emails using POP3: {error}")
        else:
            logger.error(f"{self.collector_source} Email server connection type is not supported: {email_server_type}")

        BaseCollector.publish(news_items, source, self.collector_source)
