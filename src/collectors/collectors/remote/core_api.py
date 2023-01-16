import urllib
import requests
import base64
from collectors.managers.log_manager import logger
from collectors.config import Config

class CoreApi:
    def __init__(self):
        self.api_url = Config.TARANIS_NG_CORE_URL
        self.api_key = Config.API_KEY
        self.headers = self.get_headers()
        self.node_id = self.get_node_id()
        self.verify = Config.SSL_VERIFICATION

    def get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def get_node_id(self) -> str:
        uid = self.api_url + self.api_key
        return base64.urlsafe_b64encode(uid.encode("utf-8")).decode("utf-8")

    def get_osint_sources(self, collector_type):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/collectors/{self.node_id}/osint-sources?collector_type={urllib.parse.quote(collector_type)}",
                headers=self.headers,
                verify=self.verify
            )

            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Can't get OSINT Sources")
            return None, 400

    def register_node(self, collectors_info):
        try:
            response, status = self.get_collector_status()
            if status == 200:
                return response, status
            node_info = {
                "id": self.node_id,
                "name": Config.NODE_NAME,
                "description": Config.NODE_DESCRIPTION,
                "api_url": Config.NODE_URL,
                "api_key": Config.API_KEY,
                "collectors_info": collectors_info,
            }

            response = requests.post(
                f"{self.api_url}/api/v1/collectors/node",
                json=node_info,
                headers=self.headers,
                verify=self.verify,
            )

            if response.status_code != 200:
                logger.log_debug(f"Can't register Collector node: {response.text}")
                return None, 400

            return response.json(), response.status_code
        except Exception as e:
            logger.log_debug("Can't register Collector node")
            logger.log_debug(str(e))
            return None, 400

    def get_collector_status(self):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/collectors/{self.node_id}",
                headers=self.headers,
                verify=self.verify
            )

            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Cannot update Collector status")
            return None, 400

    def add_news_items(self, news_items):
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/collectors/news-items",
                json=news_items,
                headers=self.headers,
                verify=self.verify
            )

            return response.status_code
        except Exception:
            logger.log_debug_trace("Cannot add Newsitem")
            return None, 400
