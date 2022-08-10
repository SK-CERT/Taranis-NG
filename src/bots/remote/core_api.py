import os
import json
import requests
from managers.log_manager import logger


class CoreApi:
    api_url = os.getenv("TARANIS_NG_CORE_URL")
    if api_url.endswith("/"):
        api_url = api_url[:-1]
    api_key = os.getenv("API_KEY")
    headers = {"Authorization": "Bearer " + api_key}

    @classmethod
    def get_bots_presets(cls, bot_type):
        try:
            response = requests.post(
                f"{cls.api_url}/api/v1/bots/bots-presets",
                json={"api_key": cls.api_key, "bot_type": bot_type},
                headers=cls.headers,
            )
            return response.json(), response.status_code
        except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
            return {}, 503

    @classmethod
    def get_news_items_data(cls, limit):
        try:
            response = requests.get(
                f"{cls.api_url}/api/v1/bots/news-item-data?limit={limit}",
                headers=cls.headers,
            )
            return response.json()
        except Exception:
            return None, 400

    @classmethod
    def update_news_item_attributes(cls, id, attributes):
        try:
            response = requests.put(
                f"{cls.api_url}/api/v1/bots/news-item-data/{id}/attributes",
                json=attributes,
                headers=cls.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    @classmethod
    def update_news_item_tags(cls, id, tags):
        try:
            response = requests.put(
                f"{cls.api_url}/api/v1/bots/news-item-data/{id}/tags",
                json=tags,
                headers=cls.headers,
            )
            return response.status_code
        except Exception:
            logger.log_debug_trace("update_news_item_tags failed")
            return None, 400

    @classmethod
    def delete_word_list_category_entries(cls, id, name):
        try:
            response = requests.delete(
                f"{cls.api_url}/api/v1/bots/word-list-categories/{id}/entries/{name}",
                headers=cls.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    @classmethod
    def update_word_list_category_entries(cls, id, name, entries):
        try:
            response = requests.put(
                f"{cls.api_url}/api/v1/bots/word-list-categories/{id}/entries/{name}",
                json=entries,
                headers=cls.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    @classmethod
    def get_categories(cls, id):
        try:
            response = requests.get(
                f"{cls.api_url}/api/v1/bots/word-list-categories/{id}",
                headers=cls.headers,
            )
            return response.json()
        except Exception:
            return None, 400

    @classmethod
    def add_word_list_category(cls, id, category):
        try:
            response = requests.put(
                f"{cls.api_url}/api/v1/bots/word-list-categories/{id}",
                json=category,
                headers=cls.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    @classmethod
    def get_news_items_aggregate(cls, source_group, limit):
        try:
            response = requests.get(
                f"{cls.api_url}/api/v1/bots/news-item-aggregates-by-group/{source_group}",
                headers=cls.headers,
            )
            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("get_news_items_aggregate failed")
            return None, 400

    @classmethod
    def news_items_grouping(cls, data):
        try:
            response = requests.put(
                f"{cls.api_url}/api/v1/bots/news-item-aggregates-group-action",
                json=data,
                headers=cls.headers,
            )
            return response.status_code
        except Exception:
            return None, 400
