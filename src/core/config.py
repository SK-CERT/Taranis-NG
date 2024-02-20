"""This module contains the configuration class for Taranis-NG."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config(object):
    """Configuration class for Taranis-NG.

    This class holds the configuration settings for the Taranis-NG application.
    It provides access to environment variables and other configuration options.

    Attributes:
        REDIS_URL (str): The URL of the Redis server.
        DB_URL (str): The URL of the database server.
        DB_DATABASE (str): The name of the database.
        DB_USER (str): The username for the database connection.
        DB_PASSWORD (str): The password for the database connection.
        SQLALCHEMY_DATABASE_URI (str): The SQLAlchemy database URI.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Whether to track modifications in SQLAlchemy.
        SQLALCHEMY_ECHO (bool): Whether to echo SQL queries in SQLAlchemy.
        DB_POOL_SIZE (int): The size of the database connection pool.
        DB_POOL_RECYCLE (int): The time in seconds before a connection is recycled.
        DB_POOL_TIMEOUT (int): The maximum time in seconds to wait for a connection from the pool.
        JWT_SECRET_KEY (str): The secret key for JWT token generation.
        JWT_IDENTITY_CLAIM (str): The claim name for the JWT identity.
        JWT_ACCESS_TOKEN_EXPIRES (int): The expiration time in seconds for JWT access tokens.
        DEBUG (bool): Whether to enable debug mode.
        SECRET_KEY (str): The secret key for the application.
        OIDC_CLIENT_SECRETS (str): The path to the OIDC client secrets file.
        OIDC_ID_TOKEN_COOKIE_SECURE (bool): Whether to secure the OIDC ID token cookie.
        OIDC_REQUIRE_VERIFIED_EMAIL (bool): Whether to require verified email for OIDC.
        OIDC_USER_INFO_ENABLED (bool): Whether to enable OIDC user info endpoint.
        OIDC_OPENID_REALM (str): The OIDC realm.
        OIDC_SCOPES (list): The list of OIDC scopes.
        OIDC_INTROSPECTION_AUTH_METHOD (str): The OIDC introspection authentication method.
        OIDC_TOKEN_TYPE_HINT (str): The OIDC token type hint.
        OIDC_RESOURCE_CHECK_AUD (bool): Whether to check the audience of OIDC resource.
        OIDC_CLOCK_SKEW (int): The clock skew in seconds for OIDC.
        OPENID_LOGOUT_URL (str): The URL for OIDC logout.
    """

    REDIS_URL = os.getenv("REDIS_URL")

    DB_URL = os.getenv("DB_URL")
    DB_DATABASE = os.getenv("DB_DATABASE")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    if not DB_PASSWORD:
        with open(os.getenv("DB_PASSWORD_FILE"), "r") as file:
            DB_PASSWORD = file.read()

    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://{user}:{pw}@{url}/{db}".format(user=DB_USER, pw=DB_PASSWORD, url=DB_URL, db=DB_DATABASE)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("DEBUG_SQL", "false").lower() == "true"  # DEBUG SQL Queries

    if "DB_POOL_SIZE" in os.environ:
        DB_POOL_SIZE = os.getenv("DB_POOL_SIZE")
        DB_POOL_RECYCLE = os.getenv("DB_POOL_RECYCLE")
        DB_POOL_TIMEOUT = os.getenv("DB_POOL_TIMEOUT")

        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": int(DB_POOL_SIZE),
            "pool_recycle": int(DB_POOL_RECYCLE),
            "pool_pre_ping": True,
            "pool_timeout": int(DB_POOL_TIMEOUT),
        }

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        with open(os.getenv("JWT_SECRET_KEY_FILE"), "r") as file:
            JWT_SECRET_KEY = file.read()
    JWT_IDENTITY_CLAIM = "sub"
    JWT_ACCESS_TOKEN_EXPIRES = 14400
    DEBUG = True

    SECRET_KEY = "OKdbmczZKFiteHVgKXiwFXZxKsLyRNvt"
    OIDC_CLIENT_SECRETS = "client_secrets.json"
    OIDC_ID_TOKEN_COOKIE_SECURE = False
    OIDC_REQUIRE_VERIFIED_EMAIL = False
    OIDC_USER_INFO_ENABLED = True
    OIDC_OPENID_REALM = "taranis-ng"
    OIDC_SCOPES = ["openid"]
    OIDC_INTROSPECTION_AUTH_METHOD = "client_secret_post"
    OIDC_TOKEN_TYPE_HINT = "access_token"
    OIDC_RESOURCE_CHECK_AUD = True
    OIDC_CLOCK_SKEW = 560

    OPENID_LOGOUT_URL = os.getenv("OPENID_LOGOUT_URL")
