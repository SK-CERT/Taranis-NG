"""This module contains the main application factory function."""

from flask import Flask
from flask_cors import CORS
from managers import db_manager, auth_manager, api_manager, sse_manager, remote_manager, tagcloud_manager
from model import *  # noqa F403 just until all new model classes are used regularly


def create_app():
    """Create and configure the Flask application.

    This function initializes the Flask application, configures it using the
    settings from the "config.Config" object, and sets up various managers
    and services required by the application.
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")

    with app.app_context():
        CORS(app)

        db_manager.initialize(app)
        db_manager.create_tables()

        auth_manager.initialize(app)
        api_manager.initialize(app)
        sse_manager.initialize(app)
        remote_manager.initialize(app)
        tagcloud_manager.initialize(app)

        # import test

    return app
