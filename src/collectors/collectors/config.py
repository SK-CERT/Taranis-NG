import os
from dotenv import load_dotenv


class Config(object):
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    SSL_VERIFICATION = os.getenv("SSL_VERIFICATION", False)
    TARANIS_NG_CORE_URL = os.getenv("TARANIS_NG_CORE_URL", "http://taranis")
    MODULE_ID = os.getenv("MODULE_ID", "Collectors")
    COLLECTOR_CONFIG_FILE = os.getenv("COLLECTOR_CONFIG_FILE")
    CORE_STATUS_UPDATE_INTERVAL = os.getenv("CORE_STATUS_UPDATE_INTERVAL", 120)
    COLLECTOR_LOADABLE_COLLECTORS = os.getenv("COLLECTOR_LOADABLE_COLLECTORS", default="RSS,Email,Slack,Twitter,Web,Atom,Manual").split(",")
