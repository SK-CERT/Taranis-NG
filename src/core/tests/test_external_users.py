"""The asset portal manages external users of the administrator's own organizations only.

MY_ASSETS_CONFIG is an organization's asset administrator. The portal's user management
checked only that the target shared an organization with them, so they could rename, set the
password of, or delete any account of that organization - a full administrator's included,
whose roles stayed - and the list showed the users of every organization. Asset groups and
notification templates were listed across organizations the same way.
"""

from __future__ import annotations

import types
from typing import TYPE_CHECKING

import pytest
from api import assets as assets_api
from flask import Flask
from managers import db_manager
from model import user as user_module
from model.asset import AssetGroup
from model.notification_template import NotificationTemplate
from model.user import User
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Iterator

EXTERNAL = ["MY_ASSETS_ACCESS", "MY_ASSETS_CREATE", "MY_ASSETS_CONFIG", "CONFIG_ACCESS"]
CUSTOMER_A = types.SimpleNamespace(id=1, name="Customer A")
CUSTOMER_B = types.SimpleNamespace(id=2, name="Customer B")
CSIRT = types.SimpleNamespace(id=3, name="CSIRT")


def _user(
    user_id: int,
    organizations: list,
    *,
    roles: list | None = None,
    permissions: tuple[str, ...] = ("MY_ASSETS_ACCESS",),
) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id=user_id,
        username=f"user{user_id}",
        name=f"User {user_id}",
        password="old-hash",
        organizations=organizations,
        roles=roles or [],
        permissions=[types.SimpleNamespace(id=permission) for permission in permissions],
    )


ORG_ADMIN = _user(10, [CUSTOMER_A], permissions=("MY_ASSETS_ACCESS", "MY_ASSETS_CONFIG"))


@pytest.fixture
def accounts(monkeypatch: pytest.MonkeyPatch) -> dict[int, types.SimpleNamespace]:
    stored = {
        11: _user(11, [CUSTOMER_A]),
        12: _user(12, [CUSTOMER_B]),
        13: _user(13, [CUSTOMER_A], roles=[types.SimpleNamespace(name="Admin")], permissions=()),
        14: _user(14, [CUSTOMER_A], permissions=("MY_ASSETS_ACCESS", "CONFIG_USER_UPDATE")),
        15: _user(15, [CUSTOMER_A, CSIRT]),
    }
    session = types.SimpleNamespace(
        get=lambda _model, user_id: stored.get(user_id),
        delete=lambda user: stored.pop(user.id),
        add=lambda _row: None,
        commit=lambda: None,
    )
    monkeypatch.setattr(user_module.db, "session", session)
    return stored


def test_an_external_user_of_one_s_organization_can_be_changed(accounts: dict[int, types.SimpleNamespace]) -> None:
    User.update_external(ORG_ADMIN, EXTERNAL, 11, {"username": "renamed", "name": "Renamed", "password": "new-one", "permissions": []})

    assert accounts[11].username == "renamed"


@pytest.mark.parametrize(
    ("user_id", "why"),
    [
        (12, "another organization"),
        (13, "an administrator, with a role"),
        (14, "an internal permission"),
        (15, "also in an organization the admin is not"),
    ],
)
def test_nobody_else_can_be_changed_or_deleted(accounts: dict[int, types.SimpleNamespace], user_id: int, why: str) -> None:
    with pytest.raises(ValueError, match="external users of your own organization"):
        User.update_external(ORG_ADMIN, EXTERNAL, user_id, {"username": "x", "name": "x", "password": "taken-over", "permissions": []})
    with pytest.raises(ValueError, match="external users of your own organization"):
        User.delete_external(ORG_ADMIN, user_id, EXTERNAL)

    assert accounts[user_id].password == "old-hash", why
    assert user_id in accounts


def test_the_list_shows_external_users_of_one_s_organizations_only(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list = []
    everyone = [_user(11, [CUSTOMER_A]), _user(13, [CUSTOMER_A], roles=[types.SimpleNamespace(name="Admin")], permissions=())]
    monkeypatch.setattr(User, "get", classmethod(lambda _cls, _search, organizations: asked.append(organizations) or (everyone, 2)))
    monkeypatch.setattr(
        user_module,
        "UserPresentationSchema",
        lambda **_kwargs: types.SimpleNamespace(dump=lambda users: [u.id for u in users]),
    )

    listing = User.get_all_external_json(ORG_ADMIN, None, EXTERNAL)

    assert asked == [[CUSTOMER_A]]
    assert listing == {"total_count": 1, "items": [11]}


def test_a_new_external_user_gets_no_identity_status_or_mfa_from_the_request(
    monkeypatch: pytest.MonkeyPatch,
    accounts: dict[int, types.SimpleNamespace],  # noqa: ARG001
) -> None:
    created = types.SimpleNamespace(roles=["x"], permissions=[], auth_identities=["planted"], status="pending", require_mfa=True)
    monkeypatch.setattr(user_module, "NewUserSchema", lambda: types.SimpleNamespace(load=lambda _data: created))

    User.add_new_external(ORG_ADMIN, EXTERNAL, {"identities": [{"auth_provider_id": 1, "external_username": "ceo@corp.example"}]})

    assert (created.roles, created.auth_identities, created.status, created.require_mfa) == ([], [], "active", False)


# --- the listing queries ---------------------------------------------------------------------


@pytest.fixture
def sql() -> Iterator[None]:
    """An application context, so queries can be built and compiled; nothing connects."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    db_manager.db.init_app(app)
    with app.app_context():
        yield


def _compiled(query: object) -> str:
    return str(query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.usefixtures("sql")
def test_users_are_listed_for_the_organizations_asked_for_only(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list = []
    monkeypatch.setattr(type(User.query), "all", lambda query: queries.append(query) or [])
    monkeypatch.setattr(type(User.query), "count", lambda _query: 0)

    User.get(None, [types.SimpleNamespace(id=1), types.SimpleNamespace(id=2)])

    sql = _compiled(queries[0])
    assert "EXISTS" in sql
    assert "organization.id IN (1, 2)" in sql


@pytest.mark.usefixtures("sql")
def test_notification_templates_are_listed_for_the_organization_only(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list = []
    monkeypatch.setattr(type(NotificationTemplate.query), "all", lambda query: queries.append(query) or [])
    monkeypatch.setattr(type(NotificationTemplate.query), "count", lambda _query: 0)

    NotificationTemplate.get(None, types.SimpleNamespace(id=1))

    assert "notification_template_organization.organization_id = 1" in _compiled(queries[0])


@pytest.mark.usefixtures("sql")
def test_asset_groups_are_listed_for_the_user_s_organizations_only(monkeypatch: pytest.MonkeyPatch) -> None:
    queries: list = []
    monkeypatch.setattr(type(AssetGroup.query), "all", lambda query: queries.append(query) or [])
    asker = types.SimpleNamespace(organizations=[CUSTOMER_A, CSIRT], get_permissions=lambda: ["MY_ASSETS_CONFIG"])

    assert assets_api._asset_groups_json(asker, "vpn") == {"total_count": 0, "items": []}

    sql = _compiled(queries[0])
    assert "EXISTS" in sql
    assert "organization.id IN (1, 3)" in sql
    assert "asset_group.name ILIKE '%%vpn%%'" in sql
