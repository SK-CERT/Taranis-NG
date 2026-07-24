"""This module contains the main application factory function."""

import os

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
    # redirect_uri and SAML ACS URLs, and the Secure flag on the login cookie).
    #
    # SECURITY: this trusts exactly the last TRUSTED_PROXY_HOPS proxies to have
    # set these headers. The default of 1 matches the bundled single-Traefik
    # topology. If you add another reverse proxy / load balancer / CDN in front,
    # raise it to the real number of trusted hops - and never expose core such
    # that a client can reach it directly, or X-Forwarded-Host/-Proto become
    # spoofable and poison every request-derived URL.
    proxy_hops = int(os.getenv("TRUSTED_PROXY_HOPS", "1"))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops, x_host=proxy_hops, x_prefix=proxy_hops)

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
