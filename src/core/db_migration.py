#! /usr/bin/env python
"""Database migration script."""

import sys
from alembic import command
from flask import Flask
from flask_migrate import Migrate
from managers import db_manager


command_name = ""
if len(sys.argv) > 1:
    command_name = sys.argv[1]

app = Flask(__name__)
app.config.from_object("config.Config")

db_manager.initialize(app)
db_manager.wait_for_db(app)

migrate = Migrate(app=app, db=db_manager.db)
with app.app_context():
    config = migrate.get_config()
    if command_name == "history":
        command.history(config)
    elif command_name == "current":
        command.current(config)
    elif command_name == "upgrade":
        command.upgrade(config, revision="+1")
    elif command_name == "downgrade":
        command.downgrade(config, revision="-1")
    elif command_name == "revision":
        command.revision(config)
    else:
        command.upgrade(config, revision="head")
