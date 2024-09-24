"""This file contains the logger configuration for the presenters module."""

import os
from shared.log import TaranisLogger

# setup logger level
logging_level_str = os.environ.get("LOG_LEVEL", "INFO")

logger = TaranisLogger(logging_level_str, True, False, os.environ.get("SYSLOG_ADDRESS"))
