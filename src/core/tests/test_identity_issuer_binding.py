"""Identity links of a SAML federation provider stay bound to the IdP that created them.

A federation provider stands for every IdP of the federation. Matching a returning
user by external id or username alone let any of those IdPs log in as another
institution's user; the link now records its issuer and only that IdP gets in.
"""

from __future__ import annotations

import importlib.util
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest
from auth.base_authenticator import ExternalIdentity
from managers import auth_manager
from model import auth_provider
from model.auth_provider import IdentityIssuerMismatchError, UserAuthIdentity

MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "d4a7f2c9e1b6_identity_issuer.py"
IDP_A = "https://idp.example.org/idp"
IDP_B = "https://idp.rogue.test/idp"


@pytest.fixture
def commits(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    done: list[bool] = []
    monkeypatch.setattr(auth_provider, "db", SimpleNamespace(session=SimpleNamespace(commit=lambda: done.append(True))))
    return done


def _link(**overrides: object) -> SimpleNamespace:
    defaults = {"id": 5, "external_username": "alice@example.org", "external_id": "id-1", "issuer": IDP_A, "user": "alice"}
    return SimpleNamespace(**{**defaults, **overrides})


def _matching(monkeypatch: pytest.MonkeyPatch, link: SimpleNamespace | None) -> None:
    monkeypatch.setattr(UserAuthIdentity, "_match", classmethod(lambda _cls, *_args: link))


def test_the_bound_idp_gets_in(monkeypatch: pytest.MonkeyPatch, commits: list[bool]) -> None:
    link = _link()
    _matching(monkeypatch, link)

    found = UserAuthIdentity.find_by_external(1, "id-1", "alice@example.org", IDP_A, bind_issuer=True, scoped=True)

    assert found is link
    assert commits == []


@pytest.mark.parametrize("scoped", [True, False])
def test_another_idp_is_refused_even_with_the_same_identifiers(monkeypatch: pytest.MonkeyPatch, commits: list[bool], scoped: bool) -> None:
    link = _link()
    _matching(monkeypatch, link)

    with pytest.raises(IdentityIssuerMismatchError, match=IDP_B):
        UserAuthIdentity.find_by_external(1, "id-1", "alice@example.org", IDP_B, bind_issuer=True, scoped=scoped)

    assert link.issuer == IDP_A
    assert commits == []


def test_a_link_without_issuer_is_bound_by_its_scoped_username(monkeypatch: pytest.MonkeyPatch, commits: list[bool]) -> None:
    link = _link(issuer=None, external_id=None)
    _matching(monkeypatch, link)

    found = UserAuthIdentity.find_by_external(1, "id-1", "alice@example.org", IDP_A, bind_issuer=True, scoped=True)

    assert found is link
    assert (link.issuer, link.external_id) == (IDP_A, "id-1")
    assert commits == [True]


@pytest.mark.parametrize(
    ("username", "scoped"),
    [
        ("alice", False),  # unscoped: any IdP of the federation could assert it
        ("bob@example.org", True),  # matched by external id, but the username is somebody else's
    ],
)
def test_a_link_without_issuer_is_refused_without_its_own_scoped_username(
    monkeypatch: pytest.MonkeyPatch,
    commits: list[bool],
    username: str,
    scoped: bool,
) -> None:
    link = _link(issuer=None, external_username="alice" if not scoped else "alice@example.org")
    _matching(monkeypatch, link)

    with pytest.raises(IdentityIssuerMismatchError):
        UserAuthIdentity.find_by_external(1, "id-1", username, IDP_A, bind_issuer=True, scoped=scoped)

    assert link.issuer is None
    assert commits == []


def test_outside_a_federation_the_issuer_is_only_recorded(monkeypatch: pytest.MonkeyPatch, commits: list[bool]) -> None:
    link = _link(issuer="https://old-idp.example.org/idp")
    _matching(monkeypatch, link)

    found = UserAuthIdentity.find_by_external(1, "id-1", "alice", IDP_A)

    assert found is link
    assert link.issuer == IDP_A
    assert commits == [True]


def test_providers_without_issuer_change_nothing(monkeypatch: pytest.MonkeyPatch, commits: list[bool]) -> None:
    link = _link(issuer=None)
    _matching(monkeypatch, link)

    assert UserAuthIdentity.find_by_external(1, "id-1", "alice") is link
    assert link.issuer is None
    assert commits == []


def test_no_match_is_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    _matching(monkeypatch, None)

    assert UserAuthIdentity.find_by_external(1, "id-1", "alice@example.org", IDP_B, bind_issuer=True, scoped=True) is None


@pytest.mark.parametrize(
    ("kind", "config", "expected"),
    [
        ("saml", {"discovery_url": "https://ds.example.org"}, True),
        ("saml", {"idp_entity_id": IDP_A}, False),
        ("oidc", {"discovery_url": "https://ds.example.org"}, False),
        ("saml", None, False),
    ],
)
def test_only_a_saml_federation_binds_issuers(kind: str, config: dict | None, expected: bool) -> None:
    assert UserAuthIdentity.binds_issuer(SimpleNamespace(kind=kind, config=config)) is expected  # ty: ignore[invalid-argument-type]


# --- the login path -------------------------------------------------------------------------


def _federation(**overrides: object) -> SimpleNamespace:
    defaults = {
        "id": 3,
        "name": "eduID",
        "kind": "saml",
        "config": {"discovery_url": "https://ds.example.org"},
        "provisioning_mode": "automatic",
        "get_allowed_domains": list,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _identity(username: str = "alice@example.org", *, scoped: bool = True, email: str | None = None) -> ExternalIdentity:
    return ExternalIdentity(username, "id-1", "Alice", email, IDP_B, scoped)


@pytest.fixture
def login(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    errors: list[str] = []
    calls: list[tuple] = []
    monkeypatch.setattr(auth_manager.log_manager, "store_auth_error_activity", lambda message, *_args: errors.append(message))
    monkeypatch.setattr(auth_manager.log_manager, "store_user_activity", lambda *_args: None)
    monkeypatch.setattr(
        auth_manager,
        "_finalize_login",
        lambda _provider, user: ({"access_token": f"jwt-for-{user.username}"}, HTTPStatus.OK),
    )

    def provision(_cls: type, *args: object, **kwargs: object) -> SimpleNamespace:
        calls.append(("provision", args, kwargs))
        return SimpleNamespace(username=args[1], status="active")

    def adopt(_cls: type, *args: object, **kwargs: object) -> object:
        calls.append(("adopt", args, kwargs))
        return args[1]

    monkeypatch.setattr(auth_manager.User, "provision_external", classmethod(provision))
    monkeypatch.setattr(auth_manager.User, "adopt_external", classmethod(adopt))
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, _username: None))
    return SimpleNamespace(errors=errors, calls=calls)


def test_a_link_of_another_idp_is_refused_and_never_provisioned(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    seen: list[dict] = []

    def bound_elsewhere(_cls: type, *_args: object, **kwargs: object) -> None:
        seen.append(kwargs)
        msg = f"identity link 5 is bound to '{IDP_A}', not to '{IDP_B}'"
        raise IdentityIssuerMismatchError(msg)

    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(bound_elsewhere))

    response, status = auth_manager._provision_and_issue_jwt(_federation(), _identity())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "IDP_MISMATCH"
    assert seen == [{"bind_issuer": True, "scoped": True}]
    assert login.calls == []
    assert IDP_A in login.errors[0]
    assert IDP_B in login.errors[0]


def test_losing_the_provisioning_race_to_another_idp_reports_the_mismatch(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    rollbacks: list[bool] = []
    monkeypatch.setattr(auth_manager, "db", SimpleNamespace(session=SimpleNamespace(rollback=lambda: rollbacks.append(True))))
    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args, **_kwargs: None))

    def lost_race(_cls: type, *_args: object, **_kwargs: object) -> None:
        msg = f"identity link 5 is bound to '{IDP_A}', not to '{IDP_B}'"
        raise IdentityIssuerMismatchError(msg)

    monkeypatch.setattr(auth_manager.User, "provision_external", classmethod(lost_race))

    response, status = auth_manager.provision_and_issue_jwt(_federation(), _identity())

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "IDP_MISMATCH"
    assert rollbacks == [True]
    assert IDP_A in login.errors[0]


