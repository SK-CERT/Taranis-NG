from flask_restful import Api

from publishers.api import *


def initialize(app):
    api = Api(app)

    isalive.initialize(api)
    publishers.initialize(api)
