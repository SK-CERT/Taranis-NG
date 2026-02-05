"""Publisher for SFTP server."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paramiko.pkey import PKey


import mimetypes
from base64 import b64decode
from datetime import datetime
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

import paramiko

from shared.common import TZ
from shared.config_publisher import ConfigPublisher
from shared.log_manager import logger

from .base_publisher import BasePublisher


class SFTPPublisher(BasePublisher):
    """SFTP Publisher class."""

    type = "SFTP_PUBLISHER"
    config = ConfigPublisher().get_config_by_type(type)
    name = config.name
    description = config.description
    parameters = config.parameters

    def publish(self, publisher_input: dict) -> tuple[dict, HTTPStatus]:
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

        now = datetime.now(TZ).strftime("%Y%m%d%H%M%S")

        def _get_key(key_path: str, ssh_key_password: str | None) -> PKey:
            try:
                return paramiko.RSAKey(filename=key_path, password=ssh_key_password)
            except paramiko.ssh_exception.SSHException:
                pass
            try:
                return paramiko.Ed25519Key(filename=key_path, password=ssh_key_password)
            except paramiko.ssh_exception.SSHException:
                pass
            try:
                return paramiko.ECDSAKey(filename=key_path, password=ssh_key_password)
            except paramiko.ssh_exception.SSHException:
                pass
            try:
                return paramiko.DSSKey(filename=key_path, password=ssh_key_password)
            except paramiko.ssh_exception.SSHException as error:
                self.logger.exception(f"Issue with SSH key {key_path}: {error}")
                return None

        try:
            # decide filename and extension
            mime_type = publisher_input.mime_type[:]
            file_extension = mimetypes.guess_extension(mime_type)
            filename = f"{filename}{file_extension}" if filename else f"file_{now}{file_extension}"
            full_path = Path(path) / filename

            # fill file with data
            data = publisher_input.data[:]
            bytes_data = b64decode(data, validate=True)
            file_object = BytesIO(bytes_data)

            # decide SFTP port
            port = port if port else 22

            # determine SSH key type
            ssh_key = _get_key(ssh_key, ssh_key_password) if ssh_key else None

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507  # unsafe connect
            self.logger.debug(f"Connecting to {url}, port {port}, user {username}")
            if ssh_key:
                ssh.connect(hostname=url, port=port, username=username, pkey=ssh_key)
            else:
                ssh.connect(hostname=url, port=port, username=username, password=password)
            sftp = ssh.open_sftp()
            self.logger.info(f"Successfully connected to {url} on port {port}")
            status = HTTPStatus.OK
            try:
                sftp.putfo(file_object, f"{full_path}", confirm=True)
                msg = f"Data saved to {full_path} on remote machine"
                self.logger.info(msg)
            except Exception as error:
                msg = f"Failed to save data to {full_path} on remote machine"
                self.logger.exception(f"{msg}: {error}")
                status = HTTPStatus.INTERNAL_SERVER_ERROR
            if command:
                try:
                    ssh.exec_command(command)
                    msg = f"Command {command} executed on remote machine"
                    self.logger.info(msg)
                except Exception as error:
                    msg = f"Failed to execute command {command} on remote machine"
                    self.logger.exception(f"{msg}:: {error}")
                    status = HTTPStatus.INTERNAL_SERVER_ERROR
            sftp.close()
            type_msg = "message" if status == HTTPStatus.OK else "error"
            return {type_msg: msg}, status

        except Exception as error:
            self.logger.exception(f"Error: {error}")
            return {"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR
