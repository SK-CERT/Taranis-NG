#! /usr/bin/env python
"""This script is responsible for performing database migrations for the Taranis-NG application.

It initializes the Flask application, configures the database manager, and waits for the database to be ready.
Once the database is ready, it performs the necessary migrations using Flask-Migrate.
"""
import socket
import time
from flask import Flask
from flask_migrate import Migrate

from managers import db_manager
from model import *  # noqa: F401, F403

app = Flask(__name__)
app.config.from_object("config.Config")

db_manager.initialize(app)

# wait for the database to be ready
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((app.config.get("DB_URL"), 5432))
        s.close()
        break
    except socket.error:
        time.sleep(0.1)

migrate = Migrate(app=app, db=db_manager.db)

if __name__ == "__main__":
    app.run()
