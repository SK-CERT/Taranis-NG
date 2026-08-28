"""Auto-provisioning heals orphaned accounts and never leaves one behind.

Issue #1515: a misconfigured OIDC provider left an account with no local password
and no identity at any provider - one nothing can log into - and the username
collision check then refused to provision the same person once the configuration
was fixed. Such an orphan is now adopted, a genuine collision still is not, and a
login that fails part-way rolls its account back instead of committing it.

Adoption re-provisions the row rather than inheriting it, so it can never hand
the authority an orphan happened to carry to whoever can present that username at
the identity provider, nor walk an already-active row past the approval step.
"""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

import pytest
from auth.base_authenticator import BaseAuthenticator, ExternalIdentity
from managers import auth_manager
from model.user import User


class FakeSession:
    """Records whether the failed login rolled its transaction back."""

    def __init__(self) -> None:
        """Start with no rollback recorded."""
        self.rollbacks = 0

    def rollback(self) -> None:
        """Record that the caller discarded the pending transaction."""
        self.rollbacks += 1


@pytest.fixture
def provisioning(monkeypatch) -> SimpleNamespace:  # noqa: ANN001
    """Isolate ``provision_and_issue_jwt`` from the database and the activity log."""
    session = FakeSession()
    activity: list[tuple] = []
    monkeypatch.setattr(auth_manager, "db", SimpleNamespace(session=session))
    log = auth_manager.log_manager
    monkeypatch.setattr(log, "store_auth_error_activity", lambda *args, **kwargs: activity.append(("error", args, kwargs)))
    monkeypatch.setattr(log, "store_user_activity", lambda *args: activity.append(("user", args)))
    monkeypatch.setattr(auth_manager.UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args: None))
    issue_jwt = lambda _provider, user: ({"access_token": f"jwt-for-{user.username}"}, HTTPStatus.OK)  # noqa: E731
    monkeypatch.setattr(auth_manager, "_finalize_login", issue_jwt)
    return SimpleNamespace(session=session, activity=activity)


def _provider(**overrides) -> SimpleNamespace:  # noqa: ANN003
    defaults = {
        "id": 17,
        "name": "Corporate login",
        "provisioning_mode": "automatic",
        "organization": "Default org",
        "default_roles": ["Reader"],
        "get_allowed_domains": list,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _orphan(**overrides) -> SimpleNamespace:  # noqa: ANN003
    """An account nothing can log into, with whatever authority it was left holding."""
    defaults = {
        "id": 42,
        "username": "alice",
        "name": "Stale Name",
        "email": None,
        "password": None,
        "status": "active",
        "auth_identities": [],
        "webauthn_credentials": [],
        "roles": [],
        "permissions": [],
        "organizations": [],
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _never_adopt(*_args: object) -> None:
    """Fail the test: an account that can still be logged into must never be adopted."""
    pytest.fail("a reachable account must never be adopted")


def _identity(username: str = "alice") -> ExternalIdentity:
    return ExternalIdentity(username=username, external_id="sub-1", name="Alice", email="alice@example.test")


def test_orphaned_account_is_adopted_instead_of_dead_ending(monkeypatch, provisioning) -> None:  # noqa: ANN001
    orphan = _orphan()
    adopted: list = []
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: orphan))

    def adopt(_cls: type, provider: object, user: object, username: str, name: str, email: str, external_id: str) -> object:
        adopted.append((provider, user, username, name, email, external_id))
        return user

    monkeypatch.setattr(auth_manager.User, "adopt_external", classmethod(adopt))

    response, status = auth_manager.provision_and_issue_jwt(_provider(), _identity())

    assert status == HTTPStatus.OK
    assert response == {"access_token": "jwt-for-alice"}
    assert adopted == [(adopted[0][0], orphan, "alice", "Alice", "alice@example.test", "sub-1")]
    logged = ("user", (orphan, "PROVISION", "Orphaned account re-provisioned via auth provider 'Corporate login' with status 'active'"))
    assert logged in provisioning.activity


