from flask import Flask
from flask_cors import CORS
from dotenv import dotenv_values
import bots.managers as managers


def create_app(dotenv_path="."):
    app = Flask(__name__)
    app.config.from_object("bots.config.Config")
    app.config.from_mapping(dotenv_values(dotenv_path=dotenv_path))

    with app.app_context():
        CORS(app)

        managers.api_manager.initialize(app)
        managers.bots_manager.initialize()
        managers.sse_manager.initialize()
    return app


app = create_app()
