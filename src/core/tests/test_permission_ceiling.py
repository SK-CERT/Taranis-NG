"""Nobody grants, or takes over, more than they hold themselves.

One narrow configuration permission used to be as good as all of them: CONFIG_USER_UPDATE could
give its holder any role or reset an administrator's password, CONFIG_ROLE_UPDATE could put every
permission into a role, CONFIG_API_KEY_CREATE could mint a key acting as an administrator, and a
login method could hand every new account the Admin role.
"""

from __future__ import annotations

import types
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from api import config
from flask import Flask
from managers import permission_ceiling
from model.role import Role

if TYPE_CHECKING:
    from collections.abc import Callable

APP = Flask(__name__)
ADMIN_PERMISSIONS = {"CONFIG_USER_UPDATE", "CONFIG_ROLE_UPDATE", "CONFIG_API_KEY_CREATE", "PUBLISH_ACCESS"}
ROLES = {1: {"CONFIG_USER_UPDATE", "CONFIG_ROLE_UPDATE", "CONFIG_API_KEY_CREATE", "PUBLISH_ACCESS"}, 2: {"ASSESS_ACCESS"}}


def _role(role_id: int) -> types.SimpleNamespace:
    return types.SimpleNamespace(id=role_id, get_permissions=lambda: set(ROLES[role_id]))


def _user(user_id: int, permissions: set[str], *, roles: tuple[int, ...] = (), status: str = "active") -> types.SimpleNamespace:
    direct = [types.SimpleNamespace(id=permission) for permission in permissions]
    held = set(permissions).union(*(ROLES[role_id] for role_id in roles))
    return types.SimpleNamespace(
        id=user_id,
        username=f"user{user_id}",
        status=status,
        password="hash",
        permissions=direct,
        roles=[_role(role_id) for role_id in roles],
        get_permissions=lambda: list(held),
    )


# A user manager who may change users and roles, but holds nothing else.
MANAGER = _user(
    1,
    {"CONFIG_USER_UPDATE", "CONFIG_USER_CREATE", "CONFIG_ROLE_UPDATE", "CONFIG_ROLE_CREATE", "CONFIG_API_KEY_CREATE", "ASSESS_ACCESS"},
)
ADMIN = _user(2, set(), roles=(1,))
ANALYST = _user(3, set(), roles=(2,))


@pytest.fixture(autouse=True)
def _roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Role, "find", classmethod(lambda _cls, role_id: _role(role_id) if role_id in ROLES else None))


