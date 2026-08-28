"""The Publish view reads its public-web target list from a publish-scoped endpoint.

Before this endpoint existed the GUI assembled the same list through the
configuration API: one ``CONFIG_PUBLIC_WEB_NODE_ACCESS``-gated call for the
nodes, then one request per node for its webs - so for an ordinary publishing
user the first call 403'd on every page load. These tests pin the replacement:
one endpoint, guarded by ``PUBLISH_ACCESS`` only, returning plain id/name pairs.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from api import publish
from flask import Flask
from flask_restful import Api
from model import public_web as public_web_module
from model.public_web import PublicWeb

if TYPE_CHECKING:
    from collections.abc import Callable


class _FakeQuery:
    """A query that only knows how to answer ``.order_by(...).all()``."""

    def __init__(self, rows: list) -> None:
        self._rows = rows
        self.ordered_by: list = []

    def order_by(self, *criteria: object) -> _FakeQuery:
        """Record the ordering clause and keep the primed answer."""
        self.ordered_by.extend(criteria)
        return self

    def all(self) -> list:
        """Return the rows the fixture was primed with."""
        return self._rows


@pytest.fixture
def publish_url_map(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Register publish's routes on a throwaway Flask app and return its URL map.

    ``initialize()`` also re-adds every permission row; that half is DB-backed,
    so it is stubbed out - these tests are about routing, not seeding. The map
    values are flask-restful's endpoint names (the resource class name, lowercased).
    """
    monkeypatch.setattr(publish, "Permission", types.SimpleNamespace(add=lambda *_args, **_kwargs: None))
    app = Flask(__name__)
    publish.initialize(Api(app))
    return {str(rule): rule.endpoint for rule in app.url_map.iter_rules()}


def _prime_webs(monkeypatch: pytest.MonkeyPatch, rows: list) -> _FakeQuery:
    """Swap in a model stub whose query answers from ``rows``.

    The endpoint imports ``PublicWeb`` from the model module at call time, so
    stubbing the module attribute keeps these tests free of an app context -
    the real ``query`` property needs one before it can even be read.
    """
    fake = _FakeQuery(rows)
    monkeypatch.setattr(public_web_module, "PublicWeb", types.SimpleNamespace(query=fake, name=PublicWeb.name))
    return fake


def _call_endpoint() -> tuple[dict, HTTPStatus]:
    """Call the endpoint body directly, the way the auth wrapper would after permitting."""
    unwrapped = publish.PublishPublicWebs.get.__wrapped__
    return unwrapped(publish.PublishPublicWebs())


def _required_permissions(method: Callable) -> set[str]:
    """The permission strings the auth decorator closed over for this method."""
    return {cell.cell_contents for cell in method.__closure__ or () if isinstance(cell.cell_contents, str)}


def test_public_webs_endpoint_is_registered(publish_url_map: dict[str, str]) -> None:
    """The route lives under /api/v1/publish/, next to the products it targets."""
    assert publish_url_map.get("/api/v1/publish/public-webs") == "publishpublicwebs"


def test_public_webs_endpoint_is_scoped_to_publish_access_only() -> None:
    """A CONFIG_PUBLIC_WEB_* guard would 403 the very publishing user it serves."""
    permissions = _required_permissions(publish.PublishPublicWebs.get)
    assert permissions == {"PUBLISH_ACCESS"}
    assert not any(permission.startswith("CONFIG_") for permission in permissions)


def test_public_webs_are_empty_when_none_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty list is also how the GUI learns the feature is off here."""
    _prime_webs(monkeypatch, [])

    body, status = _call_endpoint()

    assert status == HTTPStatus.OK
    assert body == {"total_count": 0, "items": []}


def test_public_webs_return_id_and_name_pairs_ordered_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The selector only needs an id and a display name - never node internals."""
    fake = _prime_webs(
        monkeypatch,
        [types.SimpleNamespace(id=2, name="Beta Feed"), types.SimpleNamespace(id=1, name="")],
    )

    body, status = _call_endpoint()

    assert status == HTTPStatus.OK
    assert body == {
        "total_count": 2,
        "items": [{"id": 2, "name": "Beta Feed"}, {"id": 1, "name": "1"}],
    }
    (ordering,) = fake.ordered_by
    assert "name" in str(ordering)
