"""Nobody grants, or takes over, more than they hold themselves.

Permissions are flat strings, and the configuration endpoints used to assign whatever a request
named. A single narrow permission was therefore as good as all of them:

- CONFIG_USER_CREATE / CONFIG_USER_UPDATE: give yourself or anyone any role or permission, set
  an administrator's password, reset their MFA, disable or delete them;
- CONFIG_ROLE_UPDATE: put every permission into a role you hold;
- CONFIG_API_KEY_CREATE: mint a key that acts as an administrator, and read its plaintext;
- CONFIG_AUTH_PROVIDER_*: provision new accounts with the Admin role, or repoint a login method
  that administrators sign in with.

The rule here: an actor may change - or act as - a user or role only while the permissions
involved, before *and* after the change, are all the actor's own. The actor's permissions are
read from the database before anything changes (the actor may be the target). The command-line
tool (``manage.py``) passes no actor and stays unrestricted: it is the recovery path.

A second rule keeps someone able to manage users at all: a change that would leave no active
user holding CONFIG_USER_UPDATE is refused, as disabling the last one already was.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from flask import g, has_request_context
from model.auth_provider import UserAuthIdentity
from model.role import Role
from model.user import User

if TYPE_CHECKING:
    from collections.abc import Iterable

    from model.auth_provider import AuthProvider

USER_ADMINISTRATION = "CONFIG_USER_UPDATE"


# A role id as the model resolves it: digits only. Anything else ("0x1", "1e0") is refused rather
# than skipped, so the ceiling never adds up fewer roles than the database would assign.
_ROLE_ID = re.compile(r"\s*\d+\s*")


def permissions_of(user: User | None) -> set[str]:
    """Everything a user may do: direct permissions and those of their roles."""
    return set(user.get_permissions()) if user is not None else set()


def _acting_permissions(actor: User) -> set[str]:
    """What the actor may do in this request.

    A restricted API key acts with only part of its owner's permissions (``auth_required`` keeps
    the request's set in ``g.active_permissions``), so the ceiling is that part. It is never more
    than the owner holds now.
    """
    held = permissions_of(actor)
    if has_request_context():
        authenticated = g.get("authenticated_user")
        active = g.get("active_permissions")
        if active is not None and authenticated is not None and authenticated.id == actor.id:
            return held & set(active)
    return held


def _ids(items: object) -> list[object]:
    """The ids of ``[{"id": ...}]`` or ``[id]``, as a request sends them."""
    if not isinstance(items, list):
        return []
    return [item.get("id") if isinstance(item, dict) else item for item in items]


def role_permissions(role_ids: Iterable[object]) -> set[str]:
    """The permissions of the roles with these ids (unknown ids add nothing).

    Raises:
        ValueError: For an id that is not a plain number.
    """
    granted: set[str] = set()
    for role_id in role_ids:
        if role_id is None:
            continue
        if isinstance(role_id, bool) or not (isinstance(role_id, int) or (isinstance(role_id, str) and _ROLE_ID.fullmatch(role_id))):
            msg = f"Unknown role id: {role_id!r}"
            raise ValueError(msg)
        role = Role.find(int(role_id))
        if role is not None:
            granted.update(role.get_permissions())
    return granted


def requested_user_permissions(data: object) -> set[str]:
    """What a user record in a request would grant: its direct permissions and its roles' ones."""
    if not isinstance(data, dict):
        return set()
    direct = {str(permission_id) for permission_id in _ids(data.get("permissions")) if permission_id}
    return direct | role_permissions(_ids(data.get("roles")))


def requested_role_permissions(data: object) -> set[str]:
    """The permissions a role record in a request holds."""
    if not isinstance(data, dict):
        return set()
    return {str(permission_id) for permission_id in _ids(data.get("permissions")) if permission_id}


def refuse_beyond(actor: User | None, permissions: Iterable[str], what: str) -> None:
    """Refuse an action involving permissions the actor does not hold.

    Args:
        actor (User | None): Who acts; None (the command line) is never refused.
        permissions (Iterable[str]): The permissions the action involves.
        what (str): The action, for the message ("change this user").

    Raises:
        ValueError: Naming the permissions the actor lacks.
    """
    if actor is None:
        return
    missing = sorted(set(permissions) - _acting_permissions(actor))
    if missing:
        msg = f"You cannot {what}: it involves permissions you do not hold ({', '.join(missing)})"
        raise ValueError(msg)


def _active_users() -> list[User]:
    """Every active user."""
    return User.query.filter(User.status == "active").all()


def keeps_a_user_administrator(
    *,
    user_id: int | None = None,
    user_permissions_after: set[str] | None = None,
    role_id: int | None = None,
    role_permissions_after: set[str] | None = None,
) -> bool:
    """Whether some active user still holds CONFIG_USER_UPDATE after a change.

    Args:
        user_id (int | None): A user being changed; with no ``user_permissions_after`` it is
            being deleted (or disabled).
        user_permissions_after (set[str] | None): That user's permissions after the change.
        role_id (int | None): A role being changed; with no ``role_permissions_after`` it is
            being deleted.
        role_permissions_after (set[str] | None): That role's permissions after the change.

    Returns:
        bool: True when at least one active user can still manage users.
    """
    for other in _active_users():
        if user_id is not None and other.id == user_id:
            permissions = user_permissions_after or set()
        else:
            permissions = {permission.id for permission in other.permissions}
            for role in other.roles:
                if role_id is not None and role.id == role_id:
                    permissions.update(role_permissions_after or set())
                else:
                    permissions.update(role.get_permissions())
        if USER_ADMINISTRATION in permissions:
            return True
    return False


def refuse_losing_the_last_user_administrator(**change: object) -> None:
    """Refuse a change after which nobody active could manage users (see keeps_a_user_administrator).

    Raises:
        ValueError: When the change would leave no active user with CONFIG_USER_UPDATE.
    """
    if not keeps_a_user_administrator(**change):
        msg = f"This would leave no active user who can manage users ({USER_ADMINISTRATION})"
        raise ValueError(msg)


def linked_users_permissions(provider: AuthProvider | None) -> set[str]:
    """The permissions of every user who can sign in through a login method."""
    if provider is None:
        return set()
    permissions: set[str] = set()
    for identity in UserAuthIdentity.query.filter_by(auth_provider_id=provider.id).all():
        permissions |= permissions_of(identity.user)
    return permissions
