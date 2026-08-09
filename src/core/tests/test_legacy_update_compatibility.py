"""Legacy Vue 2 update payloads preserve newly added MFA policy fields."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from model import organization as organization_model
from model import user as user_model


def _session_for(record: object) -> SimpleNamespace:
    return SimpleNamespace(get=lambda _model, _record_id: record, commit=lambda: None)


def _vue2_user_payload(**extra: object) -> dict:
    """Match the object assembled by Vue 2's NewUser edit dialog."""
    return {
        "id": 7,
        "username": "alice",
        "name": "Alice Example",
        "organizations": [],
        "roles": [],
        "permissions": [],
        **extra,
    }


def _vue2_organization_payload(**extra: object) -> dict:
    """Match the object assembled by Vue 2's NewOrganization edit dialog."""
    return {
        "id": 11,
        "name": "Example Org",
        "description": "Updated by the legacy GUI",
        "address": {
            "street": "Main Street 1",
            "city": "Bratislava",
            "zip": "811 01",
            "country": "Slovakia",
        },
        **extra,
    }


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (_vue2_user_payload(), True),
        (_vue2_user_payload(require_mfa=False), False),
    ],
)
def test_vue2_user_put_preserves_omitted_mfa_but_honors_explicit_false(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict,
    expected: bool,
) -> None:
    stored_user = SimpleNamespace(
        username="before",
        name="Before",
        password="existing-hash",
        email=None,
        status="active",
        require_mfa=True,
        auth_identities=[],
        organizations=[],
        roles=[],
        permissions=[],
    )
    monkeypatch.setattr(user_model, "db", SimpleNamespace(session=_session_for(stored_user)))

    user_model.User.update(7, payload)

    assert stored_user.require_mfa is expected
    assert stored_user.username == "alice"
    assert stored_user.name == "Alice Example"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (_vue2_organization_payload(), True),
        (_vue2_organization_payload(require_mfa=False), False),
    ],
)
def test_vue2_organization_put_preserves_omitted_mfa_but_honors_explicit_false(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict,
    expected: bool,
) -> None:
    stored_organization = SimpleNamespace(
        name="Before",
        description="Before",
        require_mfa=True,
        address=SimpleNamespace(street="", city="", zip="", country=""),
    )
    monkeypatch.setattr(organization_model, "db", SimpleNamespace(session=_session_for(stored_organization)))

    organization_model.Organization.update(11, payload)

    assert stored_organization.require_mfa is expected
    assert stored_organization.name == "Example Org"
    assert stored_organization.address.city == "Bratislava"
