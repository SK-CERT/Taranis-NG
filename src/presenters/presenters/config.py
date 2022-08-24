import os
from dotenv import load_dotenv


class Config:
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    SSL_VERIFICATION = os.getenv("SSL_VERIFICATION")
