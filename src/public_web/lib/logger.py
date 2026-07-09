"""Logger configuration for public-web."""

import logging
import os
import sys
from logging.handlers import SysLogHandler
from pathlib import Path

from lib import config


def _get_file_handler(path: Path) -> logging.FileHandler:
    """Returns a universal file handler for logging with a correct log format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s: [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    return file_handler


class SyslogSingleLineFormatter(logging.Formatter):
    """Simple syslog formatter that replaces newlines with ' | '.

    This is needed because newline in logs are problematic.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record by replacing newlines with ' | '.

        Args:
            record: The log record to format.

        Returns:
            The formatted log message.
        """
        original = super().format(record)
        return original.replace("\n", " | ")


def _get_syslog_handler(text: str) -> SysLogHandler | None:
    """Returns a handler for syslog, or None if /dev/log is unavailable.

    (e.g. inside a container without a syslog socket). Note that
    SysLogHandler construction can succeed even when the socket is missing
    (the connect is deferred to emit time), so check the path up front.
    """
    if not Path("/dev/log").exists():
        return None
    try:
        syslog_handler = SysLogHandler(address="/dev/log")
    except OSError:
        return None
    formatter = SyslogSingleLineFormatter("[%(levelname)s] %(message)s")
    syslog_handler.setFormatter(formatter)
    # This is so that syslog has "public-web-incoming" instead of "python3"
    # as the identity of the service.
    syslog_handler.ident = f"public-web-{text}: "
    syslog_handler.setLevel(logging.INFO)
    return syslog_handler


def get_logger(text: str, debug: bool = False, silent: bool = False) -> logging.Logger:
    """Returns an instance of a logger object."""
    logger = logging.getLogger(text)
    # Avoid attaching duplicate handlers if called more than once for a name.
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    # Do not propagate to the root logger: under gunicorn/gevent the root's
    # stderr handler can fail while an exception is active and dump noise.
    logger.propagate = False

    logger.addHandler(_get_file_handler(config.log_dir() / f"{text}.log"))
    syslog_handler = _get_syslog_handler(text)
    if syslog_handler is not None:
        logger.addHandler(syslog_handler)

    # Always log to stdout so records are visible via `docker logs`. The console
    # level follows MODULES_LOG_LEVEL (same knob as the rest of the stack) when
    # set, e.g. MODULES_LOG_LEVEL=INFO surfaces why individual products are
    # skipped. Otherwise the 'silent'/'debug' flags tune verbosity.
    env_level = getattr(logging, os.getenv("MODULES_LOG_LEVEL", "").upper(), None)
    stream_handler = logging.StreamHandler(sys.stdout)
    if isinstance(env_level, int):
        stream_handler.setLevel(env_level)
    else:
        stream_handler.setLevel(logging.WARNING if silent else (logging.DEBUG if debug else logging.INFO))
    logger.addHandler(stream_handler)

    return logger
