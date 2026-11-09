"""Secrets the GUI never receives back: API keys of nodes and providers, secret parameter values.

Lists and dialogs get an empty value and whether one is stored (``api_key_set``,
``value_set``). An update that leaves a secret empty keeps the stored one, so a dialog can
be saved without retyping it; a new value replaces it.
"""

from __future__ import annotations

import re

from managers.db_manager import db

# Parameter keys whose values are credentials (see shared/config_*.py): passwords, tokens, API
# keys and the SSH private key.
SECRET_PARAMETER = re.compile(r"(PASSWORD|TOKEN|SECRET|API_KEY|SSH_KEY)$")


def keep_stored_api_key(data: object, model: type, record_id: object) -> object:
    """``data`` with the stored ``api_key`` of ``model`` ``record_id`` when the update leaves it empty.

    Args:
        data: The submitted record.
        model: Its model class.
        record_id: Its id.

    Returns:
        The data to update with.
    """
    if not isinstance(data, dict) or (data.get("api_key") or "").strip():
        return data
    stored = db.session.get(model, record_id)
    if stored is None or not stored.api_key:
        return data
    return {**data, "api_key": stored.api_key}


def is_secret_parameter(key: str | None) -> bool:
    """Whether a parameter (by its key) holds a credential."""
    return bool(key) and SECRET_PARAMETER.search(key) is not None


def hide_secret_parameters(dumped: object) -> object:
    """Blank the secret parameter values anywhere in a dumped response (sources, channels, presets, formats).

    Each ``parameter_values`` entry ``{"value", "parameter": {"key", ...}}`` of a secret parameter
    gets ``value: ""`` and ``value_set``; the others are left as they are. Nested records too
    (a remote access lists its sources).

    Args:
        dumped: The response (dicts and lists).

    Returns:
        The same response.
    """
    if isinstance(dumped, list):
        for entry in dumped:
            hide_secret_parameters(entry)
    elif isinstance(dumped, dict):
        for key, value in dumped.items():
            if key == "parameter_values" and isinstance(value, list):
                for parameter_value in value:
                    if isinstance(parameter_value, dict) and is_secret_parameter((parameter_value.get("parameter") or {}).get("key")):
                        parameter_value["value_set"] = bool(parameter_value.get("value"))
                        parameter_value["value"] = ""
            else:
                hide_secret_parameters(value)
    return dumped


def keep_secret_parameter(key: str | None, stored: str | None, submitted: str | None) -> str | None:
    """The value to store for a parameter: a secret left empty keeps the stored value.

    Args:
        key: The parameter's key.
        stored: The stored value.
        submitted: The value the update sends.

    Returns:
        The value to store.
    """
    if is_secret_parameter(key) and not (submitted or "").strip():
        return stored
    return submitted
