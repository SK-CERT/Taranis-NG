#!/usr/bin/env python3
from os import path, chdir
import sys
from flask_sse import sse
from pathlib import Path

chdir(path.dirname(Path(__file__).resolve()))
sys.path.append(path.abspath('./'))
sys.path.append(path.abspath('../common'))

from app import create_app

app = create_app()
app.register_blueprint(sse, url_prefix='/sse')
