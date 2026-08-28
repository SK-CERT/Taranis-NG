"""Attachment download must honour the news item data ACL and ownership.

The endpoint used to resolve ``NewsItemAttribute.find(attribute_id)`` globally,
so any user holding ASSESS_ACCESS could fetch any group's attachment by ID.
The fix resolves the attribute through the owning news item data (ownership)
and checks that data against the caller's ACL (authorization).

The ``auth_required`` decorator is exercised separately by the auth-manager
suite; here the handler logic is tested through ``__wrapped__`` with the
caller's user injected the way the decorator would.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import pytest
from api import assess
from flask import Flask, Response
from model.news_item import NewsItemData

if TYPE_CHECKING:
    from collections.abc import Callable

    from model.user import User


class _FakeAttribute:
    """NewsItemAttribute stand-in with just the fields the handler reads."""

    def __init__(self, attribute_id: int, value: str = "cvss.txt", mime: str | None = "text/plain") -> None:
        self.id = attribute_id
        self.value = value
        self.binary_mime_type = mime
        self.binary_data = b"content"


@pytest.fixture
def log_app() -> Flask:
    return Flask(__name__)


@pytest.fixture
def acl_decisions(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """Replace the ACL query with a controllable per-item-data decision."""
    decisions: dict[str, bool] = {}

    def fake_allowed_with_acl(_cls: type, news_item_data_id: str, _user: object, **_kwargs: object) -> bool:
        return decisions.get(news_item_data_id, False)

    monkeypatch.setattr(NewsItemData, "allowed_with_acl", classmethod(fake_allowed_with_acl))
    return decisions


@pytest.fixture
def caller(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """The user the auth decorator resolved, plus a silent activity log."""
    fake_user = types.SimpleNamespace(id=1, username="alice")
    monkeypatch.setattr(assess.auth_manager, "get_user_from_jwt", lambda: fake_user)
    monkeypatch.setattr(assess.log_manager, "store_user_auth_error_activity", lambda *_args, **_kwargs: None)
    return fake_user


def _handler() -> Callable[..., tuple[dict, HTTPStatus] | Response]:
    """The undecorated handler - the decorator itself is unchanged framework code."""
    resource = assess.DownloadAttachment()
    return resource.post.__wrapped__.__get__(resource)


def _apply_decisions(monkeypatch: pytest.MonkeyPatch, attribute: _FakeAttribute | None) -> None:
    """Stub the scoped attribute lookup with a fixed result."""
    monkeypatch.setattr(NewsItemData, "find_data_attribute", classmethod(lambda _cls, _item, _attr: attribute))


def _call(log_app: Flask, item_data_id: str, attribute_id: str) -> tuple[dict, HTTPStatus] | Response:
    with log_app.test_request_context("/"):
        return _handler()(item_data_id, attribute_id)


@pytest.mark.usefixtures("caller")
def test_attachment_of_foreign_item_data_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
    acl_decisions: dict[str, bool],
    log_app: Flask,
) -> None:
    # the attribute ID exists, but not under the requested news item data
    acl_decisions["victim-item"] = True
    _apply_decisions(monkeypatch, None)
    _, code = _call(log_app, "victim-item", "42")
    assert code == HTTPStatus.NOT_FOUND


@pytest.mark.usefixtures("caller", "acl_decisions")
def test_attachment_outside_acl_is_unauthorized(monkeypatch: pytest.MonkeyPatch, log_app: Flask) -> None:
    # ownership would succeed, but the caller's ACL on the item data fails
    _apply_decisions(monkeypatch, _FakeAttribute(42))
    _, code = _call(log_app, "someone-elses-item", "42")
    assert code == HTTPStatus.UNAUTHORIZED


@pytest.mark.usefixtures("caller")
def test_authorised_download_streams_the_file(monkeypatch: pytest.MonkeyPatch, acl_decisions: dict[str, bool], log_app: Flask) -> None:
    acl_decisions["my-item"] = True
    _apply_decisions(monkeypatch, _FakeAttribute(42, value="report.txt"))
    response = _call(log_app, "my-item", "42")
    assert response.status_code == HTTPStatus.OK.value
    assert response.headers["Content-Disposition"].startswith("attachment; filename=report.txt")


@pytest.mark.usefixtures("caller")
def test_attachment_without_binary_is_not_found(monkeypatch: pytest.MonkeyPatch, acl_decisions: dict[str, bool], log_app: Flask) -> None:
    acl_decisions["my-item"] = True
    attribute = _FakeAttribute(42)
    attribute.binary_data = None
    _apply_decisions(monkeypatch, attribute)
    _, code = _call(log_app, "my-item", "42")
    assert code == HTTPStatus.NOT_FOUND


def test_find_data_attribute_is_scoped_to_the_owning_item(monkeypatch: pytest.MonkeyPatch) -> None:
    # a bare attribute ID must never match across item data, mirroring ReportItem.find_attachment
    owning = _FakeAttribute(7)
    item_data = types.SimpleNamespace(attributes=[owning])

    def fake_get(cls, wanted_id: str, **_kwargs: object) -> object:  # noqa: ANN001, ARG001
        return item_data if wanted_id == "item-1" else None

    monkeypatch.setattr("model.news_item.db.session", types.SimpleNamespace(get=fake_get))
    assert NewsItemData.find_data_attribute("item-1", 7) is owning
    assert NewsItemData.find_data_attribute("item-1", 8) is None
    assert NewsItemData.find_data_attribute("item-2", 7) is None


def test_acl_check_on_a_nonexistent_item_data_is_refused_not_crashed(monkeypatch: pytest.MonkeyPatch) -> None:
    # allowed_with_acl used to dereference the result of db.session.get() without
    # a None check, so an ID that resolves to nothing raised AttributeError and
    # the endpoint answered 500 instead of refusing the request.
    monkeypatch.setattr("model.news_item.db.session", types.SimpleNamespace(get=lambda _cls, _id, **_kw: None))
    nobody = cast("User", types.SimpleNamespace(id=1, username="alice"))
    assert NewsItemData.allowed_with_acl("no-such-item", nobody, see=False, access=True, modify=False) is False
