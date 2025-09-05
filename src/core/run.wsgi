#!/usr/bin/python3
"""WSGI entry point for the Taranis-NG application.

This script sets up the environment and initializes the WSGI application.

Environment Variables:
- DB_URL: URL of the database.
- DB_DATABASE: Name of the database.
- DB_USER: Username for the database.
- DB_PASSWORD: Password for the database.
- JWT_SECRET_KEY: Secret key for JWT authentication.

Modules:
- sys: Provides access to some variables used or maintained by the interpreter.
- os: Provides a way of using operating system dependent functionality.
- dotenv: Loads environment variables from a .env file.
- app: Contains the create_app function to initialize the application.

Functions:
- create_app: Initializes and returns the WSGI application.

Usage:
- This script is intended to be used as the entry point for a WSGI server.
"""

import sys
from pathlib import Path

from app import create_app
from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path.cwd()))

load_dotenv(find_dotenv())

application = create_app()
