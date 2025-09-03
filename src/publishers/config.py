"""Configuration management for the publishers service."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for the publishers service."""

    @staticmethod
    def read_secret(secret_name: str) -> str:
        """Read a secret from a file in the /run/secrets/ directory.

        Args:
            secret_name (str): The name of the secret file to read.

        Returns:
            str: The content of the secret file.

        Raises:
            RuntimeError: If the secret file is not found.
        """
        file_path = Path(f"/run/secrets/{secret_name}")
        try:
            with file_path.open() as secret_file:
                return secret_file.read().strip()
        except FileNotFoundError as err:
            msg = f"Secret file not found: {file_path}"
            raise RuntimeError(msg) from err

    API_KEY = read_secret("api_key")
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_SEND = os.getenv("EMAIL_SEND")
