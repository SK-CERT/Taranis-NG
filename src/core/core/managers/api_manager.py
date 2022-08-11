from flask_restful import Api

import core.api


def initialize(app):
    api = Api(app)

    core.api.assess.initialize(api)
    core.api.auth.initialize(api)
    core.api.collectors.initialize(api)
    core.api.isalive.initialize(api)
    core.api.config.initialize(api)
    core.api.analyze.initialize(api)
    core.api.publish.initialize(api)
    core.api.user.initialize(api)
    core.api.assets.initialize(api)
    core.api.bots.initialize(api)
    core.api.remote.initialize(api)
    core.api.dashboard.initialize(api)
