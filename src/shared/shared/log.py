"""This module contains the TaranisLogger class."""

import logging.handlers
import sys
import socket
import logging
from typing import Optional


class TaranisLogger:
    """A logger class for Taranis-NG.

    Parameters:
        module (str): The name of the module using the logger.
        logging_level_str (str): The logging level as a string.
        colored (bool): Whether to use colored output.
        gunicorn (bool): Whether the logger is used in a Gunicorn environment.
        syslog_address (Optional[tuple]): The address of the syslog server (optional).

    Attributes:
        logger (logging.Logger): The logger object.

    Methods:
        debug(message): Log a debug message.
        exception(message): Log a debug message with a traceback.
        info(message): Log an info message.
        critical(message): Log a critical message.
    """

    def __init__(self, logging_level_str: str, colored: bool, gunicorn: bool, syslog_address: Optional[tuple]):
        """Initialize a Log object.

        Parameters:
            module (str): The name of the module.
            logging_level_str (str): The logging level as a string.
            colored (bool): Indicates whether to use colored output.
            gunicorn (bool): Indicates whether the logger is used in a Gunicorn environment.
            syslog_address (Optional[tuple]): The address of the syslog server, if applicable.
        """
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        if colored:
            stream_handler.setFormatter(TaranisLogFormatter())
        else:
            stream_handler.setFormatter(logging.Formatter("[%(levelname)s] - %(message)s"))
        sys_log_handler = None
        if syslog_address:
            try:
                sys_log_handler = logging.handlers.SysLogHandler(address=syslog_address, socktype=socket.SOCK_STREAM)
            except Exception:
                print("Unable to connect to syslog server!")

        lloggers = [logging.getLogger()]

        if gunicorn:
            lloggers = [logging.getLogger("gunicorn.error")]

        for llogger in lloggers:
            llogger.handlers.clear()
            logging_level = getattr(logging, logging_level_str.upper(), logging.INFO)
            llogger.setLevel(logging_level)

            if sys_log_handler:
                llogger.addHandler(sys_log_handler)

            llogger.addHandler(stream_handler)

        self.logger = lloggers[0]

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
        self.logger.exception(message)

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
        module (str): The name of the module.
        format_string (str): The format string for log messages.
        FORMATS (dict): A dictionary mapping log levels to format strings.
    Methods:
        format(record): Formats the log record.
    """

    def __init__(self):
        """Initialize a Log object.

        Parameters:
            module (str): The name of the module.
            format_string (str): The format string used for logging messages.
            FORMATS (dict): A dictionary mapping logging levels to format strings.
        """
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
