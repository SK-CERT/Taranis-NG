"""The GCVE GNA directory: which GNA number belongs to which authority, under which names.

gcve.eu publishes the directory of GCVE Numbering Authorities (https://gcve.eu/dist/gcve.json):
every GNA's number, short and full name, website, and where it publishes its records (its pull
API and its dumps). It is signed: ``gcve.json.sigsha512`` holds an RSA PKCS#1 v1.5 SHA-512
signature, base64, by the key https://gcve.eu/dist/key/public.pem (pinned below).

An organization's GNA short name is the directory's (model.organization_gna): it is copied from
here, never typed in, and a GNA number the directory does not list has no short name, so its
records are not published. Core downloads the directory, keeps it in Redis for a day, and copies
each organization's entry when its GNA number is saved, when it is checked from the GUI, and every
night. The setting ``GCVE_GNA_DIRECTORY_URL`` says where it comes from; an empty one turns the
lookup off. The gcve.eu directory must carry a valid signature; another URL (a test stub) is used
unsigned, and said to be unverified.

Every failure degrades instead of raising: a refresh that fails keeps the last good directory.
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from managers.cache_manager import redis_client
from managers.db_manager import db
from managers.log_manager import logger
from model.organization_gna import OrganizationGna
from model.setting import Setting

from shared import gcve

if TYPE_CHECKING:
    from flask import Flask
    from shared.time_manager import SchedulerManager

SIGNATURE_SUFFIX = ".sigsha512"

# https://gcve.eu/dist/key/public.pem, as published on 2026-11-16 (dated 2025-04-24 there).
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAuZrjI/aiXgAd4rnrWfnR
FLeUzLZNfu6G+ytNQfRSI6NdAD2mBatwEbGtdDxO27DycgRiOmv6ILxpbMjCvtaD
TQwUuTKbPK/c3E827p0Ohe0zKUz2IE5WHNg6JGAvFiCkdTo3ALlsw+thB0IfkBEV
DYJ0OpQ1J7qXL2FJWcfC0PmYDasIfv/17t4UTe2T+TcpyYfL/B/wg3gzbCys9wk6
H0jbJI/PQTzVusb4rWTOLYafTtuQ7ihXhXoJT1bFYzn+Vi5hnV/zhJyvh6CIRutR
KWYHw6Ok+FzzJWESsG+SUd+ZprwDPpGhSLLM1vnNh6EZi8g9Ji1jXZnINCWd/iKd
/gnK0gvplHGh6m0FWb3/KNLnbmoQNjiisuq/rqsZLUt+Vg193i0xSjJBFT9hEYr8
D36OOmJyToyi9DVk2T5BbP8miNCdHJUdp78a4gez8k2Vxq4eOmmc0RHH7KZZg3vu
OX/Le9FU5h6BkZSeH4r5pDF06dd9hyH2q0zaOZ6gH5/vsl0rIzIzj/auhJoaxtWz
Qux/wIPbm1M7cQdeDyXATtKzaTDWCZdmkbCxW9qXpAsyEPo4FPUobiAYPdX7CzYE
SG5WO4MKf+BKqwi7y/EdIrMK0x+jB41/MulDrXdtnRNfgAwQVpqP4rqBAPeALNGW
xOT6PS8T0M9j11ZSP9ShiX0CAwEAAQ==
-----END PUBLIC KEY-----
"""

CACHE_KEY = "gna:directory"
# Held while downloading, and left to expire after a failure: the retry back-off.
LOCK_KEY = "gna:directory:fetching"

REFRESH_AFTER_SECONDS = 24 * 3600
RETRY_AFTER_SECONDS = 600
FETCH_TIMEOUT = (3.05, 15)
MAX_BYTES = 2 * 1024 * 1024
MAX_SIGNATURE_BYTES = 8 * 1024
MAX_ENTRIES = 10000
MAX_TEXT = 200
MAX_SHORT_NAME = 32

TEXT_FIELDS = ("short_name", "full_name", "cpe_vendor_name")
URL_FIELDS = ("gcve_url", "gcve_api", "gcve_dump", "gcve_allocation", "gcve_pull_api")


class DirectoryError(Exception):
    """The directory could not be downloaded, or what came back is not one; the message says why."""


def directory_url() -> str | None:
    """Where the directory is downloaded from; None when the lookup is switched off (an empty setting)."""
    return (Setting.get_setting(None, gcve.DIRECTORY_URL_SETTING, gcve.DEFAULT_DIRECTORY_URL) or "").strip() or None


