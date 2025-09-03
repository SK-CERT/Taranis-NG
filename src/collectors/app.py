"""Collectors package initialization."""

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from managers import api_manager, collectors_manager


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
        collectors_manager.initialize()

    return app
