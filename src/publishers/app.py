"""App factory for publishers service."""

from flask import Flask
from managers import api_manager, publishers_manager


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        app: The configured Flask application.
    """
    app = Flask(__name__)

    with app.app_context():
        api_manager.initialize(app)
        publishers_manager.initialize()

    return app