def test_a_new_federation_user_is_provisioned_bound_to_its_idp(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args, **_kwargs: None))

    response, status = auth_manager._provision_and_issue_jwt(_federation(), _identity())

    assert status == HTTPStatus.OK
    assert response == {"access_token": "jwt-for-alice@example.org"}
    assert login.calls[0][0] == "provision"
    assert login.calls[0][2] == {"issuer": IDP_B}


def _orphan(username: str) -> SimpleNamespace:
    return SimpleNamespace(username=username, status="active", password=None, auth_identities=[], webauthn_credentials=[])


def test_an_unscoped_username_never_adopts_an_orphan_in_a_federation(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args, **_kwargs: None))
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, username: _orphan(username)))

    response, status = auth_manager._provision_and_issue_jwt(_federation(), _identity("admin", scoped=False))

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "USERNAME_COLLISION"
    assert login.calls == []


def test_a_scoped_username_adopts_its_orphan_bound_to_the_idp(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args, **_kwargs: None))
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, username: _orphan(username)))

    _response, status = auth_manager._provision_and_issue_jwt(_federation(), _identity())

    assert status == HTTPStatus.OK
    assert login.calls[0][0] == "adopt"
    assert login.calls[0][2] == {"issuer": IDP_B}


def test_an_unscoped_username_still_adopts_outside_a_federation(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args, **_kwargs: None))
    monkeypatch.setattr(auth_manager.User, "find", classmethod(lambda _cls, username: _orphan(username)))
    single_idp = _federation(config={"idp_entity_id": IDP_B})

    _response, status = auth_manager._provision_and_issue_jwt(single_idp, _identity("alice", scoped=False))

    assert status == HTTPStatus.OK
    assert login.calls[0][0] == "adopt"


def test_a_mail_dropped_as_out_of_scope_cannot_pass_the_domain_filter(monkeypatch: pytest.MonkeyPatch, login: SimpleNamespace) -> None:
    monkeypatch.setattr(UserAuthIdentity, "find_by_external", classmethod(lambda _cls, *_args, **_kwargs: None))
    provider = _federation(get_allowed_domains=lambda: ["victim.test"])

    response, status = auth_manager._provision_and_issue_jwt(provider, _identity(email=None))

    assert status == HTTPStatus.FORBIDDEN
    assert response["code"] == "DOMAIN_NOT_ALLOWED"
    assert login.calls == []


def test_the_migration_adds_the_nullable_column_the_model_declares() -> None:
    spec = importlib.util.spec_from_file_location("identity_issuer_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert (module.revision, module.down_revision) == ("d4a7f2c9e1b6", "7a4c1e9b2d36")
    assert UserAuthIdentity.__tablename__ == module.TABLE
    assert module.COLUMN == "issuer"
    assert UserAuthIdentity.__table__.c.issuer.nullable is True
