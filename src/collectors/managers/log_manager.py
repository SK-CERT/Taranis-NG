"""This file contains the logger configuration for the collectors module."""

import os
from shared.log import TaranisLogger

# setup logger level
logging_level_str = os.environ.get("LOG_LEVEL", "INFO")

# custom module ID to append to log messages
module_id = os.environ.get("MODULE_ID", None)

logger = TaranisLogger(module_id, logging_level_str, True, False, os.environ.get("SYSLOG_ADDRESS"))
