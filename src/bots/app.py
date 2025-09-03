"""Application factory for bots service."""

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from managers import api_manager, bots_manager, sse_manager


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    load_dotenv()

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        bots_manager.initialize()
        sse_manager.initialize()

    return app
