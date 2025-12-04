#! /usr/bin/env python
"""Database migration script."""

import sys

from alembic import command, script
from alembic.runtime.migration import MigrationContext
from flask import Flask
from flask_migrate import Migrate
from managers import db_manager
from migrations.regenerate_params import regenerate_all

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
        connection = db_manager.db.engine.connect()
        mc = MigrationContext.configure(connection)
        current_rev = mc.get_current_revision()
        script_dir = script.ScriptDirectory.from_config(config)
        head_rev = script_dir.get_current_head()
        if current_rev != head_rev:
            command.upgrade(config, revision="+1")
        else:
            print("Already at the latest revision:", head_rev, flush=True)  # noqa: T201
    elif command_name == "downgrade":
        command.downgrade(config, revision="-1")
    elif command_name == "revision":
        command.revision(config)
    elif command_name == "regenerate":
        with db_manager.db.engine.begin() as connection:
            regenerate_all(connection)
    else:
        if command_name != "":
            print("Unknown command:", command_name, flush=True)  # noqa: T201
        command.upgrade(config, revision="head")
    db_manager.db.engine.dispose()
