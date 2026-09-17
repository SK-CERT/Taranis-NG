"""Publisher for publishing to an FTP server."""

import datetime
import ftplib
import mimetypes
from base64 import b64decode
from http import HTTPStatus
from io import BytesIO
from urllib.parse import urlsplit

from shared.common import TZ
from shared.config_publisher import ConfigPublisher
from shared.log_manager import logger

from .base_publisher import BasePublisher


class FTPPublisher(BasePublisher):
    """FTP Publisher class.

    Arguments:
        BasePublisher: Publisher base class

    Raises:
        Exception: _description_
    """

    publisher_type = "FTP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(publisher_type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input: dict) -> tuple[dict, HTTPStatus]:
        """Publish to an FTP server.

        Arguments:
            publisher_input: intput data for publisher

        Raises:
            Exception: _description_
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            ftp_url = publisher_input.param_key_values["FTP_URL"]
            mime_type = publisher_input.mime_type[:]
            file_extension = mimetypes.guess_extension(mime_type)
            filename = f"file_{datetime.datetime.now(TZ).strftime('%d-%m-%Y_%H:%M')}{file_extension}"
            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)
            # Kept in memory rather than staged on disk: the working directory belongs
            # to root so the unprivileged service cannot write there, and a temporary
            # file left behind on a failed upload is one more thing to clean up.
            file_object = BytesIO(bytes_data)

            ftp_data = urlsplit(ftp_url)

            ftp_hostname = ftp_data.hostname
            ftp_username = ftp_data.username
            ftp_password = ftp_data.password

            remote_path = ftp_data.path + filename

            if ftp_data.scheme == "ftp":
                ftp_port = ftp_data.port or 21
                ftp = ftplib.FTP()  # noqa: S321  # FTP is considered insecure
                self.logger.debug(f"Connecting FTP: {ftp_hostname}, port {ftp_port}")
                ftp.connect(host=ftp_hostname, port=ftp_port)
                ftp.login(ftp_username, ftp_password)
                ftp.storbinary("STOR " + remote_path, file_object)
                ftp.quit()
                return {}, HTTPStatus.OK

            msg = f"Scheme '{ftp_data.scheme}' not supported by the FTP publisher; use 'ftp' (for sftp, use the SFTP publisher)"
            self.logger.error(msg)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

        except Exception as error:
            self.logger.exception(f"Error: {error}")
            return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR
