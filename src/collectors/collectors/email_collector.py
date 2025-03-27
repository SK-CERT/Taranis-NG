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
from shared import common
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

        def proxy_tunnel(parsed_proxy, email_server_hostname, email_server_port):
            logger.debug(f"{self.collector_source} Establishing proxy tunnel")
            server = f"{email_server_hostname.lower()}"
            port = email_server_port

            proxy = (f"{parsed_proxy.scheme}://{parsed_proxy.hostname}", parsed_proxy.port)
            con = f"CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n"

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
            attributes = []

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
                    review = common.smart_truncate(content)

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
                    match binary_mime_type:
                        case "message/rfc822":
                            logger.debug(f"{self.collector_source} Found an attached email")
                            attached = part.get_payload()
                            if isinstance(attached, list):
                                attached_email = attached[0]
                            else:
                                attached_email = attached
                            # Process .eml file as an email
                            process_email(attached_email)

                        case "application/pkcs7-signature" | "application/x-pkcs7-signature":
                            logger.debug(f"{self.collector_source} Found a X.509 signature attachment")
                            # binary_value = part.get_payload()
                            # Skip signature attachments for now
                            continue

                        case "application/pgp-signature":
                            logger.debug(f"{self.collector_source} Found a PGP signature attachment")
                            # binary_value = part.get_payload()
                            # Skip signature attachments for now
                            continue

                        case _:
                            # Handle other binary attachments
                            if file_name:
                                logger.debug(f"{self.collector_source} Found an attachment '{file_name}' with MIME type '{binary_mime_type}'")
                                binary_value = part.get_payload()
                                if binary_value:
                                    news_attribute = NewsItemAttribute(binary_mime_type, file_name, binary_mime_type, binary_value)
                                    news_item.attributes.append(news_attribute)
                                else:
                                    logger.error(f"{self.collector_source} Attachment is empty or could not be decoded: {file_name}")

                news_items.append(news_item)

        def fetch_emails_imap(
            email_server_hostname, email_server_port, email_username, email_password, email_sender_address, emails_limit, proxy_server=None
        ):
            logger.debug(f"{self.collector_source} Fetching emails using IMAP")
            try:
                if parsed_proxy:
                    proxy_tunnel(parsed_proxy, email_server_hostname, email_server_port)

                connection = imaplib.IMAP4_SSL(email_server_hostname.lower(), email_server_port)
                connection.login(email_username, email_password)
                connection.select("inbox")

                if email_sender_address not in ["", None]:
                    typ, data = connection.search(None, "FROM", f'"{email_sender_address}"')
                else:
                    typ, data = connection.search(None, "ALL")

                if typ != "OK":
                    logger.error(f"{self.collector_source} Failed to search emails {typ}")

                email_uids = data[0].split()
                total_emails = len(email_uids)

                if emails_limit in ["", None] or emails_limit > total_emails:
                    emails_limit = total_emails
                start_index = max(0, total_emails - emails_limit)
                email_uids_to_process = email_uids[start_index:total_emails]
                for uid in email_uids_to_process:
                    typ, email_data = connection.fetch(uid, "(RFC822)")
                    raw_email = email_data[0][1]
                    raw_email_string = raw_email.decode("utf-8")
                    email_message = email.message_from_string(raw_email_string, policy=policy.default)
                    process_email(email_message)

                connection.close()
                connection.logout()
            except Exception as error:
                logger.exception(f"{self.collector_source} Failed to fetch emails using IMAP: {error}")

        def fetch_emails_pop3(
            email_server_hostname, email_server_port, email_username, email_password, email_sender_address, emails_limit, parsed_proxy
        ):
            logger.debug(f"{self.collector_source} Fetching emails using POP3")
            try:
                if parsed_proxy:
                    proxy_tunnel(parsed_proxy, email_server_hostname, email_server_port)

                connection = poplib.POP3_SSL(email_server_hostname.lower(), email_server_port)
                connection.user(email_username)
                connection.pass_(email_password)

                num_messages = len(connection.list()[1])

                if emails_limit in ["", None] or emails_limit > num_messages:
                    emails_limit = num_messages  # Process all emails if emails_limit is not provided

                processed_emails = 0
                for i in range(num_messages, 0, -1):  # emails are listed in reverse order
                    if processed_emails < emails_limit:
                        raw_email = b"\n".join(connection.retr(i + 1)[1])
                        email_message = email.message_from_bytes(raw_email)
                        if email_sender_address not in ["", None]:
                            sender_from_email = email.utils.parseaddr(email_message["From"])
                            if email_sender_address in sender_from_email:
                                processed_emails += 1
                                logger.debug(f"Sender email address matches: {email_sender_address} = {sender_from_email}")
                                process_email(email_message)
                        else:
                            process_email(email_message)

                connection.quit()
            except Exception as error:
                logger.exception(f"{self.collector_source} Failed to fetch emails using POP3: {error}")

        news_items = []
        email_server_type = source.parameter_values["EMAIL_SERVER_TYPE"]
        email_server_hostname = source.parameter_values["EMAIL_SERVER_HOSTNAME"]
        email_server_port = source.parameter_values["EMAIL_SERVER_PORT"]
        email_username = source.parameter_values["EMAIL_USERNAME"]
        email_password = source.parameter_values["EMAIL_PASSWORD"]
        parsed_proxy = BaseCollector.get_parsed_proxy(source.parameter_values["PROXY_SERVER"], self.collector_source)
        email_sender_address = source.parameter_values["EMAIL_SENDER"]
        emails_limit = int(source.parameter_values["EMAILS_LIMIT"])

        if email_server_type.casefold() == "imap":
            fetch_emails_imap(
                email_server_hostname, email_server_port, email_username, email_password, email_sender_address, emails_limit, parsed_proxy
            )
        elif email_server_type.casefold() == "pop3":
            fetch_emails_pop3(
                email_server_hostname, email_server_port, email_username, email_password, email_sender_address, emails_limit, parsed_proxy
            )
        else:
            logger.error(f"{self.collector_source} Email server connection type is not supported: {email_server_type}")

        BaseCollector.publish(news_items, source, self.collector_source)
