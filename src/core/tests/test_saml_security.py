"""SAML request binding, signed-root checks, replay and input bounds."""

from __future__ import annotations

import base64
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from auth import saml_replay
from auth.saml_authenticator import MAX_SAML_RESPONSE_ENCODED_BYTES, SamlAuthenticator, _enforce_saml_binding
from auth.saml_xml import inspect_verified_saml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from minisignxml.sign import sign

SAML = "urn:oasis:names:tc:SAML:2.0:assertion"
SAMLP = "urn:oasis:names:tc:SAML:2.0:protocol"
SP_ENTITY_ID = "https://sp.example.org/metadata"
IDP_ENTITY_ID = "https://idp.example.org/metadata"
ACS_URL = "https://sp.example.org/api/v1/auth/saml/test/acs"
REQUEST_ID = "_request"


@pytest.fixture(scope="module")
def idp_keypair() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-idp")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, certificate


@pytest.fixture
def authenticator(make_authenticator, idp_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate]) -> SamlAuthenticator:  # noqa: ANN001
    _key, certificate = idp_keypair
    return make_authenticator(
        {
            "sp_entity_id": SP_ENTITY_ID,
            "idp_entity_id": IDP_ENTITY_ID,
            "idp_certificate": certificate.public_bytes(serialization.Encoding.PEM).decode(),
        },
        provider_id=7,
    )


@pytest.fixture(autouse=True)
def quiet_auth_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("auth.saml_authenticator.log_manager.store_auth_error_activity", lambda *_args, **_kwargs: None)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _response(
    key: rsa.RSAPrivateKey,
    certificate: x509.Certificate,
    *,
    signed_root: str = "response",
    in_response_to: str | None = REQUEST_ID,
    recipient: str | None = ACS_URL,
    destination: str | None = ACS_URL,
    response_id: str | None = "_response",
    assertion_id: str | None = "_assertion",
    lifetime: timedelta = timedelta(minutes=5),
    additional_confirmation: tuple[str, str] | None = None,
) -> str:
    now = datetime.now(UTC)
    confirmation_attrs = f' NotOnOrAfter="{_timestamp(now + lifetime)}"'
    if in_response_to is not None:
        confirmation_attrs += f' InResponseTo="{in_response_to}"'
    if recipient is not None:
        confirmation_attrs += f' Recipient="{recipient}"'
    confirmations = (
        '<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">'
        f"<saml:SubjectConfirmationData{confirmation_attrs}/></saml:SubjectConfirmation>"
    )
    if additional_confirmation is not None:
        extra_request, extra_recipient = additional_confirmation
        confirmations += (
            '<saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">'
            f'<saml:SubjectConfirmationData InResponseTo="{extra_request}" Recipient="{extra_recipient}" '
            f'NotOnOrAfter="{_timestamp(now + lifetime)}"/></saml:SubjectConfirmation>'
        )
    assertion = etree.fromstring(
        (
            f'<saml:Assertion xmlns:saml="{SAML}"'
            f'{f" ID={assertion_id!r}" if assertion_id else ""} Version="2.0" IssueInstant="{_timestamp(now)}">'
            f"<saml:Issuer>{IDP_ENTITY_ID}</saml:Issuer>"
            "<saml:Subject><saml:NameID>alice</saml:NameID>"
            f"{confirmations}</saml:Subject>"
            f'<saml:Conditions NotBefore="{_timestamp(now - timedelta(minutes=1))}" '
            f'NotOnOrAfter="{_timestamp(now + lifetime)}">'
            f"<saml:AudienceRestriction><saml:Audience>{SP_ENTITY_ID}</saml:Audience></saml:AudienceRestriction>"
            "</saml:Conditions>"
            f'<saml:AuthnStatement AuthnInstant="{_timestamp(now)}"/>'
            "</saml:Assertion>"
        ).encode(),
    )
    if signed_root == "assertion":
        assertion = etree.fromstring(sign(element=assertion, private_key=key, certificate=certificate))

    response_attrs = f' Version="2.0" IssueInstant="{_timestamp(now)}"'
    if response_id is not None:
        response_attrs += f' ID="{response_id}"'
    if destination is not None:
        response_attrs += f' Destination="{destination}"'
    response = etree.fromstring(
        f'<samlp:Response xmlns:samlp="{SAMLP}" xmlns:saml="{SAML}"{response_attrs}/>'.encode(),
    )
    etree.SubElement(response, f"{{{SAML}}}Issuer").text = IDP_ENTITY_ID
    response.append(assertion)
    response_xml = sign(element=response, private_key=key, certificate=certificate) if signed_root == "response" else etree.tostring(response)
    return base64.b64encode(response_xml).decode()


