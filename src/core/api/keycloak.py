import os
import re
from os import environ

import requests
from flask import request, Response
from flask_restful import Resource

from managers.auth_manager import no_auth
from packaging import version

class Keycloak(Resource):
    keycloak_url = re.escape(str(environ['TARANIS_NG_KEYCLOAK_URL']))
    realm = str(environ['KEYCLOAK_REALM_NAME'])
    # there's a change in API endpoints from version 17.0.0
    auth_path = ""
    if version.parse(environ.get("KEYCLOAK_VERSION")) < version.parse("17.0.0"):
        auth_path += r"\/auth"
    matchers = [
        # login url
        re.compile(r"^" + keycloak_url + auth_path + r"\/realms\/" + realm + "\/protocol\/openid-connect\/auth\?(response_type\=code)\&(client_id\=taranis_ng)\&(redirect_uri\=(https?%3[aA]\/\/[a-z0-9A-Z%\/\.\-_]*|https?%3[aA]%2[fF]%2[fF][a-z0-9A-Z%\/\.\-_]*))$"),
        # login submit url
        re.compile(r"^" + keycloak_url + auth_path + r"\/realms\/" + realm + "\/login-actions\/authenticate(\??session_code\=[a-zA-Z0-9\-_]+)?(\&?\??execution\=[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12})?(\&?\??client_id\=taranis_ng)?(\&?\??tab_id=[a-zA-Z0-9\-_]+)?$"),
        # logout url
        re.compile(r"^" + keycloak_url + auth_path + r"\/realms\/" + realm + "\/protocol\/openid-connect\/logout\?(redirect_uri\=(https?%3[aA]\/\/[a-z0-9A-Z%\/\.\-_]*|https?%3[aA]%2[fF]%2[fF][a-z0-9A-Z%\/\.\-_]*))$"),
        # resources url
        re.compile(r"^" + keycloak_url + auth_path + r"/resources\/([^\.]*|[^\.]*\.[^\.]*|[^\.]*\.[^\.]*\.[^\.]*)$"),
        # reset password url
        re.compile(r"^" + keycloak_url + auth_path + r"\/realms\/" + realm + "\/login-actions\/required-action(\??session_code\=[a-zA-Z0-9\-_]+)?(\??\&?execution\=(UPDATE_PASSWORD))(\&?\??client_id\=taranis_ng)?(\&?\??tab_id=[a-zA-Z0-9\-_]+)?$"),
    ]

    @no_auth
    def proxy(self):
        allowed = False

        for m in self.matchers:
            if m.match(request.url):
                allowed = True
                break

        if not allowed:
            return {'error': 'Access forbidden'}, 403

        try:
            resp = requests.request(
                method=request.method,
                url=request.url.replace(str(environ['TARANIS_NG_KEYCLOAK_URL']) + '/',
                                        os.getenv('TARANIS_NG_KEYCLOAK_INTERNAL_URL') + '/', 1),
                headers={key: value for (key, value) in request.headers if key != 'Host'},
                data=request.get_data(),
                cookies=request.cookies,
                proxies={'http': None, 'https': None},
                allow_redirects=False)

            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items()
                       if name.lower() not in excluded_headers]

            response = Response(resp.content, resp.status_code, headers)
            return response
        except Exception:
            return {'error': 'Internal server error'}, 500

    def get(self, path):
        return self.proxy()

    def post(self, path):
        return self.proxy()

    def put(self, path):
        return self.proxy()

    def delete(self, path):
        return self.proxy()


def initialize(api):
    api.add_resource(Keycloak, "/api/v1/auth/keycloak/<path:path>")
