from flask import Flask
from flask_cors import CORS

from bots.managers import api_manager, bots_manager, time_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object("bots.config.Config")

    with app.app_context():
        CORS(app)

        api_manager.initialize(app)
        bots_manager.initialize()
        bots_manager.register_bot_node()
        time_manager.run_scheduler()
    return app
