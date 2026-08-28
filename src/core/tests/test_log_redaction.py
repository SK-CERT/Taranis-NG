"""Redaction of request bodies that reach the activity log.

Two shapes of body must be redacted the same way: the raw bytes fallback used
by the auth error path, and the parsed dict that the API authorization wrapper
passes for every successful call. The parsed-dict path is what previously
dodged the masking entirely.
"""

from __future__ import annotations

import json

import pytest
from flask import Flask
from managers.log_manager import _SENSITIVE_JSON_KEYS, generate_escaped_data, sensitive_value


@pytest.fixture
def log_app() -> Flask:
    """Bare Flask app providing the request context generate_escaped_data reads."""
    return Flask(__name__)


def _login_body() -> bytes:
    return json.dumps({"username": "jarsvoboda", "password": "HERE IS THE PASSWORD", "provider_id": 5}).encode()


def test_parsed_dict_body_is_redacted(log_app: Flask) -> None:
    # the API wrapper passes the body parsed by Flask, not raw bytes
    body = {"username": "jarsvoboda", "password": "HERE IS THE PASSWORD", "provider_id": 5}
    with log_app.test_request_context("/api/v1/auth/login", data=_login_body()):
        logged = generate_escaped_data(body)
    assert "HERE IS THE PASSWORD" not in logged
    assert sensitive_value("x") in logged  # the mask actually replaced it
    assert "jarsvoboda" in logged  # non-sensitive fields survive


def test_raw_bytes_body_is_redacted(log_app: Flask) -> None:
    with log_app.test_request_context("/api/v1/auth/login", data=_login_body()):
        logged = generate_escaped_data(None)
    assert "HERE IS THE PASSWORD" not in logged
    assert "jarsvoboda" in logged


def test_nested_secrets_inside_lists_are_redacted(log_app: Flask) -> None:
    body = [{"api_key": "k-123", "name": "node"}]
    with log_app.test_request_context("/", data=json.dumps(body).encode()):
        logged = generate_escaped_data(body)
    assert "k-123" not in logged
    assert "node" in logged


def test_non_json_payloads_pass_through(log_app: Flask) -> None:
    raw = b"not a json payload"
    with log_app.test_request_context("/", data=raw):
        assert generate_escaped_data(None) == "not a json payload"


def test_sensitive_value_masking_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    # default mode masks; the operator opt-in modes must keep working
    assert sensitive_value("secret") == "•••••"
    monkeypatch.setenv("LOG_SENSITIVE_DATA", "yes")
    assert sensitive_value("secret") == "secret"
    monkeypatch.setenv("LOG_SENSITIVE_DATA", "no")
    assert sensitive_value("secret") == "•••••"


def test_sensitive_key_coverage() -> None:
    for key in ("password", "token", "api_key", "client_secret", "access_token", "totp", "otp", "mfa_token", "credentials"):
        assert key in _SENSITIVE_JSON_KEYS, f"{key} missing from the redaction set"
