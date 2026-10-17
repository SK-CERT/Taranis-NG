"""Texts of notifications, in the recipient's language.

There is one JSON catalog per language the GUI offers (``i18n/<locale>.json``). A notification
is written in the user's UI language (the ``UI_LANGUAGE`` setting) and a text missing from a
catalog falls back to English. User-supplied values (a passkey's name, the user's name) only
ever fill placeholders in the body: subjects are fixed texts, safe to put in a mail header.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from managers.log_manager import logger

if TYPE_CHECKING:
    from model.user import User

CATALOG_DIR = Path(__file__).with_name("i18n")
DEFAULT_LOCALE = "en"
SUBJECT_PREFIX = "[Taranis NG] "

# The order the details of a change are listed in, with the label each one gets.
DETAIL_LABELS = (
    ("username", "account"),
    ("time", "time"),
    ("actor", "changed_by"),
    ("ip", "ip"),
    ("passkey_name", "passkey"),
    ("authenticator", "authenticator"),
    ("factors", "factors"),
)


class _KeepMissing(dict):
    """Leaves an unknown placeholder as it is instead of failing the whole message."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def fill(template: str, values: dict) -> str:
    """Fill ``{placeholders}``; an unknown or malformed one is kept as written."""
    try:
        return template.format_map(_KeepMissing(values))
    except (ValueError, IndexError, AttributeError):
        return template


@cache
def available_locales() -> tuple[str, ...]:
    """The languages there is a catalog for."""
    return tuple(sorted(path.stem for path in CATALOG_DIR.glob("*.json")))


@cache
def load_catalog(locale: str) -> dict:
    """The catalog of a language, or an empty one when it cannot be read."""
    try:
        return json.loads((CATALOG_DIR / f"{locale}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.exception(f"Could not read the notification catalog '{locale}'")
        return {}


def resolve_locale(value: str | None) -> str:
    """Match a UI language to a catalog: exactly, then by base language, else English.

    ``pt-BR`` stays ``pt-BR``, ``de-AT`` becomes ``de`` and ``pt`` becomes ``pt-BR``.
    """
    locales = {locale.lower(): locale for locale in available_locales()}
    wanted = (value or "").strip().replace("_", "-").lower()
    if wanted in locales:
        return locales[wanted]
    base = wanted.split("-", 1)[0]
    if base in locales:
        return locales[base]
    for key, locale in sorted(locales.items()):
        if key.split("-", 1)[0] == base and base:
            return locale
    return DEFAULT_LOCALE


def locale_for(user: User) -> str:
    """The language to write to a user in: their UI language."""
    try:
        from model.setting import Setting  # noqa: PLC0415 - the model needs the app's database

        return resolve_locale(Setting.get_setting(user, "UI_LANGUAGE", DEFAULT_LOCALE))
    except Exception:
        logger.exception("Could not read the UI language of a notification recipient")
        return DEFAULT_LOCALE


def text(locale: str, *path: str) -> str:
    """One text of a catalog, falling back to English, then to the empty string."""
    for catalog in (load_catalog(locale), load_catalog(DEFAULT_LOCALE)):
        node = catalog
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, str) and node:
            return node
    return ""


def render(locale: str, event: str, context: dict) -> tuple[str, str]:
    """Write the subject and the body of a notification.

    Args:
        locale (str): Catalog language.
        event (str): What happened ("totp_enabled", ..., or "test").
        context (dict): name, and the details listed in ``DETAIL_LABELS``; actor is "self",
            or an administrator's name; factors is a list of "totp" / "passkeys";
            instance_url is optional.

    Returns:
        tuple: The subject and the plain-text body.
    """
    subject = SUBJECT_PREFIX + text(locale, "events", event, "subject")
    values = dict(context)
    if "actor" in values:
        actor = values["actor"]
        values["actor"] = text(locale, "actor_self") if actor == "self" else fill(text(locale, "actor_admin"), {"admin": actor})
    if values.get("factors"):
        values["factors"] = ", ".join(text(locale, f"factor_{factor}") for factor in values["factors"])

    lines = [fill(text(locale, "greeting"), {"name": values.get("name") or ""}), "", text(locale, "events", event, "text")]
    details = [(text(locale, "labels", label), values.get(key)) for key, label in DETAIL_LABELS if values.get(key)]
    if details:
        lines.append("")
        lines.extend(f"{label}: {value}" for label, value in details)
    if event != "test":
        lines += ["", text(locale, "unexpected")]
    url = values.get("instance_url")
    signature = fill(text(locale, "signature_with_url"), {"url": url}) if url else text(locale, "signature")
    lines += ["", "-- ", signature]
    return subject, "\n".join(lines) + "\n"
