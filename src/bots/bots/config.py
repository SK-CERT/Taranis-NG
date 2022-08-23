import os


class Config:
    API_KEY = os.getenv("API_KEY")
    SSL_VERIFICATION = os.getenv("SSL_VERIFICATION", False)
    TARANIS_NG_CORE_URL = os.getenv("TARANIS_NG_CORE_URL")
