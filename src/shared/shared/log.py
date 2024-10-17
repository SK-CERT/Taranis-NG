"""This module contains the TaranisLogger class."""

import logging.handlers
import sys
import socket
import logging
import traceback
from typing import Optional


class TaranisLogger:
    """A logger class for Taranis-NG.

    Parameters:
        taranis_logging_level_str (str): The logging level for the Taranis logger as a string.
        modules_logging_level_str (str): The logging level for other modules as a string.
        colored (bool): Whether to use colored output.
        syslog_address (Optional[tuple]): The address of the syslog server (optional).

    Attributes:
        logger (logging.Logger): The logger object.

    Methods:
        debug(message): Log a debug message.
        error(message): Log an error message.
        exception(message): Log an exception message with a traceback.
        info(message): Log an info message.
        warning(message): Log a warning message.
        critical(message): Log a critical message.
    """

    def __init__(self, taranis_logging_level_str: str, modules_logging_level_str: str, colored: bool, syslog_address: Optional[tuple]):
        """Initialize a Log object.

        Parameters:
            taranis_logging_level_str (str): The logging level for the Taranis logger.
            modules_logging_level_str (str): The logging level for other modules.
            colored (bool): Indicates whether to use colored output.
            syslog_address (Optional[tuple]): The address of the syslog server, if applicable.
        """
        # Create separate stream handlers for each logger
        taranis_stream_handler = logging.StreamHandler(stream=sys.stdout)
        module_stream_handler = logging.StreamHandler(stream=sys.stdout)
        if colored:
            taranis_stream_handler.setFormatter(TaranisLogFormatter())
            module_stream_handler.setFormatter(TaranisLogFormatter())
        else:
            taranis_stream_handler.setFormatter(logging.Formatter("[%(levelname)s] - %(message)s"))
            module_stream_handler.setFormatter(logging.Formatter("[%(levelname)s] - %(message)s"))

        sys_log_handler = None
        if syslog_address:
            try:
                sys_log_handler = logging.handlers.SysLogHandler(address=syslog_address, socktype=socket.SOCK_STREAM)
            except Exception:
                print("Unable to connect to syslog server!")

        # Configure the root logger for all other modules
        module_logger = logging.getLogger()
        module_logger.handlers.clear()
        module_logging_level = getattr(logging, modules_logging_level_str.upper(), logging.INFO)
        module_logger.setLevel(module_logging_level)
        module_logger.addHandler(module_stream_handler)
        if sys_log_handler:
            module_logger.addHandler(sys_log_handler)

        # Configure the "taranis" logger
        taranis_logger = logging.getLogger("taranis")
        taranis_logger.handlers.clear()
        taranis_logging_level = getattr(logging, taranis_logging_level_str.upper(), logging.INFO)
        taranis_logger.setLevel(taranis_logging_level)
        taranis_logger.addHandler(taranis_stream_handler)
        if sys_log_handler:
            taranis_logger.addHandler(sys_log_handler)

        # Prevent the root logger from propagating messages to the taranis logger
        taranis_logger.propagate = False

        # Set the primary logger to taranis
        self.logger = taranis_logger

    def debug(self, message):
        """Log a debug message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.debug(message)

    def error(self, message=None):
        """Log an exception with an optional message.

        Parameters:
            message (str, optional): An optional message to include in the log. Defaults to None.
        """
        self.logger.error(message)

    def exception(self, message=None):
        """Log an exception with an optional message.

        Parameters:
            message (str, optional): An optional message to include in the log. Defaults to None.
        """
        self.logger.exception(message, traceback.format_exc())

    def info(self, message):
        """Log an info message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.info(message)

    def warning(self, message):
        """Log an warning message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.warning(message)

    def critical(self, message):
        """Log a critical message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.critical(message)


class TaranisLogFormatter(logging.Formatter):
    """Custom log formatter for Taranis log messages.

    Parameters:
        format_string (str): The format string for log messages.
        FORMATS (dict): A dictionary mapping log levels to format strings.
    Methods:
        format(record): Formats the log record.
    """

    def __init__(self):
        """Initialize a TaranisLogFormatter object."""
        grey_bold = "\x1b[1;38;5;246m"
        cyan_bold = "\x1b[1;36m"
        yellow_bold = "\x1b[1;38;5;214m"
        red_bold = "\x1b[1;31m"
        white_bold_on_red = "\x1b[1;37m\x1b[41m"
        reset = "\x1b[0m"
        self.format_string = "[%(levelname)s] - %(message)s"
        self.FORMATS = {
            logging.DEBUG: grey_bold + self.format_string + reset,
            logging.INFO: cyan_bold + self.format_string + reset,
            logging.WARNING: yellow_bold + self.format_string + reset,
            logging.ERROR: red_bold + self.format_string + reset,
            logging.CRITICAL: white_bold_on_red + self.format_string + reset,
        }

    def format(self, record):
        """Format the log record using the specified formatter.

        Parameters:
            record (logging.LogRecord): The log record to be formatted.
        Returns:
            str: The formatted log record.
        """
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
