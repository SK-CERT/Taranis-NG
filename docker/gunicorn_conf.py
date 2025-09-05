"""This module contains the configuration settings for Gunicorn.

The following environment variables are used:
- WORKERS_PER_CORE: Number of workers per CPU core. Default is 2.
- WEB_CONCURRENCY: Number of worker processes. Default is 1.
- HOST: The host IP address to bind to. Default is 0.0.0.0.
- PORT: The port number to bind to. Default is 80.
- BIND: The bind address and port. If not provided, it will use the host and port values.
- MODULES_LOG_LEVEL: The log level. Default is 'WARNING'.

The module defines the following variables:
- loglevel: The log level to be used by Gunicorn.
- workers: The number of worker processes.
- bind: The bind address and port.
- keepalive: The keepalive timeout.
- errorlog: The error log file. '-' means stderr.

For debugging and testing purposes, the module also defines the following variables:
- log_data: A dictionary containing the log level, number of workers, bind address and port, workers per core, host, and port.
"""

import logging
import multiprocessing
import os
import re
import typing

from gunicorn.glogging import Logger

workers_per_core = int(os.getenv("WORKERS_PER_CORE", "2"))
web_concurrency = int(os.getenv("WEB_CONCURRENCY", "0"))
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "80")
bind_env = os.getenv("BIND", None)
use_loglevel = os.getenv("MODULES_LOG_LEVEL", "WARNING")
use_bind = bind_env or f"{host}:{port}"

if not web_concurrency or web_concurrency <= 0:
    web_concurrency = workers_per_core * multiprocessing.cpu_count()

# Gunicorn config variables
loglevel = use_loglevel.lower()
workers = web_concurrency
bind = use_bind
keepalive = 120
errorlog = "-"


class CustomGunicornLogger(Logger):
    """Override Gunicorn logger to customize log output."""

    def setup(self, cfg) -> None:
        """Set up a custom logger."""
        super().setup(cfg)
        filter_strings = ["Closing connection.", "/isalive", "OPTIONS /api"]

        class RemoveStrings(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                return not any(x in record.getMessage() for x in filter_strings)

        class ColorizedFormatter(logging.Formatter):
            COLORS: typing.ClassVar[dict[str, str]] = {
                "DEBUG": "\x1b[1;38;5;246m",
                "INFO": "\x1b[1;36m",
                "WARNING": "\x1b[1;38;5;214m",
                "ERROR": "\x1b[1;31m",
                "CRITICAL": "\x1b[1;37m\x1b[41m",
            }
            RESET: typing.ClassVar[str] = "\x1b[0m"

            def format(self, record: logging.LogRecord) -> str:
                level_color = self.COLORS.get(record.levelname, self.RESET)
                record.levelname = f"{level_color}{record.levelname}{self.RESET}"  # Colorize level name
                return super().format(record)

        # Filter to remove strings from logger
        for handler in self.error_log.handlers:
            handler.addFilter(RemoveStrings())
        # Formatter to remove timestamps and add color
        formatter = ColorizedFormatter("[%(levelname)s]  %(message)s")
        for handler in self.error_log.handlers:
            handler.setFormatter(formatter)


# Comment this line to get default Gunicorn logger (KeepAlive records, extra Timestamps in output...)
logger_class = CustomGunicornLogger


def pre_request(worker, req) -> None:
    """Log formatted request details just before a worker processes the request."""
    censored = {"jwt=", "api_key="}
    query = req.query
    for cen in censored:
        search = cen + r"(.*?)(?=&|$)"
        found = re.search(search, query)
        if found:
            query = query.replace(found.group(1), r"•••••")
    worker.log.debug("%s %s  %s", req.method, req.path, query)  # add to output also query data
