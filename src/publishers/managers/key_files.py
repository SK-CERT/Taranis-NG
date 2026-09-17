"""Diagnostics for the key files publisher presets point at.

Two presets name a file the publisher has to read: the SFTP publisher's private
key, and the email publisher's signing and encryption keys. Both are mounted in
from the host, and both used to be read by a service running as root. Since the
services dropped to an unprivileged user a key mounted 0600 root:root is
readable on the host and not in the container, so the failure an operator hits
first is a bare ``Permission denied`` naming a path that, being relative to the
container's working directory, does not exist anywhere they can look.

Everything needed to act on that - the path actually opened and the uid that
could not open it - lives here so the two publishers report it the same way.
"""

from __future__ import annotations

import os
from pathlib import Path


def unreadable_key_error(key_path: str, description: str, error: OSError) -> OSError:
    """Build the error to raise when a configured key file cannot be read.

    Args:
        key_path (str): The path as configured in the preset, absolute or relative.
        description (str): What the file is, for the message ("SSH key").
        error (OSError): The failure from the attempted read.

    Returns:
        OSError: The replacement error, to raise ``from`` the original.
    """
    # A relative path resolves against the container's working directory, not
    # against anything the operator who typed it into the preset can see. Report
    # the path actually opened, so the failure names a findable file.
    msg = f"Cannot read the {description} at {Path(key_path).resolve()}: {error.strerror}."
    if isinstance(error, PermissionError):
        msg += (
            f" The publishers service runs as uid {os.getuid()}, so a file only root can read is unusable - "
            f"'chown {os.getuid()} <file>' on the host lets the container read it while it stays 0600."
        )
    return OSError(msg)
