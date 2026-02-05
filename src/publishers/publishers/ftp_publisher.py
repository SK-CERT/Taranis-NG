"""Publisher for publishing to FTP and SFTP server.

Raises:
    Exception: _description_
"""

import datetime
import ftplib
import mimetypes
from base64 import b64decode
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlsplit

import paramiko

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

    type = "FTP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input: dict) -> tuple[dict, HTTPStatus]:
        """Publish to FTP or SFTP server.

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

            with Path(filename).open("wb") as f:
                f.write(bytes_data)
                f.close()

            ftp_data = urlsplit(ftp_url)

            ftp_hostname = ftp_data.hostname
            ftp_username = ftp_data.username
            ftp_password = ftp_data.password

            remote_path = ftp_data.path + filename

            if ftp_data.scheme == "sftp":
                ssh_port = ftp_data.port if ftp_data.port else 22
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507  # unsafe connect
                self.logger.debug(f"Connecting SFTP: {ftp_hostname}, port {ssh_port}, user {ftp_username}")
                ssh.connect(hostname=ftp_hostname, port=ssh_port, username=ftp_username, password=ftp_password)
                sftp = ssh.open_sftp()
                sftp.put(filename, remote_path)
                sftp.close()
                return {}, HTTPStatus.OK

            if ftp_data.scheme == "ftp":
                ftp_port = ftp_data.port if ftp_data.port else 21
                ftp = ftplib.FTP()  # noqa: S321  # FTP is considered insecure
                self.logger.debug(f"Connecting FTP: {ftp_hostname}, port {ftp_port}")
                ftp.connect(host=ftp_hostname, port=ftp_port)
                ftp.login(ftp_username, ftp_password)
                with Path(filename).open("rb") as f:
                    ftp.storbinary("STOR " + remote_path, f)
                ftp.quit()
                return {}, HTTPStatus.OK

            msg = f"Schema '{ftp_data.scheme}' not supported, choose 'ftp' or 'sftp'"
            self.logger.exception(msg)
            return {"error": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

        except Exception as error:
            self.logger.exception(f"Error: {error}")
            return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR

        finally:
            Path(filename).unlink()