# -- downloading -----------------------------------------------------------------------------


def _get(url: str, limit: int) -> bytes:
    """The body of ``url`` (no redirects), at most ``limit`` bytes.

    Raises:
        DirectoryError: When it cannot be had.
    """
    try:
        with requests.get(url, timeout=FETCH_TIMEOUT, stream=True, allow_redirects=False) as response:
            if response.status_code != 200:  # noqa: PLR2004
                msg = f"{url} answered HTTP {response.status_code}"
                raise DirectoryError(msg)
            body = response.raw.read(limit + 1, decode_content=True)
    except requests.RequestException as error:
        msg = f"{url} could not be reached: {error}"
        raise DirectoryError(msg) from error
    if len(body) > limit:
        msg = f"{url} is larger than {limit} bytes"
        raise DirectoryError(msg)
    return body


def verify(body: bytes, signature: bytes, public_key_pem: bytes | None = None) -> bool:
    """Whether ``signature`` (base64, as gcve.eu publishes it) signs ``body`` with the key (the gcve.eu one by default)."""
    try:
        raw = base64.b64decode(b"".join(signature.split()), validate=True)
        key = serialization.load_pem_public_key(public_key_pem or PUBLIC_KEY_PEM)
        key.verify(raw, body, padding.PKCS1v15(), hashes.SHA512())
    except (InvalidSignature, binascii.Error, ValueError, TypeError):
        return False
    return True


def _clean_url(value: object) -> str | None:
    text = value.strip() if isinstance(value, str) else ""
    return text[:MAX_TEXT] if text.startswith(("https://", "http://")) else None


def clean_entry(entry: object) -> dict | None:
    """The parts of one directory entry worth keeping, or None for an unusable entry."""
    if not isinstance(entry, dict):
        return None
    number = entry.get("id")
    if isinstance(number, bool) or not isinstance(number, int) or number < 0:
        return None
    cleaned: dict = {"id": number}
    for field in TEXT_FIELDS:
        value = entry.get(field)
        if isinstance(value, str) and value.strip():
            cleaned[field] = value.strip()[:MAX_TEXT]
    short_name = cleaned.get("short_name")
    if short_name is not None and len(short_name) > MAX_SHORT_NAME:
        # The CVE Record Format's limit: such a name cannot be put in a record.
        del cleaned["short_name"]
    for field in URL_FIELDS:
        url = _clean_url(entry.get(field))
        if url:
            cleaned[field] = url
    return cleaned


def parse(body: bytes) -> dict[str, dict]:
    """The entries of a directory, by GNA number (as a string).

    Raises:
        DirectoryError: When it is not a list of GNAs.
    """
    try:
        payload = json.loads(body)
    except ValueError as error:
        msg = f"The GNA directory is not JSON: {error}"
        raise DirectoryError(msg) from error
    if not isinstance(payload, list):
        msg = "The GNA directory is not a list of GNAs"
        raise DirectoryError(msg)
    entries: dict[str, dict] = {}
    for entry in payload[:MAX_ENTRIES]:
        cleaned = clean_entry(entry)
        if cleaned is not None:
            entries[str(cleaned["id"])] = cleaned
    if not entries:
        msg = "The GNA directory lists no GNA"
        raise DirectoryError(msg)
    return entries


def download(url: str) -> dict:
    """Download and check the directory.

    Returns:
        dict: ``{"url", "verified", "fetched_at", "entries", "warning"}``; ``warning`` says why an
            unverified one is not.

    Raises:
        DirectoryError: When it cannot be had, or the gcve.eu one does not carry a valid signature.
    """
    body = _get(url, MAX_BYTES)
    entries = parse(body)
    try:
        verified = verify(body, _get(url + SIGNATURE_SUFFIX, MAX_SIGNATURE_BYTES))
        problem = None if verified else "its signature does not match the gcve.eu key"
    except DirectoryError as error:
        verified, problem = False, f"it has no signature ({error})"
    if not verified and url == gcve.DEFAULT_DIRECTORY_URL:
        msg = f"The GNA directory from {url} was refused: {problem}"
        raise DirectoryError(msg)
    return {"url": url, "verified": verified, "fetched_at": time.time(), "entries": entries, "warning": problem}


# -- the cached directory --------------------------------------------------------------------


