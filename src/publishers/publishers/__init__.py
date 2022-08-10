from flask import Flask
from flask_cors import CORS

from publishers.managers import api_manager, publishers_manager

app = Flask(__name__)

with app.app_context():
    CORS(app)

    api_manager.initialize(app)
    publishers_manager.initialize()

