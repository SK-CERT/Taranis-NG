"""A rejected request body must never come back in the error response.

``flask_restful.Api.handle_error`` builds its response from the exception's
``.data`` attribute, and marshmallow's ``ValidationError.data`` is the input it
just rejected. Left alone, ``POST /config/users`` with a bad payload answered
500 with the new account's cleartext password in the body.
"""

from __future__ import annotations

import pytest
from flask import Flask, request
from flask_restful import Resource
from managers.api_manager import SafeErrorApi
from marshmallow import Schema, fields

SECRET = "SUPERSECRET-PW"


class _UserSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(load_only=True)
    role_id = fields.Str(required=True)  # a str field the test will feed an int


@pytest.fixture
def client() -> Flask:
    app = Flask(__name__)

    class Users(Resource):
        def post(self) -> dict:
            return _UserSchema().load(request.json)

    api = SafeErrorApi(app)
    api.add_resource(Users, "/api/v1/config/users")
    return app.test_client()


def test_validation_failure_does_not_echo_the_payload(client: Flask) -> None:
    response = client.post("/api/v1/config/users", json={"username": "u", "password": SECRET, "role_id": 2})

    body = response.get_data(as_text=True)
    assert SECRET not in body, "the rejected request body must not be reflected"
    assert '"u"' not in body


def test_validation_failure_is_a_client_error_with_field_details(client: Flask) -> None:
    response = client.post("/api/v1/config/users", json={"username": "u", "password": SECRET, "role_id": 2})

    # a malformed payload is the caller's mistake, not a server fault
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Invalid request"
    # the caller still learns which field to fix
    assert "role_id" in payload["validation"]


def test_other_errors_keep_their_normal_handling(client: Flask) -> None:
    # the override must be narrow: only marshmallow rejections are rewritten
    response = client.get("/api/v1/config/users")
    assert response.status_code == 405


def test_a_valid_payload_still_passes_through(client: Flask) -> None:
    response = client.post("/api/v1/config/users", json={"username": "u", "password": SECRET, "role_id": "2"})
    assert response.status_code == 200
