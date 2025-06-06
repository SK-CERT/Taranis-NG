"""Publisher for SFTP server."""

from datetime import datetime
from base64 import b64decode
import paramiko
import mimetypes
from io import BytesIO
import os

from shared.log_manager import logger
from .base_publisher import BasePublisher
from shared.config_publisher import ConfigPublisher


class SFTPPublisher(BasePublisher):
    """SFTP Publisher class.

    This class represents a publisher that publishes data to an SFTP server.

    Attributes:
        type (str): The type of the publisher.
        name (str): The name of the publisher.
        description (str): The description of the publisher.
        parameters (list): The list of parameters required for the publisher.

    Methods:
        publish(publisher_input): Publishes data to the SFTP server.

    """

    type = "SFTP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input):
        """Publish to SFTP server.

        This method publishes the data to the SFTP server based on the provided input.

        Args:
            publisher_input (PublisherInput): The input data for the publisher.

        Raises:
            Exception: If there is an error during the publishing process.

        """
        self.logger = logger
        self.logger.log_prefix = f"{self.name} '{publisher_input.name}'"
        url = publisher_input.param_key_values["SFTP_URL"]
        port = publisher_input.param_key_values["PORT"]
        username = publisher_input.param_key_values["USERNAME"]
        password = publisher_input.param_key_values["PASSWORD"]
        path = publisher_input.param_key_values["PATH"]
        filename = publisher_input.param_key_values["FILENAME"]
        command = publisher_input.param_key_values["COMMAND"]
        ssh_key = publisher_input.param_key_values["SSH_KEY"]
        ssh_key_password = publisher_input.param_key_values["SSH_KEY_PASSWORD"]

        now = datetime.now().strftime("%Y%m%d%H%M%S")

        def _get_key(key_path, ssh_key_password=None):
            try:
                ssh_key = paramiko.RSAKey(filename=key_path, password=ssh_key_password)
                return ssh_key
            except paramiko.ssh_exception.SSHException:
                pass
            try:
                ssh_key = paramiko.Ed25519Key(filename=key_path, password=ssh_key_password)
                return ssh_key
            except paramiko.ssh_exception.SSHException:
                pass
            try:
                ssh_key = paramiko.ECDSAKey(filename=key_path, password=ssh_key_password)
                return ssh_key
            except paramiko.ssh_exception.SSHException:
                pass
            try:
                ssh_key = paramiko.DSSKey(filename=key_path, password=ssh_key_password)
                return ssh_key
            except paramiko.ssh_exception.SSHException as error:
                self.logger.exception(f"Issue with SSH key {key_path}: {error}")
                return None

        try:
            # decide filename and extension
            mime_type = publisher_input.mime_type[:]
            file_extension = mimetypes.guess_extension(mime_type)
            if filename:
                filename = f"{filename}{file_extension}"
            else:
                filename = f"file_{now}{file_extension}"
            full_path = os.path.join(path, filename)

            # fill file with data
            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)
            file_object = BytesIO(bytes_data)

            # decide SFTP port
            port = port if port else 22

            # determine SSH key type
            if ssh_key:
                ssh_key = _get_key(ssh_key, ssh_key_password)
            else:
                ssh_key = None

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if ssh_key:
                ssh.connect(hostname=url, port=port, username=username, pkey=ssh_key)
            else:
                ssh.connect(hostname=url, port=port, username=username, password=password)
            sftp = ssh.open_sftp()
            self.logger.info(f"Successfully connected to {url} on port {port}")
            try:
                sftp.putfo(file_object, f"{full_path}", confirm=True)
                self.logger.info(f"Successfully saved data to {full_path} on remote machine")
            except Exception as error:
                self.logger.exception(f"Failed to save data to {full_path} on remote machine: {error}")
            if command:
                try:
                    ssh.exec_command(command)
                    self.logger.info(f"Executed command {command} on remote machine")
                except Exception as error:
                    self.logger.exception(f"Failed to execute command {command} on remote machine: {error}")
            sftp.close()
        except Exception as error:
            self.logger.exception(f"Publishing fail: {error}")
