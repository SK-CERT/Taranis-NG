"""This file contains the logger configuration for the module."""

import os
from shared.log import TaranisLogger

# setup logger level
taranis_logging_level_str = os.environ.get("TARANIS_LOG_LEVEL", "DEBUG")
modules_logging_level_str = os.environ.get("MODULES_LOG_LEVEL", "WARNING")
syslog_address = os.environ.get("SYSLOG_ADDRESS")


def create_logger(colored=True, log_prefix=None):
    """Create a new TaranisLogger with standard configuration."""
    logger = TaranisLogger(taranis_logging_level_str, modules_logging_level_str, colored, syslog_address)
    if log_prefix:
        logger.log_prefix = log_prefix
    return logger


logger = create_logger(colored=True, log_prefix="")
