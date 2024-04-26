from flask_restful import Api
from api import *
from api import sse


def initialize(app):
    api = Api(app)

    assess.initialize(api)
    auth.initialize(api)
    collectors.initialize(api)
    isalive.initialize(api)
    config.initialize(api)
    sse.initialize(app)
    analyze.initialize(api)
    publish.initialize(api)
    user.initialize(api)
    assets.initialize(api)
    bots.initialize(api)
    remote.initialize(api)
    dashboard.initialize(api)
