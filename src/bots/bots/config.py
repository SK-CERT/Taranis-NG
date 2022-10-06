import os
from typing import List, Tuple, Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    API_KEY: str
    SSL_VERIFICATION: bool = False
    TARANIS_NG_CORE_URL: str = "http://taranis"
    MODULE_ID: str = "Bots"
    COLORED_LOGS: bool = True
    DEBUG: bool = False

    NODE_NAME: str = "MyBot"
    NODE_DESCRIPTION: str = ""
    NODE_URL: str = "http://bots"
    BOTS_LOADABLE_BOTS: List[str] = ["Analyst", "Grouping", "NLP", "Tagging"]
    SYSLOG_ADDRESS: Optional[Tuple[str, int]]
    GUNICORN: bool = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")


Config = Settings()
