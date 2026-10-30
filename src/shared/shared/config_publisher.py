"""Definition for publisher modules."""

from shared.schema.parameter import ParameterType

from .config_base import ConfigBase, ModuleType, ParamType


class ConfigPublisher(ConfigBase):
    """Configuration for publisher modules."""

    def __init__(self) -> None:
        """Initialize publisher modules."""
        self.modules: list[ModuleType] = []

        mod = ModuleType("EMAIL_PUBLISHER", "Email Publisher", "Publisher for publishing by email")
        mod.parameters = [
            ParamType("SMTP_SERVER", "SMTP server", "SMTP server for sending emails", ParameterType.STRING),
            ParamType("SMTP_SERVER_PORT", "SMTP server port", "SMTP server port for sending emails", ParameterType.STRING, "587"),
            ParamType("EMAIL_USERNAME", "Email username", "Username for email account", ParameterType.STRING),
            ParamType("EMAIL_PASSWORD", "Email password", "Password for email account", ParameterType.STRING),
            ParamType("EMAIL_SENDER", "Email sender", "Email address of the sender", ParameterType.STRING),
            ParamType("EMAIL_RECIPIENT", "Email recipient", "Email address of the recipient", ParameterType.STRING),
            ParamType("EMAIL_SUBJECT", "Email subject", "Text of email subject", ParameterType.STRING, "Security Warning"),
            ParamType("EMAIL_MESSAGE", "Email message", "Text of email message", ParameterType.STRING),
            ParamType("EMAIL_SIGN", "Email signature", "File used for signing or auto", ParameterType.STRING),
            ParamType("EMAIL_SIGN_PASSWORD", "Email signature password", "Password for signing file", ParameterType.STRING),
            ParamType("EMAIL_ENCRYPT", "Email encryption", "File used for encryption or auto", ParameterType.STRING),
        ]
        self.modules.append(mod)

        mod = ModuleType("FTP_PUBLISHER", "FTP Publisher", "Publisher for publishing to FTP server")
        mod.parameters = [ParamType("FTP_URL", "FTP URL", "FTP server url", ParameterType.STRING)]
        self.modules.append(mod)

        mod = ModuleType("MISP_PUBLISHER", "MISP Publisher", "Publisher for publishing in MISP")
        mod.parameters = [
            ParamType("MISP_URL", "MISP url", "MISP server https url", ParameterType.STRING),
            ParamType("MISP_API_KEY", "MISP API key", "User MISP API key", ParameterType.STRING),
        ]
        self.modules.append(mod)

        mod = ModuleType("SFTP_PUBLISHER", "SFTP Publisher", "Publisher for publishing to SFTP server")
        mod.parameters = [
            ParamType("SFTP_URL", "SFTP URL", "SFTP server URL", ParameterType.STRING),
            ParamType("PORT", "SSH port", "Port remote machine is using for SSH (default 22)", ParameterType.STRING),
            ParamType(
                "HOST_KEY",
                "SSH host key",
                "Expected public key of the SFTP server, as a known_hosts line or a 'keytype base64' pair. "
                "Leave empty to accept whatever key the server presents (unverified, logs a warning).",
                ParameterType.STRING,
            ),
            ParamType("SSH_KEY", "SSH key", "Private key which should be used for SSH connection", ParameterType.STRING),
            ParamType("SSH_KEY_PASSWORD", "SSH key password", "Password for the SSH private key", ParameterType.STRING),
            ParamType("USERNAME", "Username", "Username for SFTP", ParameterType.STRING),
            ParamType("PASSWORD", "Password", "Password for SFTP", ParameterType.STRING),
            ParamType(
                "PATH",
                "Remote path",
                "Either absolute or relative path where the file should be saved on the remote machine",
                ParameterType.STRING,
            ),
            ParamType(
                "FILENAME",
                "Filename",
                "Custom mame of the transported file without extension (default file_%d-%m-%Y_%H:%M)",
                ParameterType.STRING,
            ),
            ParamType("COMMAND", "Command", "Command to be executed on the remote machine", ParameterType.STRING),
        ]
        self.modules.append(mod)

        mod = ModuleType("TWITTER_PUBLISHER", "Twitter Publisher", "Publisher for publishing to Twitter account")
        mod.parameters = [
            ParamType("TWITTER_API_KEY", "Twitter API key", "API key of Twitter account", ParameterType.STRING),
            ParamType("TWITTER_API_KEY_SECRET", "Twitter API key secret", "API key secret of Twitter account", ParameterType.STRING),
            ParamType("TWITTER_ACCESS_TOKEN", "Twitter access token", "Twitter access token of Twitter account", ParameterType.STRING),
            ParamType(
                "TWITTER_ACCESS_TOKEN_SECRET",
                "Twitter access token secret",
                "Twitter access token secret of Twitter account",
                ParameterType.STRING,
            ),
        ]
        self.modules.append(mod)

        mod = ModuleType("MASTODON_PUBLISHER", "Mastodon Publisher", "Publisher for posting to Mastodon account")
        mod.parameters = [
            ParamType("MASTODON_ACCESS_TOKEN", "Mastodon access token", "Mastodon access token of Mastodon account", ParameterType.STRING),
            ParamType(
                "MASTODON_API_BASE_URL",
                "Mastodon API base URL",
                "Defaults to 'https://mastodon.social'",
                ParameterType.STRING,
                "https://mastodon.social",
            ),
            ParamType(
                "VISIBILITY",
                "Visibility",
                "Sets the visibility of the posted status (direct | private | unlisted | public)",
                ParameterType.STRING,
                "public",
            ),
            ParamType("SENSITIVE", "Sensitive", "Mark status as sensitive (true | false)", ParameterType.BOOLEAN, "false"),
        ]
        self.modules.append(mod)

        mod = ModuleType("WORDPRESS_PUBLISHER", "Wordpress Publisher", "Publisher for publishing on Wordpress webpage")
        mod.parameters = [
            ParamType("WP_URL", "Wordpress URL address", "URL address of wordpress webpage", ParameterType.STRING),
            ParamType("WP_USER", "Username of wordpress editor", "Post editor's username", ParameterType.STRING),
            ParamType(
                "WP_PYTHON_APP_SECRET",
                "Secret key of application",
                "Secret key created in Wordpress for Python application",
                ParameterType.STRING,
            ),
        ]
        self.modules.append(mod)
