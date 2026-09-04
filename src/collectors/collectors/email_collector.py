"""Module for email collector."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from email.message import EmailMessage

import datetime
import email.header
import email.utils
import hashlib
import imaplib
import poplib
import socket
import uuid
from email import policy

from shared.common import TZ, ignore_exceptions, read_int_parameter, text_to_simple_html
from shared.config_collector import ConfigCollector
from shared.schema.news_item import NewsItemAttribute, NewsItemData

from .base_collector import BaseCollector


class EmailCollector(BaseCollector):
    """Collector for gathering data from emails.

    Attributes:
        collector_type (str): Type of the collector.
        name (str): Name of the collector.
        description (str): Description of the collector.
        parameters (list): List of parameters required for the collector.

    Methods:
        collect(): Collect data from email source.
    """

    collector_type = "EMAIL_COLLECTOR"
    config = ConfigCollector().get_config_by_type(collector_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def __proxy_tunnel(self, email_server_hostname: str, email_server_port: str) -> None:
        self.source.logger.debug("Establishing proxy tunnel")
        server = f"{email_server_hostname.lower()}"
        port = email_server_port

        proxy = (f"{self.source.parsed_proxy.scheme}://{self.source.parsed_proxy.hostname}", self.source.parsed_proxy.port)
        con = f"CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(proxy)
            s.send(str.encode(con))
            s.recv(4096)

    def __fetch_emails_imap(self) -> None:
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
                # Parsed from bytes, so each part is decoded with the charset it declares.
                # Decoding the whole message as UTF-8 first threw away everything else.
                email_message = email.message_from_bytes(raw_email, policy=policy.default)
                self.__process_email_safely(email_message)

            connection.close()
            connection.logout()
        except Exception as error:
            self.source.logger.exception(f"Failed to fetch emails using IMAP: {error}")

    def __fetch_emails_pop3(self) -> None:
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
                    # retr() numbers messages from 1, so retr(i + 1) asked for one past the
                    # end on the first pass and every POP3 collection died there.
                    raw_email = b"\r\n".join(connection.retr(i)[1])
                    email_message = email.message_from_bytes(raw_email, policy=policy.default)
                    if self.email_sender_address not in ["", None]:
                        sender_from_email = email.utils.parseaddr(email_message.get("From", ""))
                        if self.email_sender_address in sender_from_email:
                            processed_emails += 1
                            self.source.logger.debug(f"Sender email address matches: {self.email_sender_address} = {sender_from_email}")
                            self.__process_email_safely(email_message)
                    else:
                        self.__process_email_safely(email_message)

            connection.quit()
        except Exception as error:
            self.source.logger.exception(f"Failed to fetch emails using POP3: {error}")

    def __process_email_safely(self, email_message: EmailMessage) -> None:
        """Process one email, keeping a failure from ending the run.

        Both fetchers hold the whole mailbox in a single ``try``, so anything raised over
        one malformed message used to cost every message after it as well.

        Args:
            email_message (EmailMessage): The email to process.
        """
        try:
            self.__process_email(email_message)
        except Exception as error:
            self.source.logger.exception(f"Processing an email failed, skipping it: {error}")

    def __decode_text(self, raw_value: str, name: str) -> str:
        """Return header text with any RFC 2047 encoded words resolved.

        Args:
            raw_value (str): The raw header text.
            name (str): Name of the header (for logging purposes).

        Returns:
            str: The decoded text.
        """
        if not raw_value:
            return ""
        try:
            return str(email.header.make_header(email.header.decode_header(raw_value)))
        except Exception:
            self.source.logger.debug(f"Could not decode the '{name}' header, using it as it is")
            return str(raw_value)

    def __decode_header(self, email_message: EmailMessage, name: str) -> str:
        """Return a header as plain text, or an empty string when the email has none.

        Args:
            email_message (EmailMessage): The email to read the header from.
            name (str): Name of the header.

        Returns:
            str: The decoded header value.
        """
        raw_value = email_message.get(name)
        if raw_value is None:
            self.source.logger.debug(f"Email has no '{name}' header")
            return ""
        return self.__decode_text(raw_value, name)

    def __get_author(self, email_message: EmailMessage) -> tuple[str, str]:
        """Return the sender as a readable name and as a bare address.

        Args:
            email_message (EmailMessage): The email to read the sender from.

        Returns:
            tuple[str, str]: The author to display and the sender's address.
        """
        realname, address = email.utils.parseaddr(email_message.get("From", ""))
        realname = self.__decode_text(realname, "From")
        # Parenthesised, not the "Name <address>" the header uses: sanitize_news_item()
        # strips markup from the author, and angle brackets read as a tag - which took the
        # whole address with them.
        author = f"{realname} ({address})" if realname and address else realname or address
        return author, address

    def __get_published(self, email_message: EmailMessage, title: str) -> str:
        """Return the send date of the email, falling back to the current time.

        Args:
            email_message (EmailMessage): The email to read the date from.
            title (str): Subject of the email (for logging purposes).

        Returns:
            str: The formatted date.
        """
        try:
            date = email.utils.parsedate_to_datetime(email_message.get("Date"))
        except (TypeError, ValueError):
            self.source.logger.debug(f"Email '{title}' has no usable 'Date' header, using the time of collection")
            date = datetime.datetime.now(TZ)
        if date.tzinfo is None:
            date = date.replace(tzinfo=TZ)
        return date.astimezone(TZ).strftime("%d.%m.%Y - %H:%M")

    def __decode_body(self, part: EmailMessage, title: str) -> str:
        """Decode one body part using the charset it declares.

        Args:
            part (EmailMessage): The body part of the email.
            title (str): Subject of the email (for logging purposes).

        Returns:
            str: The decoded body.
        """
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        self.source.logger.debug(f"Detected encoding of email '{title}': {charset}")
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            self.source.logger.warning(f"Unknown encoding '{charset}' of email '{title}', reading it as UTF-8")
            return payload.decode("utf-8", errors="replace")

    def __get_content(self, email_message: EmailMessage, title: str) -> str:
        """Return the email body as HTML, keeping the formatting the sender used.

        An email carrying both an HTML and a plain text alternative is stored as HTML - the
        richer of the two, the same preference the RSS and web collectors apply to a feed
        entry. Plain text goes in preformatted, so its line breaks, indentation and ASCII
        tables survive instead of collapsing into one paragraph.

        Args:
            email_message (EmailMessage): The email to read the body from.
            title (str): Subject of the email (for logging purposes).

        Returns:
            str: The body as an HTML fragment, empty when the email has no body.
        """
        part = email_message.get_body(preferencelist=("html", "plain"))
        body = self.__decode_body(part, title) if part is not None else ""
        if not body.strip():
            self.source.logger.warning(f"No text or HTML body found in email '{title}'")
            return ""
        if part.get_content_subtype() == "html":
            self.source.logger.debug(f"Using the HTML body of email '{title}'")
            # Left as it is: sanitize_news_item() reduces it to the supported tags.
            return body
        self.source.logger.debug(f"Using the plain text body of email '{title}'")
        return text_to_simple_html(body, preformatted_text=True)

    def __collect_attachments(self, email_message: EmailMessage, news_item: NewsItemData) -> None:
        """Attach the email's files to the news item and collect any attached email.

        Args:
            email_message (EmailMessage): The email to read the attachments from.
            news_item (NewsItemData): The news item to attach them to.
        """
        for part in email_message.walk():
            file_name = part.get_filename()
            binary_mime_type = part.get_content_type()
            match binary_mime_type:
                case "message/rfc822":
                    self.source.logger.debug("Found an attached email")
                    attached = part.get_payload()
                    attached_email = attached[0] if isinstance(attached, list) else attached
                    # Process .eml file as an email. Guarded, so a broken attachment does
                    # not cost the email carrying it.
                    self.__process_email_safely(attached_email)

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

    def __process_email(self, email_message: EmailMessage) -> None:
        preview_size = 3000

        email_string = email_message.as_string()
        if len(email_string) > preview_size:
            email_string = f"{email_string[:preview_size]}\n..."
        self.source.logger.debug(f"Processing email: {email_string}")

        title = self.__decode_header(email_message, "Subject")
        self.source.logger.debug(f"Processing email: {title}")
        author, address = self.__get_author(email_message)
        message_id = self.__decode_header(email_message, "Message-ID")
        published = self.__get_published(email_message, title)
        content = self.__get_content(email_message, title)

        # Hashed on the raw sender rather than the reformatted author, so emails collected
        # by earlier versions keep the hash they have and are not collected a second time.
        for_hash = self.__decode_header(email_message, "From") + title + message_id

        news_item = NewsItemData(
            uuid.uuid4(),
            hashlib.sha256(for_hash.encode()).hexdigest(),
            title,
            content,  # the review; sanitize_news_item() strips the markup and truncates it
            address,
            "",  # the link, an email has none
            published,
            author,
            datetime.datetime.now(TZ),
            content,
            self.source.id,
            [],
        )

        self.__collect_attachments(email_message, news_item)
        self.sanitize_news_item(news_item, self.source)
        news_item.print_news_item(self.source.logger)
        self.news_items.append(news_item)

    @ignore_exceptions
    def collect(self) -> None:
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