def test_adoption_grants_the_provider_defaults_not_the_orphan_authority() -> None:
    """An orphaned administrator must not hand its rights to whoever claims the username."""
    orphan = _orphan(roles=["Admin"], permissions=["CONFIG_USER_UPDATE"], organizations=["Some other org"])

    User._apply_provider_defaults(orphan, _provider(), "Alice", "alice@example.test")

    assert orphan.roles == ["Reader"]
    assert orphan.permissions == []
    assert orphan.organizations == ["Default org"]
    # Display name and e-mail come from the provider too, exactly as on a fresh provision.
    assert (orphan.name, orphan.email) == ("Alice", "alice@example.test")


def test_adoption_under_approval_mode_still_needs_an_administrator(monkeypatch) -> None:  # noqa: ANN001
    """An already-active orphan must not walk past the approval the mode promises."""
    monkeypatch.setattr(auth_manager.log_manager, "store_auth_warning_activity", lambda *_args: None)
    orphan = _orphan(status="active")

    User._apply_provider_defaults(orphan, _provider(provisioning_mode="approval"), "Alice", None)

    assert orphan.status == "pending"
    response, status = BaseAuthenticator.check_user_status(SimpleNamespace(username="alice", status=orphan.status))
    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "PENDING_APPROVAL"


def test_account_with_a_local_password_is_still_a_collision(monkeypatch, provisioning) -> None:  # noqa: ANN001, ARG001
    existing = _orphan(password="pbkdf2:hash")
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: existing))
    monkeypatch.setattr(auth_manager.User, "adopt_external", classmethod(_never_adopt))

    response, status = auth_manager.provision_and_issue_jwt(_provider(), _identity())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "USERNAME_COLLISION"


def test_account_linked_to_another_provider_is_still_a_collision(monkeypatch, provisioning) -> None:  # noqa: ANN001, ARG001
    existing = _orphan(auth_identities=[SimpleNamespace(auth_provider_id=99)])
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: existing))
    monkeypatch.setattr(auth_manager.User, "adopt_external", classmethod(_never_adopt))

    response, status = auth_manager.provision_and_issue_jwt(_provider(), _identity())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "USERNAME_COLLISION"


def test_account_with_only_a_passkey_is_still_a_collision(monkeypatch, provisioning) -> None:  # noqa: ANN001, ARG001
    """A passkey is a passwordless login on its own, so such an account is not an orphan."""
    existing = _orphan(webauthn_credentials=[SimpleNamespace(id=1)])
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: existing))
    monkeypatch.setattr(auth_manager.User, "adopt_external", classmethod(_never_adopt))

    response, status = auth_manager.provision_and_issue_jwt(_provider(), _identity())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "USERNAME_COLLISION"


def test_manual_mode_rejects_before_it_could_adopt(monkeypatch, provisioning) -> None:  # noqa: ANN001, ARG001
    def _never_looked_up(*_args: object) -> None:
        pytest.fail("manual mode must not look for an account to adopt")

    monkeypatch.setattr(auth_manager.User, "find", classmethod(_never_looked_up))

    response, status = auth_manager.provision_and_issue_jwt(_provider(provisioning_mode="manual"), _identity())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "ACCOUNT_NOT_LINKED"


def test_a_failure_after_the_account_is_written_rolls_back(monkeypatch, provisioning) -> None:  # noqa: ANN001
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: None))
    provision = lambda *_args: SimpleNamespace(username="alice", status="active")  # noqa: E731
    monkeypatch.setattr(auth_manager.User, "provision_external", classmethod(provision))

    def explode(_provider: object, _user: object) -> None:
        msg = "the MFA gate blew up"
        raise RuntimeError(msg)

    monkeypatch.setattr(auth_manager, "_finalize_login", explode)

    response, status = auth_manager.provision_and_issue_jwt(_provider(), _identity())

    assert status == HTTPStatus.UNAUTHORIZED
    assert response == {"error": "Authentication failed"}
    # Without this the half-provisioned account survives and blocks every later
    # login attempt with USERNAME_COLLISION - exactly the reported dead end.
    assert provisioning.session.rollbacks == 1
