"""This module contains the main application factory function."""

import os

from flask import Flask, Response, request
from flask_cors import CORS
from managers import (
    api_manager,
    auth_manager,
    cache_manager,
    db_manager,
    remote_manager,
    run_state_cache,
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
        # credentials-capable CORS must never reflect arbitrary origins (that
        # would let any website make credentialed cross-site API calls). By
        # default CORS is therefore not enabled at all - the production
        # deployment serves the GUI and the API from the same origin. A
        # development GUI on another port opts in explicitly:
        #   TARANIS_NG_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
        # The list is parsed once in config.Config so that this grant and the
        # same-origin check on /auth/redeem always agree on who is trusted.
        cors_origins = app.config.get("CORS_ORIGINS") or []
        if cors_origins:
            CORS(app, supports_credentials=True, origins=cors_origins)

        db_manager.initialize(app)
        db_manager.create_tables()

        cache_manager.initialize(app)
        # The cached run state describes collector nodes as they were before this restart. A
        # compose restart takes them down with core, so nothing would ever report those runs
        # finishing; the nodes re-report their schedule on their next heartbeat.
        run_state_cache.clear_all()
        auth_manager.initialize(app)
        api_manager.initialize(app)
        sse_manager.initialize(app)
        remote_manager.initialize(app)
        tagcloud_manager.initialize(app)

        _install_security_headers(app)

    return app


def _install_security_headers(app: Flask) -> None:
    """Attach conservative security headers to every API response.

    The API serves JSON (not documents), so the browser-facing hardeners that
    apply are: content-type sniffing off, framing off, referrer minimisation.
    CSP here is defense-in-depth for any HTML the API does return (error
    pages, JSON echoed in browsers): a restrictive default-src blocks script
    injection in them. Traefik appends HSTS at the TLS edge.

    Rendered product previews are the exception, and there are two of them:

    * HTML previews run the presenter's own template, which owns its styling
      *and* its scripting - template_osint.html, for one, inlines Chart.js and
      draws its charts in the browser. Blocking inline script would ship a
      report with no charts. These templates are server-side code authored by
      administrators, not user content, and the policy still denies loading
      anything over the network, framing, and form submission.
    * Non-HTML previews (PDF above all) are handed to a browser's built-in
      viewer. ``default-src 'none'`` also zeroes ``object-src``, which has
      historically kept those viewers from rendering, so previews that are not
      HTML get no CSP rather than a policy that might silently blank them.
    """
    preview_prefix = "/api/v1/publish/products/preview/"

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # One hook decides the CSP outright. Splitting this across two
        # after_request handlers worked only because Flask runs them in reverse
        # registration order, which is far too subtle a thing to rely on.
        if request.path.startswith(preview_prefix):
            if response.mimetype == "text/html":
                response.headers.setdefault(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' 'self'; "
                    "img-src data: 'self'; font-src data: 'self'; frame-ancestors 'none'; form-action 'none'",
                )
            return response

        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'",
        )
        return response
