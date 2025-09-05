"""This module contains the main application factory function."""

import logging
import os

from flask import Flask
from flask_cors import CORS
from managers import api_manager, presenters_manager

# fix for fontTools which is ignoring global logging settings and puts garbage into the logs
# after some time you can check if this is still needed (try generate some pdf and see logs)
# https://github.com/fonttools/fonttools/issues/3371
module_logging_level_str = os.getenv("MODULES_LOG_LEVEL", "WARNING")
module_logging_level = getattr(logging, module_logging_level_str.upper(), logging.WARNING)
for name in logging.root.manager.loggerDict:
    if name.startswith("fontTools"):
        font_logger = logging.getLogger(name)
        font_logger.setLevel(module_logging_level)
        for handler in font_logger.handlers:
            handler.setLevel(module_logging_level)


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        presenters_manager.initialize()

    return app
