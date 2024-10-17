"""This file contains the logger configuration for the publishers module."""

import os
from shared.log import TaranisLogger

# setup logger level
taranis_logging_level_str = os.environ.get("LOG_LEVEL", "INFO")
modules_logging_level_str = os.environ.get("MODULES_LOG_LEVEL", "INFO")

logger = TaranisLogger(taranis_logging_level_str, modules_logging_level_str, True, os.environ.get("SYSLOG_ADDRESS"))
