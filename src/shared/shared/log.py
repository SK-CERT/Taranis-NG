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
        module (str): The name of the module using the logger.
        logging_level_str (str): The logging level as a string.
        colored (bool): Whether to use colored output.
        gunicorn (bool): Whether the logger is used in a Gunicorn environment.
        syslog_address (Optional[tuple]): The address of the syslog server (optional).

    Attributes:
        logger (logging.Logger): The logger object.

    Methods:
        log_debug(message): Log a debug message.
        debug(message): Log a debug message.
        log_debug_trace(message): Log a debug message with a traceback.
        exception(message): Log a debug message with a traceback.
        log_info(message): Log an info message.
        info(message): Log an info message.
        log_critical(message): Log a critical message.
        critical(message): Log a critical message.
        log_collector_activity_debug(collector_type, source_name, message): Log a debug message for collector activity.
        log_collector_activity_info(collector_type, source_name, message): Log an info message for collector activity.
        log_system_activity_debug(module, message): Log a debug message for system activity.
        log_system_activity_info(module, message): Log an info message for system activity.
        log_bot_activity_debug(bot, message): Log a debug message for bot activity.
        log_bot_activity_info(bot, message): Log an info message for bot activity.
    """

    def __init__(self, module: str, logging_level_str: str, colored: bool, gunicorn: bool, syslog_address: Optional[tuple]):
        """Initialize a Log object.

        Parameters:
            module (str): The name of the module.
            logging_level_str (str): The logging level as a string.
            colored (bool): Indicates whether to use colored output.
            gunicorn (bool): Indicates whether the logger is used in a Gunicorn environment.
            syslog_address (Optional[tuple]): The address of the syslog server, if applicable.
        """
        self.module = module
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        if colored:
            stream_handler.setFormatter(TaranisLogFormatter(module))
        else:
            stream_handler.setFormatter(logging.Formatter(f"[{module}] [%(levelname)s] - %(message)s"))
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

    log_debug = debug

    def debug_trace(self, message=None):
        """Log a debug message along with the traceback of the current exception.

        Parameters:
            message (str, optional): The debug message to be logged.
        """
        if message:
            self.logger.debug(message)
        self.logger.debug(traceback.format_exc())

    log_debug_trace = debug_trace

    def exception(self, message=None):
        """Log an exception with an optional message.

        Parameters:
            message (str, optional): An optional message to include in the log. Defaults to None.
        """
        self.log_debug_trace(message)

    log_exception = exception

    def info(self, message):
        """Log an info message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.info(message)

    log_info = info

    def warning(self, message):
        """Log an warning message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.warning(message)

    log_warning = warning

    def critical(self, message):
        """Log a critical message.

        Parameters:
            message (str): The message to be logged.
        """
        self.logger.critical(message)

    log_critical = critical

    def log_collector_activity_debug(self, collector_type, source_name, message):
        """Log the debug activity of a collector.

        Parameters:
            collector_type (str): The type of the collector.
            source_name (str): The name of the source.
            message (str): The debug message.
        """
        self.logger.debug(f"COLLECTOR {collector_type} '{source_name}': {message}")

    def log_collector_activity_info(self, collector_type, source_name, message):
        """Log the info activity of a collector.

        Parameters:
            collector_type (str): The type of the collector.
            source_name (str): The name of the source.
            message (str): The info message.
        """
        self.logger.info(f"COLLECTOR {collector_type} '{source_name}': {message}")

    def log_system_activity_debug(self, module, message):
        """Log a debug message for system activity.

        Parameters:
            module (str): The name of the module.
            message (str): The message to be logged.
        """
        self.logger.debug(f"[{module}] {message}")

    def log_system_activity_info(self, module, message):
        """Log an info message for system activity.

        Parameters:
            module (str): The name of the module.
            message (str): The message to be logged.
        """
        self.logger.info(f"[{module}] {message}")

    def log_bot_activity_debug(self, bot, message):
        """Log the debug activity of a bot.

        Parameters:
            bot (str): The name of the bot.
            message (str): The debug message to be logged.
        """
        self.logger.debug(f"BOT '{bot}': {message}")

    def log_bot_activity_info(self, bot, message):
        """Log the info activity of a bot.

        Parameters:
            bot (str): The name of the bot.
            message (str): The info message to be logged.
        """
        self.logger.info(f"BOT '{bot}': {message}")


class TaranisLogFormatter(logging.Formatter):
    """Custom log formatter for Taranis log messages.

    Parameters:
        module (str): The name of the module.
        format_string (str): The format string for log messages.
        FORMATS (dict): A dictionary mapping log levels to format strings.
    Methods:
        format(record): Formats the log record.
    """

    def __init__(self, module):
        """Initialize a Log object.

        Parameters:
            module (str): The name of the module.
            format_string (str): The format string used for logging messages.
            FORMATS (dict): A dictionary mapping logging levels to format strings.
        """
        grey = "\x1b[38;20m"
        cyan_bold = "\x1b[1;36m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        red_bold = "\x1b[1;31m"
        reset = "\x1b[0m"
        self.module = module
        self.format_string = f"[{self.module}] [%(levelname)s] - %(message)s"
        self.FORMATS = {
            logging.DEBUG: grey + self.format_string + reset,
            logging.INFO: cyan_bold + self.format_string + reset,
            logging.WARNING: yellow + self.format_string + reset,
            logging.ERROR: red + self.format_string + reset,
            logging.CRITICAL: red_bold + self.format_string + reset,
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
