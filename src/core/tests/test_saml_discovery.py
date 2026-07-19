"""SAMLDS discovery-service URL building and mode detection.

Federation mode sends the user to a WAYF following the SAML Identity Provider
Discovery Service protocol; an optional discovery-service filter parameter
rides along as an opaque pass-through.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

SP = "https://taranis.example.org/sp"
DISCO_RETURN = "https://taranis.example.org/api/v1/auth/saml/1/disco?state=STATE"
ACS = "https://taranis.example.org/api/v1/auth/saml/1/acs"


def test_is_federation_true_when_discovery_url_configured(make_authenticator) -> None:
    auth = make_authenticator({"sp_entity_id": SP, "discovery_url": "https://ds.example.org/wayf"})
    assert auth.is_federation() is True


def test_is_federation_false_for_single_idp(make_authenticator) -> None:
    auth = make_authenticator({"sp_entity_id": SP, "idp_sso_url": "https://idp/sso"})
    assert auth.is_federation() is False


def test_discovery_url_carries_samlds_parameters(make_authenticator) -> None:
    auth = make_authenticator({"sp_entity_id": SP, "discovery_url": "https://ds.example.org/wayf"})
    url = auth.get_discovery_redirect_url(DISCO_RETURN)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "ds.example.org"
    assert query["entityID"] == [SP]
    assert query["return"] == [DISCO_RETURN]
    assert query["returnIDParam"] == ["idp_entity_id"]


def test_discovery_params_are_passed_through_verbatim(make_authenticator) -> None:
    auth = make_authenticator(
        {"sp_entity_id": SP, "discovery_url": "https://ds.example.org/wayf", "discovery_params": "filter=eyAgImFsbG93SG9zdGVsIjogdHJ1ZSB9"},
    )
    query = parse_qs(urlparse(auth.get_discovery_redirect_url(DISCO_RETURN)).query)
    assert query["filter"] == ["eyAgImFsbG93SG9zdGVsIjogdHJ1ZSB9"]


def test_discovery_url_preserves_existing_query(make_authenticator) -> None:
    auth = make_authenticator({"sp_entity_id": SP, "discovery_url": "https://ds.example.org/wayf?lang=en"})
    query = parse_qs(urlparse(auth.get_discovery_redirect_url(DISCO_RETURN)).query)
    assert query["lang"] == ["en"]
    assert query["entityID"] == [SP]


def test_authn_request_url_targets_the_given_sso_endpoint(make_authenticator) -> None:
    auth = make_authenticator({"sp_entity_id": SP})
    url = auth.get_authn_request_url("https://idp.example.org/sso", ACS, relay_state="RELAY", request_id="_abc")
    assert url.startswith("https://idp.example.org/sso")
    query = parse_qs(urlparse(url).query)
    assert "SAMLRequest" in query
    assert query["RelayState"] == ["RELAY"]
