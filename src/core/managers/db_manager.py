"""Database manager module."""

import socket
import time
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def initialize(app):
    """Initialize the database with the given Flask application.

    This function sets up the database connection for the provided Flask app
    by initializing the database extension with the app instance.
    Args:
        app (Flask): The Flask application instance to initialize the database with.
    """
    db.init_app(app)


def create_tables():
    """Create all database tables defined in the application's models.

    This function uses the SQLAlchemy `create_all` method to create all tables
    that are defined in the application's database models. It should be called
    during the initial setup of the application to ensure that the database
    schema is properly initialized.
    """
    db.create_all()


def wait_for_db(app, retries=5, delay=1):
    """Wait for the database to be ready for connection.

    This function attempts to connect to the database specified in the app's configuration.
    It will retry the connection a specified number of times with an exponential backoff delay
    between attempts.
    Args:
        app: The application instance containing the configuration with the database URL.
        retries (int, optional): The number of times to retry the connection. Defaults to 5.
        delay (int, optional): The initial delay between retries in seconds. Defaults to 1.
    Raises:
        ConnectionError: If the database is not ready after the specified number of retries.
    """
    db_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    attempt = 0
    while attempt < retries:
        try:
            db_socket.connect((app.config.get("DB_URL"), 5432))
            db_socket.close()
            return
        except socket.error as error:
            attempt += 1
            print(f"Waiting for database: {error}. Attempt {attempt} of {retries}.")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    print("Database is not ready after multiple attempts.")
    raise ConnectionError("Database is not ready after multiple attempts.")
