"""This module contains the main application factory function."""

from flask import Flask
from flask_cors import CORS
from managers import (
    api_manager,
    auth_manager,
    cache_manager,
    db_manager,
    remote_manager,
    sse_manager,
    tagcloud_manager,
)
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.

    """
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Honor X-Forwarded-* headers from the reverse proxy (Traefik terminates
    # TLS and forwards to core over plain HTTP). Without this, request.scheme
    # resolves to "http" and request.host to the internal address, which
    # breaks places that build absolute URLs from the request (e.g. the OAuth2
    # redirect_uri sent to the IdP).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    with app.app_context():
        CORS(app, supports_credentials=True)

        db_manager.initialize(app)
        db_manager.create_tables()

        cache_manager.initialize(app)
        auth_manager.initialize(app)
        api_manager.initialize(app)
        sse_manager.initialize(app)
        remote_manager.initialize(app)
        tagcloud_manager.initialize(app)

    return app
