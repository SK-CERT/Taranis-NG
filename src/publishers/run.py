#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from os import path, chdir
import sys
from pathlib import Path

chdir(path.dirname(Path(__file__).resolve()))
sys.path.append(path.abspath('./'))
sys.path.append(path.abspath('../common'))

from app import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
