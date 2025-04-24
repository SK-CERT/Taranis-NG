"""This module contains the TaranisLogger class."""

import logging.handlers
import sys
import socket
import logging
from typing import Optional, Dict, Tuple


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

        self.log_level_mapping: Dict[str, Tuple[Optional[str], Optional[str]]] = {}  # Mapping of log levels to target attributes
        self.dynamic_target = None  # Dynamic target object (e.g., source)
        self.module_name = None  # Module name for log messages

        if colored:
            taranis_stream_handler.setFormatter(TaranisLogFormatter())
            module_stream_handler.setFormatter(TaranisLogFormatter())
        else:
            taranis_stream_handler.setFormatter(logging.Formatter("[%(levelname)s]  %(message)s"))
            module_stream_handler.setFormatter(logging.Formatter("[%(levelname)s]  %(message)s"))

        sys_log_handler = None
        if syslog_address:
            try:
                sys_log_handler = logging.handlers.SysLogHandler(address=syslog_address, socktype=socket.SOCK_STREAM)
            except Exception as ex:
                print(f"Unable to connect to syslog server: {ex}")

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

    def _get_log_prefix(self) -> str:
        """Retrieve the value of the log_prefix attribute from the calling class.

        Returns:
            str: The value of log_prefix or a default if not set.
        """
        try:
            import inspect

            frame = inspect.currentframe()
            while frame:
                # Get the 'self' object from the calling frame
                caller = frame.f_locals.get("self")
                if caller and hasattr(caller, "log_prefix"):
                    return getattr(caller, "log_prefix", "")
                frame = frame.f_back
        except Exception:
            pass

        # Default log prefix if none is found
        return ""

    def _format_message(self, message: str) -> str:
        """Format the log message to include the log_prefix attribute.

        Parameters:
            message (str): The original log message.

        Returns:
            str: The formatted log message.
        """
        log_prefix = self._get_log_prefix()
        if log_prefix:
            whole_message = f"{log_prefix}: {message}"
        else:
            whole_message = message
        return whole_message

    def set_log_level_target(self, level: str, attribute: Optional[str]):
        """Set the target attribute for a specific log level.

        Parameters:
            level (str): The log level (e.g., "debug", "error", "exception", etc.).
            attribute (str): The attribute of the dynamic target where the message should be stored.
        """
        self.log_level_mapping[level.lower()] = attribute

    def set_dynamic_target(self, target: Optional[object]):
        """Set the dynamic target object (e.g., source).

        Parameters:
            target (object): The dynamic target object.
        """
        self.dynamic_target = target

    def _store_message(self, level: str, message: str):
        """Store the message in the target attribute for the given log level.

        Parameters:
            level (str): The log level (e.g., "debug", "error", "exception", etc.).
            message (str): The message to be stored.
        """
        attribute = self.log_level_mapping.get(level.lower())
        if self.dynamic_target is not None and attribute is not None:
            setattr(self.dynamic_target, attribute, message)

    def debug(self, message):
        """Log a debug message.

        Parameters:
            message (str): The message to be logged.
        """
        self._store_message("debug", message)
        self.logger.debug(self._format_message(message))

    def error(self, message):
        """Log an error message.

        Parameters:
            message (str): The message to be logged.
        """
        self._store_message("error", message)
        self.logger.error(self._format_message(message))

    def exception(self, message="Traceback:"):
        """Log an exception with an optional message.

        Parameters:
            message (str, optional): An optional message to include in the log. Defaults to "Traceback:".
        """
        self._store_message("exception", message)
        self.logger.exception(self._format_message(message))

    def info(self, message):
        """Log an info message.

        Parameters:
            message (str): The message to be logged.
        """
        self._store_message("info", message)
        self.logger.info(self._format_message(message))

    def warning(self, message):
        """Log an warning message.

        Parameters:
            message (str): The message to be logged.
        """
        self._store_message("warning", message)
        self.logger.warning(self._format_message(message))

    def critical(self, message):
        """Log a critical message.

        Parameters:
            message (str): The message to be logged.
        """
        self._store_message("critical", message)
        self.logger.critical(self._format_message(message))


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
        # same colors are used in gunicorn_conf.py
        grey_bold = "\x1b[1;38;5;246m"
        cyan_bold = "\x1b[1;36m"
        yellow_bold = "\x1b[1;38;5;214m"
        red_bold = "\x1b[1;31m"
        white_bold_on_red = "\x1b[1;37m\x1b[41m"
        reset = "\x1b[0m"
        self.format_string = "[%(levelname)s]  %(message)s"
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
