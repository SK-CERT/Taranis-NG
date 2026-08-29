"""Response headers the core API attaches to every reply.

The hardening pass added these but nothing pinned them, so a refactor could
drop a header (or the whole CSP branch for previews) without a test noticing.
"""

from __future__ import annotations

import pytest
from app import _install_security_headers
from flask import Flask, Response


@pytest.fixture
def client() -> Flask:
    """A minimal app carrying only the header hook and the routes it branches on."""
    app = Flask(__name__)

    @app.route("/api/v1/assess/news-items")
    def json_route() -> tuple[dict, int]:
        return {"ok": True}, 200

    @app.route("/api/v1/publish/products/preview/<token>")
    def preview_route(token: str) -> Response:
        mime = {"html": "text/html", "pdf": "application/pdf"}[token]
        return Response(b"body", mimetype=mime)

    _install_security_headers(app)
    return app.test_client()


def test_json_responses_carry_the_strict_policy(client: Flask) -> None:
    headers = client.get("/api/v1/assess/news-items").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_html_preview_may_run_its_own_inline_script(client: Flask) -> None:
    # template_osint.html inlines Chart.js; a policy without script-src falls
    # back to default-src 'none' and ships the report with no charts.
    csp = client.get("/api/v1/publish/products/preview/html").headers["Content-Security-Policy"]
    assert "script-src 'unsafe-inline'" in csp
    assert "style-src 'unsafe-inline' 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "default-src 'none'" in csp  # network loads stay blocked


def test_non_html_preview_gets_no_csp(client: Flask) -> None:
    # default-src 'none' also zeroes object-src, which can stop a browser's
    # built-in PDF viewer from rendering the response at all.
    response = client.get("/api/v1/publish/products/preview/pdf")
    assert "Content-Security-Policy" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"  # the rest still applies


def test_a_handler_set_policy_is_not_overwritten() -> None:
    # setdefault, not assignment: a route that knows better keeps its own policy
    app = Flask(__name__)

    @app.route("/api/v1/anything")
    def route() -> Response:
        return Response(b"{}", mimetype="application/json", headers={"Content-Security-Policy": "default-src 'self'"})

    _install_security_headers(app)
    assert app.test_client().get("/api/v1/anything").headers["Content-Security-Policy"] == "default-src 'self'"