@pytest.fixture
def acting(monkeypatch: pytest.MonkeyPatch) -> Callable[[types.SimpleNamespace], None]:
    """Make a user the one the request is authenticated as; nothing is logged."""

    def act(actor: types.SimpleNamespace) -> None:
        monkeypatch.setattr(config, "get_user_from_jwt", lambda: actor)
        monkeypatch.setattr(config.auth_manager, "get_user_from_jwt", lambda: actor)

    monkeypatch.setattr(config.log_manager, "store_data_error_activity", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(permission_ceiling, "_active_users", lambda: [MANAGER, ADMIN, ANALYST])
    return act


# --- the rule ---------------------------------------------------------------------------------


def test_only_permissions_the_actor_lacks_are_refused() -> None:
    permission_ceiling.refuse_beyond(MANAGER, {"ASSESS_ACCESS"}, "do it")

    with pytest.raises(ValueError, match=r"PUBLISH_ACCESS"):
        permission_ceiling.refuse_beyond(MANAGER, {"ASSESS_ACCESS", "PUBLISH_ACCESS"}, "do it")


def test_the_command_line_has_no_actor_and_is_never_refused() -> None:
    permission_ceiling.refuse_beyond(None, {"ANYTHING"}, "do it")


def test_a_user_record_grants_its_permissions_and_those_of_its_roles() -> None:
    data = {"permissions": [{"id": "PUBLISH_ACCESS"}], "roles": [{"id": 2}, {"id": "1"}, {"id": 99}]}

    assert permission_ceiling.requested_user_permissions(data) == {"PUBLISH_ACCESS"} | ROLES[1] | ROLES[2]


@pytest.mark.parametrize(
    ("change", "kept"),
    [
        ({"user_id": 1, "user_permissions_after": {"ASSESS_ACCESS"}}, True),  # the admin is left
        ({"user_id": 2}, True),  # the manager is left
        ({"role_id": 1, "role_permissions_after": {"PUBLISH_ACCESS"}}, True),  # the manager holds it directly
    ],
)
def test_some_user_administrator_is_left(acting: Callable, change: dict, *, kept: bool) -> None:  # noqa: ARG001
    assert permission_ceiling.keeps_a_user_administrator(**change) is kept


def test_the_last_user_administrator_cannot_be_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(permission_ceiling, "_active_users", lambda: [ADMIN, ANALYST])

    with pytest.raises(ValueError, match="no active user who can manage users"):
        permission_ceiling.refuse_losing_the_last_user_administrator(role_id=1, role_permissions_after={"PUBLISH_ACCESS"})
    with pytest.raises(ValueError, match="no active user who can manage users"):
        permission_ceiling.refuse_losing_the_last_user_administrator(user_id=2)


# --- the endpoints ----------------------------------------------------------------------------


def _call(resource: type, method: str, *args: object, json: object = None) -> object:
    with APP.test_request_context("/", method=method.upper(), json=json):
        return getattr(resource, method).__wrapped__(resource(), *args)


def test_a_user_manager_cannot_change_an_administrator(acting: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    acting(MANAGER)
    monkeypatch.setattr(config.user.User, "find_by_id", classmethod(lambda _cls, _user_id: ADMIN))
    monkeypatch.setattr(config.user.User, "update", classmethod(lambda *_args: pytest.fail("nothing may change")))
    monkeypatch.setattr(config.user.User, "delete", classmethod(lambda *_args: pytest.fail("nothing may be deleted")))
    monkeypatch.setattr(config.user.User, "set_status", classmethod(lambda *_args: pytest.fail("no status change")))
    monkeypatch.setattr(config.user.User, "reset_mfa", classmethod(lambda *_args, **_kwargs: pytest.fail("no MFA reset")))

    body, status = _call(
        config.UserResource,
        "put",
        2,
        json={"username": "admin", "name": "x", "password": "new", "roles": [], "permissions": []},
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert "change this user" in body["error"]
    assert _call(config.UserResource, "delete", 2)[1] == HTTPStatus.BAD_REQUEST
    assert _call(config.UserStatusResource, "put", 2, json={"status": "disabled"})[1] == HTTPStatus.BAD_REQUEST
    assert _call(config.UserMfaResetResource, "post", 2, json={})[1] == HTTPStatus.BAD_REQUEST


def test_a_user_manager_cannot_give_a_role_beyond_their_own(acting: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    acting(MANAGER)
    updated: list = []
    monkeypatch.setattr(config.user.User, "find_by_id", classmethod(lambda _cls, _user_id: MANAGER))
    monkeypatch.setattr(config.user.User, "update", classmethod(lambda _cls, user_id, _data: updated.append(user_id)))
    monkeypatch.setattr(config.user.User, "add_new", classmethod(lambda *_args: pytest.fail("nothing may be created")))
    monkeypatch.setattr(config, "_notify_password_change", lambda *_args: None)

    record = {"username": "manager", "name": "Manager", "roles": [{"id": 1}], "permissions": []}
    body, status = _call(config.UserResource, "put", 1, json=record)
    assert status == HTTPStatus.BAD_REQUEST
    assert "PUBLISH_ACCESS" in body["error"]
    assert _call(config.UsersResource, "post", json={**record, "username": "new"})[1] == HTTPStatus.BAD_REQUEST

    # Re-saving one's own record unchanged is fine: the dialog sends everything every time.
    own = {
        "username": "manager",
        "name": "Manager",
        "roles": [],
        "permissions": [{"id": permission.id} for permission in MANAGER.permissions],
    }
    assert _call(config.UserResource, "put", 1, json=own) is None
    assert updated == [1]


def test_a_role_cannot_be_given_permissions_beyond_the_actor_s(acting: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    acting(MANAGER)
    monkeypatch.setattr(Role, "add_new", classmethod(lambda *_args: pytest.fail("nothing may be created")))
    monkeypatch.setattr(Role, "update", classmethod(lambda *_args: pytest.fail("nothing may change")))
    monkeypatch.setattr(Role, "delete", classmethod(lambda *_args: pytest.fail("nothing may be deleted")))

    assert _call(config.RolesResource, "post", json={"name": "x", "permissions": [{"id": "PUBLISH_ACCESS"}]})[1] == HTTPStatus.BAD_REQUEST
    # The Admin role holds what the manager does not: neither trimmed nor deleted by them.
    assert _call(config.RoleResource, "put", 1, json={"name": "Admin", "permissions": [{"id": "ASSESS_ACCESS"}]})[1] == HTTPStatus.BAD_REQUEST
    assert _call(config.RoleResource, "delete", 1)[1] == HTTPStatus.BAD_REQUEST


def test_an_api_key_cannot_act_as_a_user_with_more_permissions(acting: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    acting(MANAGER)
    monkeypatch.setattr(config.user.User, "find_by_id", classmethod(lambda _cls, user_id: {2: ADMIN, 3: ANALYST}[user_id]))
    created: list = []
    monkeypatch.setattr(config.api_key_manager, "create", lambda owner, _data, _actor: created.append(owner.id) or ({"id": 5}, "tnk_x"))
    monkeypatch.setattr(config.db.session, "rollback", lambda: None)

    body, status = _call(config.ApiKeysResource, "post", json={"user_id": 2, "name": "x"})
    assert status == HTTPStatus.BAD_REQUEST
    assert "API keys of this user" in body["error"]
    assert _call(config.ApiKeysResource, "post", json={"user_id": 3, "name": "x"})[1] == HTTPStatus.CREATED
    assert created == [3]


def test_a_login_method_cannot_hand_out_or_take_over_more(acting: Callable, monkeypatch: pytest.MonkeyPatch) -> None:
    acting(MANAGER)
    provider = types.SimpleNamespace(id=7)
    monkeypatch.setattr(config.auth_provider.AuthProvider, "add_new", classmethod(lambda *_args: pytest.fail("nothing may be created")))
    monkeypatch.setattr(config.auth_provider.AuthProvider, "update", classmethod(lambda *_args: pytest.fail("nothing may change")))
    monkeypatch.setattr(config.auth_provider.AuthProvider, "find", classmethod(lambda _cls, _provider_id: provider))
    monkeypatch.setattr(
        permission_ceiling,
        "linked_users_permissions",
        lambda found: permission_ceiling.permissions_of(ADMIN) if found is provider else set(),
    )

    assert _call(config.AuthProvidersResource, "post", json={"name": "SSO", "default_roles": [{"id": 1}]})[1] == HTTPStatus.BAD_REQUEST
    # An administrator signs in through it: whoever repoints it can sign in as them.
    assert _call(config.AuthProviderResource, "put", 7, json={"name": "SSO", "default_roles": []})[1] == HTTPStatus.BAD_REQUEST


def test_a_restricted_api_key_grants_nothing_beyond_its_own_scope(acting: Callable) -> None:
    """The ceiling is what the request may do, not everything the key's owner holds."""
    acting(ADMIN)
    with APP.test_request_context("/"):
        permission_ceiling.g.authenticated_user = ADMIN
        permission_ceiling.g.active_permissions = {"CONFIG_USER_UPDATE"}

        with pytest.raises(ValueError, match="PUBLISH_ACCESS"):
            permission_ceiling.refuse_beyond(ADMIN, {"PUBLISH_ACCESS"}, "give this user these permissions")
        permission_ceiling.refuse_beyond(ADMIN, {"CONFIG_USER_UPDATE"}, "give this user these permissions")


def test_stale_request_permissions_never_widen_the_ceiling(acting: Callable) -> None:
    acting(ANALYST)
    with APP.test_request_context("/"):
        permission_ceiling.g.authenticated_user = ANALYST
        permission_ceiling.g.active_permissions = {"ASSESS_ACCESS", "PUBLISH_ACCESS"}

        with pytest.raises(ValueError, match="PUBLISH_ACCESS"):
            permission_ceiling.refuse_beyond(ANALYST, {"PUBLISH_ACCESS"}, "do it")


@pytest.mark.parametrize("role_id", ["0x1", "1e0", "one", "1.0", True, 1.0])
def test_a_role_id_the_database_might_read_differently_is_refused(role_id: object) -> None:
    with pytest.raises(ValueError, match="Unknown role id"):
        permission_ceiling.requested_user_permissions({"roles": [{"id": role_id}]})


@pytest.mark.parametrize("role_id", [1, "1", " 1 "])
def test_plain_role_ids_count(role_id: object) -> None:
    assert permission_ceiling.requested_user_permissions({"roles": [{"id": role_id}]}) == ROLES[1]
