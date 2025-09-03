"""This module contains the main application factory function."""

from flask import Flask
from flask_cors import CORS
from managers import api_manager, presenters_manager


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
