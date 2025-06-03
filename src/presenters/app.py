"""This module contains the main application factory function."""

import logging
from flask import Flask
from flask_cors import CORS
from managers import api_manager, presenters_manager

# fix for fontTools which is ignoring global logging settings and puts garbage into the logs
# after some time you can check if this is still needed (try generate some pdf and see logs)
for name in list(logging.root.manager.loggerDict):
    if name.startswith("fontTools"):
        logger = logging.getLogger(name)
        # print(f"{name}: level={logger.level}, effective={logger.getEffectiveLevel()}")
        logger.setLevel(logging.WARNING)
        for handler in logger.handlers:
            handler.setLevel(logging.WARNING)


def create_app():
    """Create and configure the Flask application.

    This function initializes the Flask application, applies CORS, and sets up
    the API and presenters managers. It returns the configured Flask app instance.
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        presenters_manager.initialize()

    return app