def _cached() -> dict | None:
    try:
        raw = redis_client.get(CACHE_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        logger.exception("Could not read the cached GNA directory")
        return None


def _store(data: dict) -> None:
    try:
        redis_client.set(CACHE_KEY, json.dumps(data, separators=(",", ":")))
    except Exception:
        logger.exception("Could not cache the GNA directory")


def directory(force: bool = False) -> dict | None:
    """The directory, downloaded first when there is none from the configured URL, it is a day old, or ``force``.

    Only one worker downloads at a time (unless forced); the others go on with what is cached. A
    failed download keeps the last good directory and notes why in ``error``.

    Returns:
        dict | None: ``{"url", "verified", "fetched_at", "entries", "warning", "error"}``; None when the
            lookup is off, or nothing was ever downloaded from the URL.
    """
    url = directory_url()
    if url is None:
        return None
    cached = _cached()
    if cached is not None and cached.get("url") != url:
        cached = None
    fresh = cached is not None and cached.get("entries") and time.time() - float(cached.get("fetched_at") or 0) < REFRESH_AFTER_SECONDS
    if fresh and not force:
        return cached
    try:
        if not force and not redis_client.set(LOCK_KEY, "1", nx=True, ex=RETRY_AFTER_SECONDS):
            return cached
    except Exception:
        logger.exception("Could not take the GNA directory download lock")
        return cached
    try:
        data = download(url)
    except DirectoryError as error:
        logger.warning(f"GNA directory: {error}")
        failed = dict(cached) if cached is not None else {"url": url, "verified": False, "fetched_at": None, "entries": {}, "warning": None}
        failed["error"] = str(error)
        _store(failed)
        return failed
    data["error"] = None
    _store(data)
    try:
        redis_client.delete(LOCK_KEY)
    except Exception:
        logger.exception("Could not release the GNA directory download lock")
    return data


def lookup(gna_id: int, force: bool = False) -> dict | None:
    """The directory's entry for a GNA number; None when it does not list it (or there is no directory)."""
    data = directory(force)
    return (data or {}).get("entries", {}).get(str(gna_id))


def status(data: dict | None) -> dict:
    """What the GUI says about the directory: where from, whether verified, when, and what went wrong."""
    if data is None:
        url = directory_url()
        return {"url": url, "enabled": url is not None, "verified": False, "fetched_at": None, "warning": None, "error": None}
    fetched_at = data.get("fetched_at")
    return {
        "url": data.get("url"),
        "enabled": True,
        "verified": bool(data.get("verified")),
        "fetched_at": datetime.fromtimestamp(float(fetched_at), UTC).isoformat() if fetched_at else None,
        "warning": data.get("warning"),
        "error": data.get("error"),
    }


# -- the organizations' GNAs -----------------------------------------------------------------


def check_organization(gna: OrganizationGna, data: dict | None) -> bool:
    """Copy the directory's entry for an organization's GNA number into it (not committed).

    Nothing changes when there is no directory to go by.

    Returns:
        bool: Whether its short name changed (its published records name it).
    """
    if data is None or not data.get("entries"):
        return False
    entry = data["entries"].get(str(gna.gna_id))
    before = gna.short_name
    gna.directory = entry
    gna.short_name = (entry or {}).get("short_name")
    gna.directory_checked_at = datetime.now(UTC)
    return gna.short_name != before


def refresh_organizations(force: bool = False) -> int:
    """Check every organization's GNA against the directory, and tell the public webs when a name changed.

    Returns:
        int: How many short names changed.
    """
    data = directory(force)
    changed = sum(check_organization(gna, data) for gna in OrganizationGna.all())
    db.session.commit()
    if changed:
        notify_public_webs()
    return changed


def notify_public_webs() -> None:
    """Best-effort: the public webs drop their copy of the records (a GNA's name or settings changed)."""
    try:
        from managers import public_web_manager  # noqa: PLC0415 (it imports the API client chain)
        from model.public_web_node import PublicWebNode  # noqa: PLC0415

        if public_web_manager.public_web_enabled():
            public_web_manager.notify_nodes(PublicWebNode.get_all())
    except Exception:
        logger.exception("Could not tell the public webs that a GNA changed")


def job(app: Flask) -> None:
    """The nightly check of the organizations' GNAs."""
    with app.app_context():
        try:
            if OrganizationGna.query.limit(1).first() is not None:
                refresh_organizations()
        except Exception:
            db.session.rollback()
            logger.exception("Could not check the GNAs against the GCVE directory")


def schedule(manager: SchedulerManager, app: Flask) -> None:
    """Check the organizations' GNAs against the directory every night."""
    manager.schedule_job_every_day("03:17", job, "GCVE GNA directory check", app)
