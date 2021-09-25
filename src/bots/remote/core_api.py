import requests
import os


class CoreApi:
    api_url = os.getenv('TARANIS_NG_CORE_URL')
    api_key = os.getenv('API_KEY')
    headers = {'Authorization': 'Bearer ' + api_key}

    @classmethod
    def get_bots_presets(cls, bot_type):
        try:
            response = requests.post(cls.api_url + '/api/bots/presets', json={'api_key': cls.api_key,
                                                                              'bot_type': bot_type},
                                     headers=cls.headers)
            return response.json(), response.status_code
        except requests.exceptions.ConnectionError:
            return {}, 503

    @classmethod
    def get_news_items_data(cls):
        response = requests.get(cls.api_url + '/api/assess/newsitemdata', headers=cls.headers)
        return response.json()

    @classmethod
    def update_news_item_data(cls, id, data):
        response = requests.put(cls.api_url + '/api/assess/newsitemdata/' + id, json=data, headers=cls.headers)
        return response.status_code