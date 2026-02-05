"""Module for email collector."""

import datetime
import email.header
import email.utils
import hashlib
import imaplib
import poplib
import socket
import uuid
from email import policy

from shared.common import ignore_exceptions, read_int_parameter, smart_truncate
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemAttribute, NewsItemData

from .base_collector import BaseCollector


class EmailCollector(BaseCollector):
    """Collector for gathering data from emails.

    Attributes:
        type (str): Type of the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (list): List of parameters required for the collector.

    Methods:
        collect(): Collect data from email source.
    """

    type = "EMAIL_COLLECTOR"
    config = ConfigCollector().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def __proxy_tunnel(self, email_server_hostname, email_server_port):
        self.source.logger.debug("Establishing proxy tunnel")
        server = f"{email_server_hostname.lower()}"
        port = email_server_port

        proxy = (f"{self.source.parsed_proxy.scheme}://{self.source.parsed_proxy.hostname}", self.source.parsed_proxy.port)
        con = f"CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(proxy)
            s.send(str.encode(con))
            s.recv(4096)

    def __fetch_emails_imap(self):
        self.source.logger.debug("Fetching emails using IMAP")
        try:
            if self.source.parsed_proxy:
                self.__proxy_tunnel(self.email_server_hostname, self.email_server_port)

            connection = imaplib.IMAP4_SSL(self.email_server_hostname.lower(), self.email_server_port)
            connection.login(self.email_username, self.email_password)
            connection.select("inbox")

            if self.email_sender_address not in ["", None]:
                typ, data = connection.search(None, "FROM", f'"{self.email_sender_address}"')
            else:
                typ, data = connection.search(None, "ALL")

            if typ != "OK":
                self.source.logger.error(f"Failed to search emails {typ}")

            email_uids = data[0].split()
            total_emails = len(email_uids)

            if self.emails_limit in ["", None] or self.emails_limit > total_emails:
                self.emails_limit = total_emails
            start_index = max(0, total_emails - self.emails_limit)
            email_uids_to_process = email_uids[start_index:total_emails]
            for uid in email_uids_to_process:
                typ, email_data = connection.fetch(uid, "(RFC822)")
                raw_email = email_data[0][1]
                raw_email_string = raw_email.decode("utf-8")
                email_message = email.message_from_string(raw_email_string, policy=policy.default)
                self.__process_email(email_message)

            connection.close()
            connection.logout()
        except Exception as error:
            self.source.logger.exception(f"Failed to fetch emails using IMAP: {error}")

    def __fetch_emails_pop3(self):
        self.source.logger.debug("Fetching emails using POP3")
        try:
            if self.source.parsed_proxy:
                self.__proxy_tunnel(self.email_server_hostname, self.email_server_port)

            connection = poplib.POP3_SSL(self.email_server_hostname.lower(), self.email_server_port)
            connection.user(self.email_username)
            connection.pass_(self.email_password)

            num_messages = len(connection.list()[1])

            if self.emails_limit in ["", None] or self.emails_limit > num_messages:
                self.emails_limit = num_messages  # Process all emails if emails_limit is not provided

            processed_emails = 0
            for i in range(num_messages, 0, -1):  # emails are listed in reverse order
                if processed_emails < self.emails_limit:
                    raw_email = b"\n".join(connection.retr(i + 1)[1])
                    email_message = email.message_from_bytes(raw_email)
                    if self.email_sender_address not in ["", None]:
                        sender_from_email = email.utils.parseaddr(email_message["From"])
                        if self.email_sender_address in sender_from_email:
                            processed_emails += 1
                            self.source.logger.debug(f"Sender email address matches: {self.email_sender_address} = {sender_from_email}")
                            self.__process_email(email_message)
                    else:
                        self.__process_email(email_message)

            connection.quit()
        except Exception as error:
            self.source.logger.exception(f"Failed to fetch emails using POP3: {error}")

    def __process_email(self, email_message):
        email_string = email_message.as_string()
        if len(email_string) > 3000:
            email_string = f"{email_string[:3000]}\n..."
        self.source.logger.debug(f"Processing email: {email_string}")
        review = ""
        content = ""
        address = ""
        link = ""
        news_item = None
        attributes = []

        title = str(email.header.make_header(email.header.decode_header(email_message["Subject"])))
        self.source.logger.debug(f"Processing email: {title}")
        author = str(email.header.make_header(email.header.decode_header(email_message["From"])))
        address = email.utils.parseaddr(email_message["From"])[1]
        message_id = str(email.header.make_header(email.header.decode_header(email_message["Message-ID"])))
        date_tuple = email.utils.parsedate_tz(email_message["Date"])
        published = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date_tuple)).strftime("%d.%m.%Y - %H:%M")

        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset()
                self.source.logger.debug(f"Detected encoding of email '{title}': {charset}")
                text_data = part.get_payload(decode=True)
                if charset is None:
                    charset = "utf-8"
                content = text_data.decode(charset)
                review = smart_truncate(content)

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
                    self.source.id,
                    attributes,
                )
                break

        if news_item:
            for part in email_message.walk():
                file_name = part.get_filename()
                binary_mime_type = part.get_content_type()
                match binary_mime_type:
                    case "message/rfc822":
                        self.source.logger.debug("Found an attached email")
                        attached = part.get_payload()
                        if isinstance(attached, list):
                            attached_email = attached[0]
                        else:
                            attached_email = attached
                        # Process .eml file as an email
                        self.__process_email(attached_email)

                    case "application/pkcs7-signature" | "application/x-pkcs7-signature":
                        self.source.logger.debug("Found a X.509 signature attachment")
                        # binary_value = part.get_payload()
                        # Skip signature attachments for now
                        continue

                    case "application/pgp-signature":
                        self.source.logger.debug("Found a PGP signature attachment")
                        # binary_value = part.get_payload()
                        # Skip signature attachments for now
                        continue

                    case _:
                        # Handle other binary attachments
                        if file_name:
                            self.source.logger.debug(f"Found an attachment '{file_name}' with MIME type '{binary_mime_type}'")
                            binary_value = part.get_payload()
                            if binary_value:
                                news_attribute = NewsItemAttribute(binary_mime_type, file_name, binary_mime_type, binary_value)
                                news_item.attributes.append(news_attribute)
                            else:
                                self.source.logger.error(f"Attachment is empty or could not be decoded: {file_name}")

            self.news_items.append(news_item)

    @ignore_exceptions
    def collect(self):
        """Collect data from email source."""
        self.news_items = []
        self.email_server_type = self.source.param_key_values["EMAIL_SERVER_TYPE"]
        if not self.email_server_type:
            self.source.logger.error("Email server type is not set. Skipping collection.")
            return
        self.email_server_hostname = self.source.param_key_values["EMAIL_SERVER_HOSTNAME"]
        if not self.email_server_hostname:
            self.source.logger.error("Email server hostname is not set. Skipping collection.")
            return
        self.email_server_port = self.source.param_key_values["EMAIL_SERVER_PORT"]
        self.email_username = self.source.param_key_values["EMAIL_USERNAME"]
        self.email_password = self.source.param_key_values["EMAIL_PASSWORD"]
        self.source.proxy = self.source.param_key_values["PROXY_SERVER"]
        self.source.parsed_proxy = self.get_parsed_proxy()
        self.email_sender_address = self.source.param_key_values["EMAIL_SENDER"]
        self.emails_limit = read_int_parameter("EMAILS_LIMIT", "", self.source)

        if self.email_server_type.casefold() == "imap":
            self.__fetch_emails_imap()
        elif self.email_server_type.casefold() == "pop3":
            self.__fetch_emails_pop3()
        else:
            self.source.logger.error(f"Email server connection type is not supported: '{self.email_server_type}'")

        self.publish(self.news_items)
