"""Publisher for publishing to FTP and SFTP server.

Raises:
    Exception: _description_
"""

import datetime
import ftplib
import os
from base64 import b64decode
from urllib.parse import urlsplit
import paramiko
import mimetypes

from .base_publisher import BasePublisher
from shared.log_manager import logger
from shared.config_publisher import ConfigPublisher


class FTPPublisher(BasePublisher):
    """FTP Publisher class.

    Arguments:
        BasePublisher -- Publisher base class

    Raises:
        Exception: _description_
    """

    type = "FTP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input):
        """Publish to FTP or SFTP server.

        Arguments:
            publisher_input -- intput data for publisher

        Raises:
            Exception: _description_
        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        try:
            ftp_url = publisher_input.parameter_values_map["FTP_URL"]
            mime_type = publisher_input.mime_type[:]
            file_extension = mimetypes.guess_extension(mime_type)
            filename = f"file_{datetime.datetime.now().strftime('%d-%m-%Y_%H:%M')}{file_extension}"
            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)

            f = open(filename, "wb")
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
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=ftp_hostname, port=ssh_port, username=ftp_username, password=ftp_password)
                sftp = ssh.open_sftp()
                sftp.put(filename, remote_path)
                sftp.close()
            elif ftp_data.scheme == "ftp":
                ftp_port = ftp_data.port if ftp_data.port else 21
                ftp = ftplib.FTP()
                ftp.connect(host=ftp_hostname, port=ftp_port)
                ftp.login(ftp_username, ftp_password)
                ftp.storbinary("STOR " + remote_path, open(filename, "rb"))
                ftp.quit()
            else:
                raise Exception("Schema '{}' not supported, choose 'ftp' or 'sftp'".format(ftp_data.scheme))
        except Exception as error:
            self.logger.exception(f"Publishing fail: {error}")
        finally:
            os.remove(filename)
