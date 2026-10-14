"""Names and icons of passkey authenticators, looked up by AAGUID.

An authenticator reports its AAGUID when a passkey is registered. The community list at
github.com/passkeydeveloper/passkey-authenticator-aaguids maps the AAGUIDs of passkey providers and
FIDO certified security keys to a name and an icon, which is what people recognise in a list of
passkeys. The list is not ours to ship (it carries no licence and changes often), so core downloads
it and keeps it in Redis.

Downloading it means reaching GitHub, so the lookup is off until an administrator turns on the
PASSKEY_AUTHENTICATOR_LOOKUP setting. The PASSKEY_AUTHENTICATOR_LIST_URL setting says where the list
comes from, the upstream file unless a mirror is configured.

Every failure degrades instead of raising. A refresh that fails keeps serving the last good list,
and without any list an AAGUID is simply not described: the GUI then shows a generic icon next to
the raw AAGUID.
"""

from __future__ import annotations

import json
import re
import time

import requests
from flask import g, has_app_context
from managers.cache_manager import redis_client
from managers.log_manager import logger
from model.setting import Setting

LOOKUP_SETTING = "PASSKEY_AUTHENTICATOR_LOOKUP"
URL_SETTING = "PASSKEY_AUTHENTICATOR_LIST_URL"
DEFAULT_URL = "https://raw.githubusercontent.com/passkeydeveloper/passkey-authenticator-aaguids/main/combined_aaguid.json"

LIST_KEY = "webauthn:authenticators"
FETCHED_AT_KEY = "webauthn:authenticators:fetched_at"
# The URL the cached list came from: pointing the setting elsewhere refreshes it straight away.
SOURCE_KEY = "webauthn:authenticators:source"
# Held by the worker that downloads the list. It is left to expire after a failed download, which
# makes it the retry back-off as well: nobody tries again within the hour.
LOCK_KEY = "webauthn:authenticators:fetching"

REFRESH_AFTER_SECONDS = 7 * 24 * 3600
RETRY_AFTER_SECONDS = 3600
FETCH_TIMEOUT = (3, 15)

MAX_NAME_LENGTH = 200
# Most icons are a few KB; the few large ones would be repeated for every user in the users list.
MAX_ICON_LENGTH = 64 * 1024

# What an authenticator reports when it does not disclose its model.
ZERO_AAGUID = "00000000-0000-0000-0000-000000000000"
AAGUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Icons end up in an <img src>, so only base64 images are accepted, never markup or other URLs.
ICON_RE = re.compile(r"^data:image/(?:svg\+xml|png);base64,[A-Za-z0-9+/]+={0,2}$")


def source_url() -> str | None:
    """The URL of the list, or None while the lookup is switched off.

    The users list asks for every passkey it shows, so the settings are read once per request.
    """
    if has_app_context() and "passkey_authenticator_url" in g:
        return g.passkey_authenticator_url
    url = None
    if Setting.get_setting_bool(None, LOOKUP_SETTING, default_value=False):
        url = (Setting.get_setting(None, URL_SETTING, DEFAULT_URL) or "").strip() or None
    if has_app_context():
        g.passkey_authenticator_url = url
    return url


def lookup_enabled() -> bool:
    """Tell whether authenticators are being named, so the GUI can tell "off" from "unknown"."""
    try:
        return source_url() is not None
    except Exception:
        logger.exception("Could not read the passkey authenticator settings")
        return False


def describe(aaguid: str | None) -> dict | None:
    """Tell which authenticator an AAGUID belongs to.

    Args:
        aaguid (str | None): The AAGUID recorded for a passkey.

    Returns:
        dict | None: ``name``, ``icon_light`` and ``icon_dark`` (either icon may be None), or None
            when the AAGUID is missing or undisclosed, the lookup is off, the list does not know
            it, or no list is available.
    """
    if not aaguid:
        return None
    aaguid = aaguid.lower()
    if aaguid == ZERO_AAGUID:
        return None
    try:
        url = source_url()
        if not url:
            return None
        _refresh_if_due(url)
        raw = redis_client.hget(LIST_KEY, aaguid)
    except Exception:
        # A name next to a passkey is not worth failing the page over.
        logger.exception("Could not look up a passkey authenticator")
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _refresh_if_due(url: str) -> None:
    """Download the list when there is none, it is a week old or came from another URL.

    Only one worker downloads at a time; the others go on with whatever is cached.
    """
    fetched_at = redis_client.get(FETCHED_AT_KEY)
    source = redis_client.get(SOURCE_KEY)
    fresh = fetched_at and time.time() - float(fetched_at) < REFRESH_AFTER_SECONDS
    if fresh and source and source.decode() == url and redis_client.exists(LIST_KEY):
        return
    if not redis_client.set(LOCK_KEY, "1", nx=True, ex=RETRY_AFTER_SECONDS):
        return
    entries = _download(url)
    if entries is None:
        # Keep whatever list is cached and leave the lock to expire.
        return
    temporary_key = f"{LIST_KEY}:new"
    redis_client.delete(temporary_key)
    redis_client.hset(temporary_key, mapping=entries)
    # Readers see either the old list or the new one, never half of it.
    redis_client.rename(temporary_key, LIST_KEY)
    redis_client.set(FETCHED_AT_KEY, str(time.time()))
    redis_client.set(SOURCE_KEY, url)
    redis_client.delete(LOCK_KEY)


def _download(url: str) -> dict[str, str] | None:
    """Fetch and validate the list.

    Returns:
        dict | None: AAGUID to the entry as compact JSON, or None when nothing usable came back.
    """
    try:
        response = requests.get(url, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning(f"Could not download the passkey authenticator list from {url}: {error}")
        return None
    if not isinstance(payload, dict):
        logger.warning(f"The passkey authenticator list from {url} is not a JSON object")
        return None
    entries = {}
    for aaguid, entry in payload.items():
        cleaned = _clean_entry(aaguid, entry)
        if cleaned:
            entries[aaguid.lower()] = json.dumps(cleaned, separators=(",", ":"))
    if not entries:
        # The upstream README says a retired list becomes an empty object.
        logger.warning(f"The passkey authenticator list from {url} has no usable entries")
        return None
    return entries


def _clean_entry(aaguid: object, entry: object) -> dict | None:
    """Keep the parts of one list entry that are safe to show, or None for an unusable entry."""
    if not isinstance(aaguid, str) or not AAGUID_RE.match(aaguid.lower()) or not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    icon_light = _clean_icon(entry.get("icon_light"))
    icon_dark = _clean_icon(entry.get("icon_dark"))
    if icon_dark == icon_light:
        icon_dark = None
    return {"name": name.strip()[:MAX_NAME_LENGTH], "icon_light": icon_light, "icon_dark": icon_dark}


def _clean_icon(icon: object) -> str | None:
    if not isinstance(icon, str) or len(icon) > MAX_ICON_LENGTH or not ICON_RE.match(icon):
        return None
    return icon
