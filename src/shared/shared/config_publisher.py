"""Definition for publisher modules."""

from .config_base import ConfigBase, module_type, param_type
from typing import List
from shared.schema.parameter import ParameterType


class ConfigPublisher(ConfigBase):
    """Configuration for publisher modules."""

    def __init__(self):
        """Initialize publisher modules."""
        self.modules: List[module_type] = []

        mod = module_type("EMAIL_PUBLISHER", "EMAIL Publisher", "Publisher for publishing by email")
        mod.parameters = [
            param_type("SMTP_SERVER", "SMTP server", "SMTP server for sending emails", ParameterType.STRING),
            param_type("SMTP_SERVER_PORT", "SMTP server port", "SMTP server port for sending emails", ParameterType.STRING),
            param_type("EMAIL_USERNAME", "Email username", "Username for email account", ParameterType.STRING),
            param_type("EMAIL_PASSWORD", "Email password", "Password for email account", ParameterType.STRING),
            param_type("EMAIL_SENDER", "Email sender", "Email address of the sender", ParameterType.STRING),
            param_type("EMAIL_RECIPIENT", "Email recipient", "Email address of the recipient", ParameterType.STRING),
            param_type("EMAIL_SUBJECT", "Email subject", "Text of email subject", ParameterType.STRING),
            param_type("EMAIL_MESSAGE", "Email message", "Text of email message", ParameterType.STRING),
            param_type("EMAIL_SIGN", "Email signature", "File used for signing or auto", ParameterType.STRING),
            param_type("EMAIL_SIGN_PASSWORD", "Email signature password", "Password for signing file", ParameterType.STRING),
            param_type("EMAIL_ENCRYPT", "Email encryption", "File used for encryption or auto", ParameterType.STRING),
        ]
        self.modules.append(mod)

        mod = module_type("FTP_PUBLISHER", "FTP Publisher", "Publisher for publishing to FTP server")
        mod.parameters = [param_type("FTP_URL", "FTP URL", "FTP server url", ParameterType.STRING)]
        self.modules.append(mod)

        mod = module_type("MISP_PUBLISHER", "MISP Publisher", "Publisher for publishing in MISP")
        mod.parameters = [
            param_type("MISP_URL", "MISP url", "MISP server https url", ParameterType.STRING),
            param_type("MISP_API_KEY", "MISP API key", "User MISP API key", ParameterType.STRING),
        ]
        self.modules.append(mod)

        mod = module_type("SFTP_PUBLISHER", "SFTP Publisher", "Publisher for publishing to SFTP server")
        mod.parameters = [
            param_type("SFTP_URL", "SFTP URL", "SFTP server URL", ParameterType.STRING),
            param_type("PORT", "SSH port", "Port remote machine is using for SSH (default 22)", ParameterType.STRING),
            param_type("SSH_KEY", "SSH key", "Private key which should be used for SSH connection", ParameterType.STRING),
            param_type("SSH_KEY_PASSWORD", "SSH key password", "Password for the SSH private key", ParameterType.STRING),
            param_type("USERNAME", "Username", "Username for SFTP", ParameterType.STRING),
            param_type("PASSWORD", "Password", "Password for SFTP", ParameterType.STRING),
            param_type(
                "PATH",
                "Remote path",
                "Either absolute or relative path where the file should be saved on the remote machine",
                ParameterType.STRING,
            ),
            param_type(
                "FILENAME",
                "Filename",
                "Custom mame of the transported file without extension (default file_%d-%m-%Y_%H:%M)",
                ParameterType.STRING,
            ),
            param_type("COMMAND", "Command", "Command to be executed on the remote machine", ParameterType.STRING),
        ]
        self.modules.append(mod)

        mod = module_type("TWITTER_PUBLISHER", "Twitter Publisher", "Publisher for publishing to Twitter account")
        mod.parameters = [
            param_type("TWITTER_API_KEY", "Twitter API key", "API key of Twitter account", ParameterType.STRING),
            param_type("TWITTER_API_KEY_SECRET", "Twitter API key secret", "API key secret of Twitter account", ParameterType.STRING),
            param_type("TWITTER_ACCESS_TOKEN", "Twitter access token", "Twitter access token of Twitter account", ParameterType.STRING),
            param_type(
                "TWITTER_ACCESS_TOKEN_SECRET",
                "Twitter access token secret",
                "Twitter access token secret of Twitter account",
                ParameterType.STRING,
            ),
        ]
        self.modules.append(mod)

        mod = module_type("WORDPRESS_PUBLISHER", "Wordpress Publisher", "Publisher for publishing on Wordpress webpage")
        mod.parameters = [
            param_type("WP_URL", "Wordpress URL address", "URL address of wordpress webpage", ParameterType.STRING),
            param_type("WP_USER", "Username of wordpress editor", "Post editor's username", ParameterType.STRING),
            param_type(
                "WP_PYTHON_APP_SECRET",
                "Secret key of application",
                "Secret key created in Wordpress for Python application",
                ParameterType.STRING,
            ),
        ]
        self.modules.append(mod)
