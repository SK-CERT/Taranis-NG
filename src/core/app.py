"""This module contains the main application factory function."""

from flask import Flask
from flask_cors import CORS
from managers import (
    api_manager,
    auth_manager,
    cache_manager,
    db_manager,
    remote_manager,
    sse_manager,
    tagcloud_manager,
)


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.

    """
    app = Flask(__name__)
    app.config.from_object("config.Config")

    with app.app_context():
        CORS(app)

        db_manager.initialize(app)
        db_manager.create_tables()

        cache_manager.initialize(app)
        auth_manager.initialize(app)
        api_manager.initialize(app)
        sse_manager.initialize(app)
        remote_manager.initialize(app)
        tagcloud_manager.initialize(app)

    return app
