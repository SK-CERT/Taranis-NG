"""A rejected request body must never come back in the error response.

``flask_restful.Api.handle_error`` builds its response from the exception's
``.data`` attribute, and marshmallow's ``ValidationError.data`` is the input it
just rejected. Left alone, ``POST /config/users`` with a bad payload answered
500 with the new account's cleartext password in the body.
"""

from __future__ import annotations

import types

import pytest
from flask import Flask, request
from flask_restful import Resource
from managers import api_manager
from managers.api_manager import SafeErrorApi
from marshmallow import Schema, fields, post_load
from sqlalchemy.exc import DataError

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


def test_a_rejected_request_is_logged_without_echoing_it(client: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    """Answered quietly, a rejected payload left nothing in the log to explain "it did not save"."""
    logged: list[tuple] = []
    monkeypatch.setattr(
        api_manager.log_manager,
        "store_data_error_activity",
        lambda user, detail, exception=None, request_data=None: logged.append((user, detail, exception, request_data)),
    )

    response = client.post("/api/v1/config/users", json={"username": "u", "password": SECRET, "role_id": 2})

    assert response.status_code == 400
    ((user, detail, exception, request_data),) = logged
    assert detail == "Request rejected, invalid fields: role_id"
    assert exception.normalized_messages() == {"role_id": ["Not a valid string."]}
    # The body is logged the usual way (redacted by log_manager), never answered back.
    assert user is None
    assert request_data is None
    assert SECRET not in response.get_data(as_text=True)


def test_nested_rejections_name_their_path() -> None:
    messages = {"deliveries": {0: {"language": ["Unknown"]}, 2: {"format": ["Missing"]}}, "name": ["Required"]}

    assert api_manager._field_names(messages) == ["deliveries.0.language", "deliveries.2.format", "name"]
    assert api_manager._field_names(["Invalid input type."]) == ["_schema"]


# ── what fuzzing the API turned up ────────────────────────────────────────────────


class _Thing:
    def __init__(self, name: str, kind: str) -> None:
        if kind == "boom":
            msg = "__init__() missing 1 required positional argument: 'raised inside'"
            raise TypeError(msg)
        self.name = name


class _ThingSchema(Schema):
    name = fields.Str()
    kind = fields.Str()

    @post_load
    def make(self, data: dict, **_kwargs: object) -> _Thing:
        return _Thing(**data)


@pytest.fixture
def fuzz_client(monkeypatch: pytest.MonkeyPatch) -> Flask:
    app = Flask(__name__)
    monkeypatch.setattr(api_manager.log_manager, "store_data_error_activity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api_manager.db, "session", types.SimpleNamespace(rollback=lambda: None))

    class Things(Resource):
        def post(self) -> dict:
            thing = _ThingSchema().load(request.json)
            return {"name": thing.name}

    class Search(Resource):
        def get(self) -> dict:
            cause = Exception("PostgreSQL text fields cannot contain NUL (0x00) bytes")
            raise DataError(statement="SELECT ...", params={}, orig=cause)

    app.before_request(api_manager._reject_scalar_json_body)
    api = SafeErrorApi(app)
    api.add_resource(Things, "/things")
    api.add_resource(Search, "/search")
    return app.test_client()


def test_a_value_the_database_refuses_is_a_400(fuzz_client: Flask) -> None:
    # e.g. ?search=%00 on every list: PostgreSQL refuses NUL characters, which was a 500.
    response = fuzz_client.get("/search")

    assert response.status_code == 400
    assert "NUL" in response.get_json()["error"]


def test_a_request_missing_what_the_model_needs_is_a_400(fuzz_client: Flask) -> None:
    response = fuzz_client.post("/things", json={})

    assert response.status_code == 400
    assert response.get_json()["error"].startswith("Invalid request")


def test_a_type_error_inside_the_model_stays_a_server_error(fuzz_client: Flask) -> None:
    # Only the call failing on its arguments is the request's fault; a bug in the model is not.
    response = fuzz_client.post("/things", json={"name": "x", "kind": "boom"})

    assert response.status_code == 500


@pytest.mark.parametrize("body", ['"x"', "42", "true"])
def test_a_bare_json_value_is_refused(fuzz_client: Flask, body: str) -> None:
    response = fuzz_client.post("/things", data=body, content_type="application/json")

    assert response.status_code == 400
    assert response.get_json() == {"error": "The request body must be a JSON object"}


def test_objects_and_lists_pass(fuzz_client: Flask) -> None:
    assert fuzz_client.post("/things", json={"name": "x", "kind": "y"}).status_code == 200
