#!/usr/bin/env python3
from os import path, chdir
import sys
import os
from pathlib import Path

chdir(path.dirname(Path(__file__).resolve()))
sys.path.append(path.abspath('./'))
sys.path.append(path.abspath('../common'))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