def test_valid_signed_response_checks_binding_and_claims_both_ids(
    authenticator: SamlAuthenticator,
    idp_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claimed: list[tuple[int, tuple[str, ...], datetime]] = []
    monkeypatch.setattr(saml_replay, "claim", lambda provider_id, ids, expiry: claimed.append((provider_id, ids, expiry)) or True)

    identity = authenticator.handle_response(_response(*idp_keypair), REQUEST_ID, ACS_URL)

    assert identity is not None
    assert identity.username == "alice"
    assert claimed[0][0:2] == (7, ("_response", "_assertion"))


def test_binding_selector_accepts_any_signed_bearer_confirmation(
    idp_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    _key, certificate = idp_keypair
    xml = base64.b64decode(
        _response(
            *idp_keypair,
            in_response_to="_other_request",
            recipient="https://other.example/acs",
            additional_confirmation=(REQUEST_ID, ACS_URL),
        ),
        validate=True,
    )
    details = inspect_verified_saml(xml, [certificate])

    _enforce_saml_binding(
        details,
        REQUEST_ID,
        ACS_URL,
    )
    assert details.bearer_confirmations == (
        ("https://other.example/acs", "_other_request"),
        (ACS_URL, REQUEST_ID),
    )


@pytest.mark.parametrize("in_response_to", [None, "_different"])
def test_missing_or_mismatched_in_response_to_is_rejected(authenticator, idp_keypair, monkeypatch, in_response_to) -> None:  # noqa: ANN001
    monkeypatch.setattr(saml_replay, "claim", lambda *_args: True)
    assert authenticator.handle_response(_response(*idp_keypair, in_response_to=in_response_to), REQUEST_ID, ACS_URL) is None


@pytest.mark.parametrize("recipient", [None, "https://attacker.example/acs"])
def test_missing_or_mismatched_recipient_is_rejected(authenticator, idp_keypair, monkeypatch, recipient) -> None:  # noqa: ANN001
    monkeypatch.setattr(saml_replay, "claim", lambda *_args: True)
    assert authenticator.handle_response(_response(*idp_keypair, recipient=recipient), REQUEST_ID, ACS_URL) is None


def test_signed_response_destination_must_match_when_present(authenticator, idp_keypair, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(saml_replay, "claim", lambda *_args: True)
    assert authenticator.handle_response(_response(*idp_keypair, destination="https://attacker.example/acs"), REQUEST_ID, ACS_URL) is None
    assert authenticator.handle_response(_response(*idp_keypair, destination=None), REQUEST_ID, ACS_URL) is not None


def test_signed_assertion_does_not_require_unsigned_response_id(authenticator, idp_keypair, monkeypatch) -> None:  # noqa: ANN001
    claimed: list[tuple[str, ...]] = []
    monkeypatch.setattr(saml_replay, "claim", lambda _provider_id, ids, _expiry: claimed.append(ids) or True)

    identity = authenticator.handle_response(
        _response(*idp_keypair, signed_root="assertion", response_id=None, destination="https://unsigned.example/acs"),
        REQUEST_ID,
        ACS_URL,
    )

    assert identity is not None
    assert claimed == [("_assertion",)]


def test_missing_id_on_assertion_protected_by_signed_response_is_rejected(authenticator, idp_keypair, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(saml_replay, "claim", lambda *_args: True)
    assert authenticator.handle_response(_response(*idp_keypair, assertion_id=None), REQUEST_ID, ACS_URL) is None


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("not base64!", id="not-base64"),
        # Named, because pytest derives the test ID from the value itself: unnamed, this
        # one spells the whole 1.4 MB payload into every -v run and CI log line.
        pytest.param("A" * (MAX_SAML_RESPONSE_ENCODED_BYTES + 1), id="oversized"),
    ],
)
def test_malformed_or_oversized_saml_response_is_rejected_without_replay_claim(authenticator, monkeypatch, value: str) -> None:  # noqa: ANN001
    claimed = False

    def claim(*_args) -> bool:  # noqa: ANN002
        nonlocal claimed
        claimed = True
        return True

    monkeypatch.setattr(saml_replay, "claim", claim)
    assert authenticator.handle_response(value, REQUEST_ID, ACS_URL) is None
    assert claimed is False


class MemoryRedis:
    """Atomic-enough stand-in for the replay Lua script."""

    def __init__(self) -> None:
        """Create an empty, locked key store."""
        self.keys: set[str] = set()
        self.ttls: list[int] = []
        self.lock = threading.Lock()

    def eval(self, _script: str, key_count: int, *args: object) -> int:
        """Apply the replay script's all-or-nothing claim semantics."""
        keys = tuple(str(value) for value in args[:key_count])
        ttl = int(args[key_count])
        with self.lock:
            if any(key in self.keys for key in keys):
                return 0
            self.keys.update(keys)
            self.ttls.append(ttl)
            return 1


def test_response_and_assertion_ids_are_claimed_atomically_until_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(saml_replay, "redis_client", redis)
    expiry = datetime.now(UTC) + timedelta(minutes=5)

    assert saml_replay.claim(7, ("_response", "_assertion"), expiry) is True
    assert saml_replay.claim(7, ("_new_response", "_assertion"), expiry) is False
    assert len(redis.keys) == 2
    assert 1 <= redis.ttls[0] <= 300


def test_only_one_concurrent_replay_claim_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(saml_replay, "redis_client", redis)
    expiry = datetime.now(UTC) + timedelta(minutes=5)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _index: saml_replay.claim(7, ("_assertion",), expiry), range(16)))

    assert results.count(True) == 1
    assert results.count(False) == 15


def test_overlong_assertion_lifetime_is_rejected_before_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = MemoryRedis()
    monkeypatch.setattr(saml_replay, "redis_client", redis)
    expiry = datetime.now(UTC) + timedelta(seconds=saml_replay.MAX_ASSERTION_LIFETIME_SECONDS + 1)

    with pytest.raises(ValueError, match="lifetime exceeds"):
        saml_replay.claim(7, ("_assertion",), expiry)
    assert redis.keys == set()
