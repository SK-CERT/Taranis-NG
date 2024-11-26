#! /usr/bin/env python
"""Database migration script."""

import socket
import time
from flask import Flask
from flask_migrate import Migrate

from managers import db_manager
from managers.log_manager import logger
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
    except socket.error as error:
        logger.warning(f"Waiting for database: {error}")
        time.sleep(0.1)


@app.cli.command("migrate")
def migrate():
    """Run the database migrations."""
    Migrate(app=app, db=db_manager.db)
