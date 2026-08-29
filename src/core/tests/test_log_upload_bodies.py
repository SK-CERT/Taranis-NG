"""A file upload must not put its bytes into the activity log.

Uploading a public-web favicon took the whole request down with
`psycopg.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`.
`auth_required` calls `get_json(force=True)`, which reads and caches the body
whatever its content type; the log then fell back to `request.data` and tried to
store the raw multipart payload — PNG bytes and all — in a text column.
"""

from __future__ import annotations

import io

import pytest
from flask import Flask, request
from managers.log_manager import _no_nul, generate_escaped_data

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 40


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


def _upload() -> dict:
    # a fresh stream per request: werkzeug consumes it while encoding
    return {"file": (io.BytesIO(PNG), "favicon.ico", "image/x-icon")}


def test_upload_body_is_summarised_not_dumped(app: Flask) -> None:
    with app.test_request_context(
        "/api/v1/config/public-web-nodes/1/webs/1/images/favicon",
        method="POST",
        data=_upload(),
        content_type="multipart/form-data",
    ):
        request.get_json(force=True, silent=True)  # what auth_required does before logging
        logged = generate_escaped_data(None)

    assert "\x00" not in logged, "a NUL byte here makes PostgreSQL reject the whole insert"
    assert "PNG" not in logged, "raw file bytes must not reach the log"
    assert "IHDR" not in logged, "raw file bytes must not reach the log"
    assert "multipart/form-data" in logged
    # the record is still useful: it names what was uploaded
    assert "favicon.ico" in logged


def test_json_bodies_are_still_logged_and_redacted(app: Flask) -> None:
    # the summary must not swallow the ordinary case the log exists for
    body = b'{"username":"jarsvoboda","password":"hunter2"}'
    with app.test_request_context("/api/v1/auth/login", method="POST", data=body, content_type="application/json"):
        logged = generate_escaped_data(None)

    assert "jarsvoboda" in logged
    assert "hunter2" not in logged


def test_nul_is_stripped_at_the_column_boundary() -> None:
    # last line of defence: an audit record must never fail the operation it records
    assert _no_nul("before\x00after") == "beforeafter"
    assert _no_nul(None) is None
    assert _no_nul(123) == 123
