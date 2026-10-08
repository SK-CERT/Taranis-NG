"""A delete blocked by references answers 409, not the 400 every other failure gets.

SK-CERT#527: the GUI said "OSINT source is in use and could not be deleted" when the
request never reached the server. It could not do better - every failed delete answered
400 "Could not delete ...", so "in use" and "anything else" looked the same. A row that
other records still reference fails at commit with an IntegrityError; that is now a 409,
both for the config endpoints that catch their own errors and, via ``SafeErrorApi``, for
the ones that let the exception escape. The service nodes check for their dependants before
deleting and answer the same 409 when they find some.
"""

from __future__ import annotations

import ast
import types
from http import HTTPStatus
from pathlib import Path

import pytest
from api import config as config_api
from flask import Flask
from flask_restful import Resource
from managers import api_manager
from managers.api_manager import SafeErrorApi
from model import bots_node, presenters_node, publishers_node
from sqlalchemy.exc import IntegrityError


def _integrity_error() -> IntegrityError:
    return IntegrityError("DELETE FROM role WHERE role.id = %(id)s", {"id": 1}, Exception("violates foreign key constraint"))


@pytest.fixture
def logged(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Record the activity-log calls instead of touching the database."""
    calls: list[tuple] = []
    monkeypatch.setattr(config_api.log_manager, "store_data_error_activity", lambda *args: calls.append(args))
    monkeypatch.setattr(config_api, "get_user_from_jwt", lambda: None)
    return calls


def test_a_referenced_row_is_a_conflict(logged: list[tuple]) -> None:
    body, status = config_api._delete_failed("Could not delete role", _integrity_error())

    assert status == HTTPStatus.CONFLICT
    assert body == {"error": "Could not delete role: it is still in use"}
    assert len(logged) == 1


def test_any_other_failure_stays_a_bad_request(logged: list[tuple]) -> None:
    body, status = config_api._delete_failed("Could not delete role", RuntimeError("boom"))

    assert status == HTTPStatus.BAD_REQUEST
    assert body == {"error": "Could not delete role"}
    assert len(logged) == 1


def test_every_config_delete_reports_through_the_helper() -> None:
    """A delete endpoint answering its own 400 would hide "in use" from the GUI again."""
    tree = ast.parse(Path(config_api.__file__).read_text(encoding="utf-8"))
    offenders = []
    for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
        for method in (node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "delete"):
            for handler in (node for node in ast.walk(method) if isinstance(node, ast.ExceptHandler)):
                if ast.unparse(handler.type) != "Exception":
                    continue
                returns = [node for node in ast.walk(handler) if isinstance(node, ast.Return)]
                if not all(isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == "_delete_failed" for node in returns):
                    offenders.append(cls.name)
    assert not offenders, f"delete endpoints bypassing _delete_failed: {offenders}"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setattr(api_manager.log_manager, "store_data_error_activity", lambda *_args: None)
    app = Flask(__name__)

    class Records(Resource):
        def delete(self) -> None:
            raise _integrity_error()

        def post(self) -> None:
            raise _integrity_error()

        def put(self) -> None:
            msg = "not an integrity problem"
            raise RuntimeError(msg)

    api = SafeErrorApi(app)
    api.add_resource(Records, "/api/v1/records")
    return app.test_client()


def test_an_uncaught_integrity_error_on_delete_is_in_use(client: Flask) -> None:
    response = client.delete("/api/v1/records")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.get_json() == {"error": "The record is still in use and could not be deleted"}


def test_an_uncaught_integrity_error_elsewhere_is_a_conflict(client: Flask) -> None:
    response = client.post("/api/v1/records")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.get_json() == {"error": "The change conflicts with existing data"}


def test_other_uncaught_errors_keep_their_normal_handling(client: Flask) -> None:
    response = client.put("/api/v1/records")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


class _FakeSession:
    """Hands out one node and records whether anything was deleted."""

    def __init__(self, node: object) -> None:
        self.node = node
        self.deleted: list[object] = []

    def get(self, _model: object, _node_id: str) -> object:
        return self.node

    def delete(self, row: object) -> None:
        self.deleted.append(row)

    def commit(self) -> None:
        pass


@pytest.mark.parametrize(
    ("module", "model", "node"),
    [
        (
            presenters_node,
            presenters_node.PresentersNode,
            types.SimpleNamespace(presenters=[types.SimpleNamespace(product_types=["product type"])]),
        ),
        (publishers_node, publishers_node.PublishersNode, types.SimpleNamespace(publishers=[types.SimpleNamespace(presets=["preset"])])),
        (bots_node, bots_node.BotsNode, types.SimpleNamespace(bots=[types.SimpleNamespace(presets=["preset"])])),
    ],
)
def test_a_node_still_in_use_is_a_conflict(monkeypatch: pytest.MonkeyPatch, module: object, model: type, node: object) -> None:
    session = _FakeSession(node)
    monkeypatch.setattr(module, "db", types.SimpleNamespace(session=session))

    _, status = model.delete("node-1")

    assert status == HTTPStatus.CONFLICT
    assert session.deleted == []
