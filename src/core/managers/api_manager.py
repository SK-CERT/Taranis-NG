"""API Manager to initialize all API endpoints."""

from api import analyze, assess, assets, auth, bots, collectors, config, dashboard, isalive, publish, remote, sse, state, user
from flask_restful import Api


def initialize(app: object) -> None:
    """Initialize all API endpoints."""
    api = Api(app)

    assess.initialize(api)
    auth.initialize(api)
    collectors.initialize(api)
    isalive.initialize(api)
    config.initialize(api)
    sse.initialize(api)
    analyze.initialize(api)
    publish.initialize(api)
    user.initialize(api)
    assets.initialize(api)
    bots.initialize(api)
    remote.initialize(api)
    dashboard.initialize(api)
    state.initialize(api)
