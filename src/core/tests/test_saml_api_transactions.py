"""SAML browser state is opaque, typed and consumed exactly once."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace

from api import auth
from flask import Flask
from managers import auth_manager
from managers.auth_transaction_manager import AuthTransactionKind

app = Flask(__name__)


class FakeSamlAuthenticator:
    """SAML authenticator double recording request and response bindings."""

    def __init__(self) -> None:
        """Create a provider and empty call records."""
        self.provider = SimpleNamespace(id=23)
        self.config: dict = {}
        self.login_call: tuple[str, str, str] | None = None
        self.response_call: tuple[str, str, str, str | None] | None = None

    @staticmethod
    def is_federation() -> bool:
        """Use the direct single-IdP flow."""
        return False

    def get_login_redirect_url(self, acs_url: str, relay_state: str, request_id: str) -> str:
        """Record the server-side binding and return a deterministic redirect."""
        self.login_call = (acs_url, relay_state, request_id)
        return f"https://idp.example/sso?RelayState={relay_state}"

    def handle_response(
        self,
        saml_response: str,
        request_id: str,
        acs_url: str,
        idp_entity_id: str | None,
    ) -> object:
        """Record the values recovered from consumed state."""
        self.response_call = (saml_response, request_id, acs_url, idp_entity_id)
        return object()


def _store(monkeypatch):  # noqa: ANN001, ANN202
    values: dict[tuple[AuthTransactionKind, str], dict] = {}
    created: list[tuple[AuthTransactionKind, dict, int, str]] = []
    tokens = iter(("A" * 43, "B" * 43, "C" * 43))

    def create(kind: AuthTransactionKind, payload: dict, ttl_seconds: int) -> str:
        token = next(tokens)
        values[(kind, token)] = payload
        created.append((kind, payload, ttl_seconds, token))
        return token

    def consume(kind: AuthTransactionKind, token: str) -> dict | None:
        return values.pop((kind, token), None)

    monkeypatch.setattr(auth.auth_transaction_manager, "create", create)
    monkeypatch.setattr(auth.auth_transaction_manager, "consume", consume)
    return values, created


def test_saml_login_uses_opaque_server_side_request_state(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeSamlAuthenticator()
    _values, created = _store(monkeypatch)
    monkeypatch.setattr(auth_manager, "get_saml_authenticator", lambda _slug: authenticator)

    with app.test_request_context(
        "/api/v1/auth/saml/corporate/login?gotoUrl=/v2/dashboard",
        base_url="https://taranis.example",
    ):
        response = auth.SamlLoginRedirect.get.__wrapped__(auth.SamlLoginRedirect(), "corporate")

    kind, payload, ttl, token = created[0]
    assert kind is AuthTransactionKind.SAML_STATE
    assert payload["provider_id"] == 23
    assert payload["goto_url"] == "/v2/dashboard"
    assert payload["acs_url"] == "https://taranis.example/api/v1/auth/saml/corporate/acs"
    assert payload["request_id"].startswith("_")
    assert token == "A" * 43
    assert "." not in token
    assert ttl == auth_manager.OAUTH_STATE_MINUTES * 60
    assert authenticator.login_call == (payload["acs_url"], token, payload["request_id"])
    assert response.location.endswith(token)


def test_saml_acs_consumes_state_and_passes_stored_binding_once(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeSamlAuthenticator()
    values, _created = _store(monkeypatch)
    state = "A" * 43
    values[(AuthTransactionKind.SAML_STATE, state)] = {
        "provider_id": 23,
        "goto_url": "/v2/dashboard",
        "request_id": "_request",
        "acs_url": "https://taranis.example/api/v1/auth/saml/corporate/acs",
        "idp_entity_id": "https://idp.example/metadata",
    }
    monkeypatch.setattr(auth_manager, "get_saml_authenticator", lambda _slug: authenticator)
    monkeypatch.setattr(
        auth_manager,
        "provision_and_issue_jwt",
        lambda _provider, _identity: ({"access_token": "jwt"}, HTTPStatus.OK),
    )

    with app.test_request_context(
        "/api/v1/auth/saml/corporate/acs",
        method="POST",
        base_url="https://taranis.example",
        data={"RelayState": state, "SAMLResponse": "signed-response"},
    ):
        response = auth.SamlAcs.post.__wrapped__(auth.SamlAcs(), "corporate")

    assert response.status_code == HTTPStatus.FOUND
    assert authenticator.response_call == (
        "signed-response",
        "_request",
        "https://taranis.example/api/v1/auth/saml/corporate/acs",
        "https://idp.example/metadata",
    )

    with app.test_request_context(
        "/api/v1/auth/saml/corporate/acs",
        method="POST",
        base_url="https://taranis.example",
        data={"RelayState": state, "SAMLResponse": "signed-response"},
    ):
        replay = auth.SamlAcs.post.__wrapped__(auth.SamlAcs(), "corporate")
    assert replay == ({"error": "Invalid state"}, HTTPStatus.UNAUTHORIZED)


def test_saml_acs_rejects_oversized_form_before_consuming_state(monkeypatch) -> None:  # noqa: ANN001
    authenticator = FakeSamlAuthenticator()
    values, _created = _store(monkeypatch)
    state = "A" * 43
    values[(AuthTransactionKind.SAML_STATE, state)] = {"provider_id": 23}
    monkeypatch.setattr(auth_manager, "get_saml_authenticator", lambda _slug: authenticator)
    monkeypatch.setattr(auth.saml_authenticator, "MAX_SAML_FORM_BYTES", 64)

    with app.test_request_context(
        "/api/v1/auth/saml/corporate/acs",
        method="POST",
        base_url="https://taranis.example",
        data={"RelayState": state, "SAMLResponse": "A" * 256},
    ):
        response = auth.SamlAcs.post.__wrapped__(auth.SamlAcs(), "corporate")

    assert response == ({"error": "SAML response is too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
    assert values[(AuthTransactionKind.SAML_STATE, state)] == {"provider_id": 23}
