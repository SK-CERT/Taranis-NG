import os
from dotenv import load_dotenv


class Config:
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    SSL_VERIFICATION = os.getenv("SSL_VERIFICATION", False)
    TARANIS_NG_CORE_URL = os.getenv("TARANIS_NG_CORE_URL", "http://taranis")
    MODULE_ID = os.getenv("MODULE_ID", "Bots")
