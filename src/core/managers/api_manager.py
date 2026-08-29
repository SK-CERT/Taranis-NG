"""API Manager to initialize all API endpoints."""

from api import (
    analyze,
    assess,
    assets,
    auth,
    bots,
    collectors,
    config,
    dashboard,
    isalive,
    public_web,
    publish,
    remote,
    sse,
    state,
    traefik,
    user,
)
from flask_restful import Api
from marshmallow import ValidationError


class SafeErrorApi(Api):
    """``Api`` that will not echo a rejected request body back to the client.

    ``flask_restful.Api.handle_error`` builds the error response from
    ``getattr(e, "data", ...)`` (flask_restful/__init__.py:340). Marshmallow's
    ``ValidationError`` sets ``.data`` to the *input it just rejected*, so any
    schema load that escapes a resource returns the whole request body - which
    for ``POST /config/users`` is the new account's cleartext password, and
    elsewhere API keys, client secrets and tokens. It is also a 500 for what is
    a client mistake.

    Both are fixed here rather than at the ~46 ``schema.load()`` call sites,
    because one missed call site reintroduces the leak.
    """

    def handle_error(self, e: Exception) -> object:
        """Turn a schema rejection into a 400 carrying only the field errors."""
        if isinstance(e, ValidationError):
            return self.make_response({"error": "Invalid request", "validation": e.normalized_messages()}, 400)
        return super().handle_error(e)


def initialize(app: object) -> None:
    """Initialize all API endpoints."""
    api = SafeErrorApi(app)

    assess.initialize(api)
    auth.initialize(api)
    collectors.initialize(api)
    isalive.initialize(api)
    config.initialize(api)
    sse.initialize(api)
    analyze.initialize(api)
    publish.initialize(api)
    public_web.initialize(api)
    user.initialize(api)
    assets.initialize(api)
    bots.initialize(api)
    remote.initialize(api)
    dashboard.initialize(api)
    state.initialize(api)
    traefik.initialize(api)
