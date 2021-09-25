import requests
import os


class CoreApi:
    api_url = os.getenv('TARANIS_NG_CORE_URL')
    api_key = os.getenv('API_KEY')
    headers = {'Authorization': 'Bearer ' + api_key}

    @classmethod
    def get_osint_sources(cls, collector_type):
        try:
            response = requests.post(cls.api_url + '/api/collectors/sources', json={'api_key': cls.api_key,
                                                                                'collector_type': collector_type},
                                 headers=cls.headers)
            return response.json(), response.status_code
        except:
            return None, 400

    @classmethod
    def add_news_items(cls, news_items):
        try:
            response = requests.post(cls.api_url + '/api/assess/newsitems/add', json=news_items,
                                 headers=cls.headers)
            return response.status_code
        except:
            return 400
