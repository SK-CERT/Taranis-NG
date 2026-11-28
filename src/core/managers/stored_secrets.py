"""Secrets the GUI never receives back: API keys of nodes and providers, secret parameter values.

Lists and dialogs get an empty value and whether one is stored (``api_key_set``,
``value_set``). An update that leaves a secret empty keeps the stored one, so a dialog can
be saved without retyping it; a new value replaces it. Removing a stored secret takes an
explicit request (``clear_api_key``, ``clear_stored`` on a parameter value), sent by the
dialog's remove button.
"""

from __future__ import annotations

import re

from managers.db_manager import db

# Parameter keys whose values are credentials (see shared/config_*.py): passwords, tokens, API
# keys and the SSH private key.
SECRET_PARAMETER = re.compile(r"(PASSWORD|TOKEN|SECRET|API_KEY|SSH_KEY)$")


class StoredSecretError(ValueError):
    """A stored secret would go somewhere other than where it was saved for; the caller answers 400."""


def _same_destination(submitted: object, stored: object) -> bool:
    """Whether two URLs, hosts or names are the same destination (whitespace and a trailing / aside)."""
    return _comparable(submitted) == _comparable(stored)


def _comparable(value: object) -> str:
    """A destination value as text: None and "" alike, a URL without its trailing /."""
    return "" if value is None else str(value).strip().rstrip("/")


def changed_destination(data: dict, stored: object, fields: tuple[str, ...]) -> list[str]:
    """The ``fields`` the submitted ``data`` changes from ``stored`` (attributes, or a dict's keys)."""
    read = stored.get if isinstance(stored, dict) else lambda field: getattr(stored, field, None)
    return [field for field in fields if field in data and not _same_destination(data.get(field), read(field))]


def refuse_moved_secret(changed: list[str], what: str = "API key") -> None:
    """Raise StoredSecretError when a kept secret's destination changed.

    "Saved empty keeps the stored secret" lets a dialog be saved without retyping a secret the
    GUI never shows. Applied to a request that also changes where the secret is sent, it sent
    the stored secret to whatever URL or host the request named - a secret no administrator can
    read was handed to anyone who may edit the record. So the secret has to be typed in again.

    Raises:
        StoredSecretError: When ``changed`` names any field.
    """
    if changed:
        msg = f"Enter the {what} again: {', '.join(changed)} changed, and the stored {what} is only sent where it was saved for"
        raise StoredSecretError(msg)


def keep_stored_api_key(data: object, model: type, record_id: object, destination: tuple[str, ...] = ()) -> object:
    """``data`` with the stored ``api_key`` of ``model`` ``record_id`` when the update leaves it empty.

    ``clear_api_key: true`` with an empty ``api_key`` removes the stored key instead (for a
    record whose key is optional); the flag itself never reaches the schema.

    Args:
        data: The submitted record.
        model: Its model class.
        record_id: Its id.
        destination: The fields that say where the key is sent (``api_url``); when the update
            changes any of them, the stored key is not kept (see :func:`refuse_moved_secret`).

    Returns:
        The data to update with.

    Raises:
        StoredSecretError: When the key is left empty while a destination field changes.
    """
    if isinstance(data, dict) and "clear_api_key" in data:
        # JSON true only: "false", or any other non-empty value, must not remove the key.
        clear = data.get("clear_api_key") is True
        data = {field: value for field, value in data.items() if field != "clear_api_key"}
        if clear and not (data.get("api_key") or "").strip():
            return {**data, "api_key": ""}
    if not isinstance(data, dict) or (data.get("api_key") or "").strip():
        return data
    stored = db.session.get(model, record_id)
    if stored is None or not stored.api_key:
        return data
    refuse_moved_secret(changed_destination(data, stored, destination))
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


def keep_secret_parameter(key: str | None, stored: str | None, submitted: str | None, *, clear: bool = False) -> str | None:
    """The value to store for a parameter: a secret left empty keeps the stored value.

    The GUI never receives a stored secret, so an empty one can only mean "keep it". Removing
    it takes an explicit ``clear`` (the dialog's remove button); a value typed in still wins.

    Args:
        key: The parameter's key.
        stored: The stored value.
        submitted: The value the update sends.
        clear: The update asks to remove the stored secret.

    Returns:
        The value to store.
    """
    if is_secret_parameter(key) and not (submitted or "").strip():
        return "" if clear else stored
    return submitted
