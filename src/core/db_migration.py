from os import path, chdir
import sys

chdir(path.dirname(path.abspath(__file__)))
sys.path.append(path.abspath('.'))
sys.path.append(path.abspath('../taranis-ng-common'))

from flask import Flask
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from managers import db_manager
from model import *

app = Flask(__name__)
app.config.from_object('config.Config')

db_manager.initialize(app)

migrate = Migrate(app=app, db=db_manager.db)

manager = Manager(app=app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
