from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str
    MODULE_ID: str = "Core"
    DEBUG: bool = False
    SECRET_KEY: str

    JWT_IDENTITY_CLAIM: str = "sub"
    JWT_ACCESS_TOKEN_EXPIRES: int = 14400
    REDIS_URL: str = "redis://localhost"

    DB_URL: str = "localhost"
    DB_DATABASE: str = "taranis"
    DB_USER: str = "taranis"
    DB_PASSWORD: str = "supersecret"
    SQLALCHEMY_SCHEMA: str = "postgresql+psycopg2"
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_DATABASE_URI: str = f"{SQLALCHEMY_SCHEMA}://{DB_USER}:{DB_PASSWORD}@{DB_URL}/{DB_DATABASE}"

    # if "postgresql" in SQLALCHEMY_DATABASE_URI:
    #     DB_POOL_SIZE: int = 10
    #     DB_POOL_RECYCLE: int = 300
    #     DB_POOL_TIMEOUT: int = 5

    #     SQLALCHEMY_ENGINE_OPTIONS: dict = {
    #         "pool_size": DB_POOL_SIZE,
    #         "pool_recycle": DB_POOL_RECYCLE,
    #         "pool_pre_ping": True,
    #         "pool_timeout": DB_POOL_TIMEOUT,
    #     }

    OPENID_CLIENT_ID: Optional[str]
    OPENID_CLIENT_SECRET: Optional[str]
    OPENID_METADAT_URL: str = "http://keycloak/realms/master/.well-known/openid-configuration"


Config = Settings()
