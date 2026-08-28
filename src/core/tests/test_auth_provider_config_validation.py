"""Save-time validation of the OAuth2/OIDC provider config dict.

The GUI enforces these rules in its forms, but ``config`` is a free-form JSON
dict writable through the API: an invalid value that passed the GUI checks
would otherwise only surface as an opaque "auth_failed" on the first login.
These tests exercise :meth:`AuthProvider._validate_oidc_config` directly, which
only reads the dict it is handed — no database, no application context.
"""

from __future__ import annotations

import pytest
from model.auth_provider import AuthProvider

validate = AuthProvider._validate_oidc_config


def _config(**overrides: object) -> dict:
    """A minimal valid oidc config, with the internal-issuer keys on top."""
    config: dict = {"issuer_url": "https://idp.example.com", "client_id": "taranis"}
    config.update(overrides)
    return config


# --- normalisation ----------------------------------------------------------


def test_whitespace_only_internal_issuer_is_dropped_not_kept() -> None:
    # Runtime treats blank as set (" " is truthy), which would send every
    # back-channel request to an invalid URL; the save must normalise it away.
    config = _config(internal_issuer_url="   ", allow_insecure_internal_transport=True)
    validate(config)
    assert "internal_issuer_url" not in config
    # and the now-meaningless opt-in is dropped with it
    assert "allow_insecure_internal_transport" not in config


def test_internal_issuer_is_trimmed() -> None:
    config = _config(internal_issuer_url="  https://kc.internal:8443  ")
    validate(config)
    assert config["internal_issuer_url"] == "https://kc.internal:8443"


def test_leading_space_internal_issuer_over_plain_http_is_rejected() -> None:
    # The GUI rule rejects this, but the API must not accept it either: the
    # trimmed value is a plain-HTTP internal issuer with no opt-in.
    with pytest.raises(ValueError, match="HTTPS"):
        validate(_config(internal_issuer_url=" http://keycloak:8080"))


# --- flag coercion ----------------------------------------------------------


def test_flag_string_false_is_normalised_to_false_not_implicitly_enabled() -> None:
    # bool("false") would be True — an implicit opt-in to cleartext transport.
    # The saver normalises it to a real False.
    config = _config(internal_issuer_url="https://kc.internal:8443", allow_insecure_internal_transport="false")
    validate(config)
    assert config["allow_insecure_internal_transport"] is False


@pytest.mark.parametrize("spelling", ["true", "True", "1", "yes", "on", " TRUE "])
def test_flag_truthy_spellings_are_normalised_to_true(spelling: str) -> None:
    config = _config(internal_issuer_url="http://keycloak:8080", allow_insecure_internal_transport=spelling)
    validate(config)
    assert config["allow_insecure_internal_transport"] is True


@pytest.mark.parametrize("spelling", ["false", "False", "0", "no", "off", ""])
def test_flag_falsy_spellings_are_normalised_to_false(spelling: str) -> None:
    # https internal issuer: after normalisation nothing else can fire, so the
    # flag value itself is what is under test.
    config = _config(internal_issuer_url="https://kc.internal:8443", allow_insecure_internal_transport=spelling)
    validate(config)
    assert config["allow_insecure_internal_transport"] is False


@pytest.mark.parametrize("spelling", ["false", "0", "no", "off", ""])
def test_falsy_flag_over_plain_http_does_not_enable_the_opt_in(spelling: str) -> None:
    # Combined semantics: normalising the spelling to False leaves a plain-HTTP
    # internal issuer without a (truthy) opt-in, which must be rejected.
    with pytest.raises(ValueError, match="HTTPS"):
        validate(_config(internal_issuer_url="http://keycloak:8080", allow_insecure_internal_transport=spelling))


def test_flag_integer_one_is_accepted() -> None:
    config = _config(internal_issuer_url="http://keycloak:8080", allow_insecure_internal_transport=1)
    validate(config)
    assert config["allow_insecure_internal_transport"] is True


def test_flag_integer_zero_over_https_internal_is_normalised_to_false() -> None:
    config = _config(internal_issuer_url="https://kc.internal:8443", allow_insecure_internal_transport=0)
    validate(config)
    assert config["allow_insecure_internal_transport"] is False


@pytest.mark.parametrize("value", [[], {}, "maybe"])
def test_flag_unrecognised_types_are_rejected(value: object) -> None:
    with pytest.raises(ValueError, match="boolean"):
        validate(_config(internal_issuer_url="https://kc.internal:8443", allow_insecure_internal_transport=value))


def test_flag_is_dropped_when_no_internal_issuer_remains() -> None:
    # A stale opt-in without an internal issuer is a no-op at runtime; dropping
    # it stops a later re-added URL from silently inheriting it.
    config = _config(allow_insecure_internal_transport=True)
    validate(config)
    assert "allow_insecure_internal_transport" not in config


def test_real_booleans_pass_through_unchanged() -> None:
    config = _config(internal_issuer_url="http://keycloak:8080", allow_insecure_internal_transport=True)
    validate(config)
    assert config["allow_insecure_internal_transport"] is True


# --- URL checks -------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    ["https://kc.internal:8443", "http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]:8080"],
)
def test_https_or_loopback_http_internals_are_accepted(url: str) -> None:
    validate(_config(internal_issuer_url=url))


def test_plain_http_internal_issuer_without_opt_in_is_rejected() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        validate(_config(internal_issuer_url="http://keycloak:8080"))


def test_plain_http_internal_issuer_with_opt_in_is_accepted() -> None:
    validate(_config(internal_issuer_url="http://keycloak:8080", allow_insecure_internal_transport=True))


@pytest.mark.parametrize("url", ["keycloak:8080", "ftp://kc.internal"])
def test_non_http_scheme_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="http\\(s\\) URL"):
        validate(_config(internal_issuer_url=url))


def test_credentials_in_the_url_are_rejected() -> None:
    with pytest.raises(ValueError, match="credentials"):
        validate(_config(internal_issuer_url="https://user:pass@kc.internal:8443"))


def test_fragment_in_the_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="fragment"):
        validate(_config(internal_issuer_url="https://kc.internal:8443/#frag"))


def test_hostless_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="host"):
        validate(_config(internal_issuer_url="https://"))


# --- untouched providers ----------------------------------------------------


def test_oidc_config_without_internal_issuer_passes() -> None:
    config = _config()
    validate(config)
    assert config["issuer_url"] == "https://idp.example.com"


def test_oauth2_kind_config_with_no_oidc_keys_passes() -> None:
    validate({"authorize_url": "https://login.example.com/authorize", "token_url": "https://login.example.com/token"})


def test_unrelated_config_keys_are_left_alone() -> None:
    config = _config(pkce_method="S256", scopes="openid profile")
    validate(config)
    assert config["pkce_method"] == "S256"
    assert config["scopes"] == "openid profile"
