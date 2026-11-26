"""A login method's stored secret is kept when the dialog leaves it empty, and removed only on request."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from model import auth_provider
from model.auth_provider import AuthProvider


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """A stored provider, and an update that touches no database."""
    record = SimpleNamespace(kind="oidc", secret="encrypted-secret", config={})
    validated: list[bool] = []
    monkeypatch.setattr(auth_provider.db.session, "get", lambda _model, _provider_id: record)
    monkeypatch.setattr(auth_provider.db.session, "commit", lambda: None)
    monkeypatch.setattr(
        AuthProvider,
        "_validate",
        classmethod(lambda _cls, _provider, _provider_id, *, keeps_stored_secret: validated.append(keeps_stored_secret)),
    )

    def load(data: dict) -> SimpleNamespace:
        assert "clear_secret" not in data  # the flag never reaches the schema
        return SimpleNamespace(
            slug="corp",
            name="Corp",
            secret=data.get("secret") or None,
            **dict.fromkeys(("enabled", "organization", "default_roles", "provisioning_mode", "allowed_domains", "require_mfa", "config")),
        )

    monkeypatch.setattr(auth_provider, "NewAuthProviderSchema", lambda: SimpleNamespace(load=load))
    record.validated = validated
    return record


@pytest.mark.parametrize(
    ("data", "secret", "keeps"),
    [
        ({}, "encrypted-secret", True),
        ({"clear_secret": False}, "encrypted-secret", True),
        ({"clear_secret": True}, None, False),
        ({"clear_secret": True, "secret": "new-encrypted"}, "new-encrypted", True),
    ],
)
def test_the_stored_secret_is_removed_only_on_request(stored: SimpleNamespace, data: dict, secret: str | None, keeps: bool) -> None:
    AuthProvider.update(1, {"name": "Corp", **data}, "admin")

    assert stored.secret == secret
    assert stored.validated == [keeps]
