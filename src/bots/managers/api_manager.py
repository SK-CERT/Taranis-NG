from api import *
from flask_restful import Api


def initialize(app):
    api = Api(app)

    isalive.initialize(api)
    bots.initialize(api)
