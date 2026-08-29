"""Host-key verification for the SSH/SFTP publishers.

``AutoAddPolicy`` accepts whatever key the far end presents on first contact, so
anything able to answer on the configured address can impersonate the target and
receive the report - which for a Taranis publisher may be TLP:AMBER or RED
material. Configuring the expected key turns that into a real check.

The policy is deliberately *not* strict-by-default: every existing preset was
created without a host key, and defaulting to ``RejectPolicy`` would break all
of them on upgrade. A preset with ``HOST_KEY`` set verifies strictly; one
without keeps the old behaviour and logs a warning naming the key it saw, which
is the value an operator pastes into the setting to migrate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import paramiko
from paramiko.hostkeys import HostKeyEntry

if TYPE_CHECKING:
    import logging

DEFAULT_SSH_PORT = 22


def host_key_name(hostname: str, port: int | str | None) -> str:
    """Return the name paramiko indexes a host key under.

    Paramiko stores non-default ports in the ``[host]:port`` form, so a key
    registered under the bare hostname would never be found for, say, port 2222.

    Args:
        hostname (str): The SSH host.
        port (int | str | None): The SSH port, if not the default.

    Returns:
        str: The lookup name for this host and port.
    """
    try:
        resolved = int(port) if port else DEFAULT_SSH_PORT
    except (TypeError, ValueError):
        resolved = DEFAULT_SSH_PORT
    return hostname if resolved == DEFAULT_SSH_PORT else f"[{hostname}]:{resolved}"


def apply_host_key_policy(
    ssh: paramiko.SSHClient,
    host_key: str | None,
    hostname: str,
    port: int | str | None,
    logger: logging.Logger,
) -> None:
    """Pin the configured host key, or warn that the connection is unverified.

    Args:
        ssh (paramiko.SSHClient): The client about to connect.
        host_key (str | None): The expected key, as a ``known_hosts`` line or a
            bare ``keytype base64`` pair. Empty means "not configured".
        hostname (str): The SSH host being connected to.
        port (int | str | None): The SSH port.
        logger (logging.Logger): Where to report an unverified connection.

    Raises:
        ValueError: When ``host_key`` is set but cannot be parsed.
    """
    if not (host_key and host_key.strip()):
        logger.warning(
            f"Connecting to {hostname} without host key verification - any host answering on that address is trusted. "
            f"Set the publisher preset's 'SSH host key' to the server's public key to verify it.",
        )
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return

    name = host_key_name(hostname, port)
    entry = _parse_host_key(host_key.strip(), name)
    ssh.get_host_keys().add(name, entry.key.get_name(), entry.key)
    # Nothing may be added at connect time: an unknown or changed key is refused.
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    logger.debug(f"Verifying {name} against the configured {entry.key.get_name()} host key")


def _parse_host_key(host_key: str, name: str) -> HostKeyEntry:
    """Parse a known_hosts line, or a bare 'keytype base64' pair, into an entry."""
    for candidate in (host_key, f"{name} {host_key}"):
        try:
            entry = HostKeyEntry.from_line(candidate)
        except Exception:  # any parse failure just means "try the other shape"
            entry = None
        if entry is not None and entry.key is not None:
            return entry
    msg = "The configured SSH host key could not be parsed. Provide a known_hosts line or a 'keytype base64' pair."
    raise ValueError(msg)
